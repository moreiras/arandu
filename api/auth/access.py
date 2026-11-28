# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Decisão de acesso (allowlist / usuário / sessão anônima + política por rota).

Usada por dois pontos de entrada, com a MESMA regra:
  - `GET /auth/gate` — subrequisição `auth_request` do nginx do frontend, executada
    ANTES do cache em disco do nginx (sem isto, um HIT serve qualquer usuário sem
    passar pela API);
  - middleware `anon_session_guard` em `api/main.py` — defesa em profundidade para
    chamadas que não passam pelo nginx (dev, rede Docker) e cache MISS.

Modo (`ACCESS_POLICY_MODE`):
  off      — comportamento legado: com o limite de tempo atingido, bloqueia tudo
             (exceto rotas isentas);
  shadow   — (padrão) igual ao `off`, e LOGA `policy_shadow` quando a política nova
             decidiria diferente. Não muda o que o visitante vê;
  enforce  — vale a política nova (`api/auth/access_policy.py`): `open` nunca bloqueia,
             `metered` bloqueia com o orçamento esgotado, `login` sempre pede login.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from fastapi import Request

from api.auth import access_policy as policy
from api.auth import anon_session
from api.auth.anon_session import COOKIE_NAME as ANON_COOKIE_NAME
from api.auth.deps import client_ip, ip_in_allowlist
from api.auth import sessao

# Prefixos isentos: fluxo de login/logout/heartbeat (precisam funcionar mesmo com
# o limite atingido) e docs/health (sem dado sensível).
EXEMPT_PREFIXES = (
    "/auth/",
    "/internal/",              # só o MCP chama (token interno); o nginx não encaminha
    "/health",
    "/api/v1/docs",
    "/api/v1/redoc",
    "/api/v1/openapi.json",
)

BLOCK_LIMIT = "limit"   # orçamento de uso esgotado → 429 com Retry-After na API; 403 só entre o gate e o nginx (que o troca por 429, ver `limite_anonimo`)
BLOCK_LOGIN = "login"   # ação que exige login → 401

_log = logging.getLogger("arandurape.access")
_LOG_TTL = 600.0  # 1 linha por (ip, tier, decisão) a cada 10 min — evita ruído
_seen: dict[tuple, float] = {}


def policy_mode() -> str:
    mode = os.environ.get("ACCESS_POLICY_MODE", "shadow").strip().lower()
    return mode if mode in ("off", "shadow", "enforce") else "shadow"


def _log_once(key: tuple, msg: str, *args) -> None:
    now = time.monotonic()
    last = _seen.get(key)
    if last is not None and now - last < _LOG_TTL:
        return
    if len(_seen) > 5000:
        _seen.clear()
    _seen[key] = now
    _log.info(msg, *args)


@dataclass
class AccessDecision:
    ip: str
    tier: str                    # allowed | user | anon
    blocked: bool
    kind: Optional[str] = None   # BLOCK_LIMIT | BLOCK_LOGIN (quando blocked)
    cls: Optional[str] = None    # open | metered | login (classe da rota)
    reason: Optional[str] = None


def is_exempt(path: str) -> bool:
    return any(path.startswith(p) for p in EXEMPT_PREFIXES)


# "Datas atuais" (as 2 mais recentes) — cache de 60 s para não varrer o disco a
# cada requisição (o gate é chamado em todas as chamadas de API).
_recent_cache: tuple[float, list[str]] = (0.0, [])


def recent_dates(request: Request) -> Optional[Sequence[str]]:
    global _recent_cache
    now = time.monotonic()
    ts, dates = _recent_cache
    if dates and now - ts < 60:
        return dates
    store = getattr(request.app.state, "store", None)
    if store is None:
        return None
    try:
        snaps = store.list_snapshots()
    except Exception:  # noqa: BLE001 — falha de leitura não pode derrubar o guard
        return dates or None
    dates = list(snaps[-policy.N_DATAS_ATUAIS:])
    _recent_cache = (now, dates)
    return dates or None


def _new_policy_blocks(cls: str, limit_reached: bool) -> Optional[str]:
    if cls == policy.LOGIN:
        return BLOCK_LOGIN
    if cls == policy.METERED and limit_reached:
        return BLOCK_LIMIT
    return None


def evaluate_access(
    request: Request,
    path: str,
    via: str = "middleware",
    method: Optional[str] = None,
    query: Optional[dict] = None,
) -> Optional[AccessDecision]:
    """Decide se a requisição é bloqueada. None = não se aplica (rota isenta ou sem config)."""
    if is_exempt(path):
        return None
    cfg = getattr(request.app.state, "auth_config", None)
    if cfg is None:
        return None

    ip = client_ip(request)
    method = (method or request.method or "GET").upper()
    query = dict(request.query_params) if query is None else query

    if ip_in_allowlist(ip, cfg.allowed_ips):
        _log_once((ip, "allowed", "pass"), "access_decision ip=%s tier=allowed decision=pass path=%s via=%s", ip, path, via)
        return AccessDecision(ip, "allowed", False)

    usuario = sessao.usuario_do_cookie(request.cookies.get("auth_token"), cfg.jwt_secret, cfg.data_dir)
    if usuario:
        request.state.conta_id = usuario["conta_id"]        # lido pelo log de uso por conta (api/uso_conta.py)
        _log_once((ip, "user", "pass"), "access_decision ip=%s tier=user decision=pass path=%s via=%s", ip, path, via)
        return AccessDecision(ip, "user", False)

    # ── anônimo ──────────────────────────────────────────────────────────────
    anon_cfg = request.app.state.anon_config
    cookie_sid = request.cookies.get(ANON_COOKIE_NAME)
    fp_raw = request.headers.get(anon_session.FINGERPRINT_HEADER)
    # quem não tem sessão emitida pelo servidor (cookie que existe no banco, ou fingerprint ligado a uma sessão real) é contado pela
    # rede do IP. Cookie inventado e fingerprint aleatório não acham sessão e caem aqui.
    rede = anon_session.hash_rede(ip, cfg.jwt_secret)
    fp_hash = anon_session.hash_fingerprint(fp_raw, rede) if fp_raw else None
    fp_est_raw = request.headers.get(anon_session.FINGERPRINT_ESTAVEL_HEADER)
    fp_est_hash = anon_session.hash_fingerprint_estavel(fp_est_raw, rede) if fp_est_raw else None
    state = anon_session.peek_state(cfg.data_dir, anon_cfg, cookie_sid, fp_hash, rede, fp_est_hash, rede)   # inclui o teto da rede
    limit_reached = state.limit_reached

    classification = policy.classify(method, path, query, recent_dates(request))
    new_kind = _new_policy_blocks(classification.cls, limit_reached)
    legacy_kind = BLOCK_LIMIT if limit_reached else None

    # Cliente sem sessão válida (script/curl, cookie inventado): debita custo por requisição não aberta na conta da rede do IP.
    if (
        anon_cfg.api_client_cost_seconds > 0
        and state.identity not in ("cookie", "fingerprint", "fingerprint_estavel")
        and classification.cls != policy.OPEN
        and policy_mode() == "enforce"
    ):
        if anon_session.charge_client(cfg.data_dir, anon_cfg, rede, anon_cfg.api_client_cost_seconds):
            new_kind = new_kind or BLOCK_LIMIT

    mode = policy_mode()
    kind = new_kind if mode == "enforce" else legacy_kind

    if mode == "shadow" and new_kind != legacy_kind:
        _log_once(
            (ip, "shadow", new_kind, legacy_kind, classification.cls, classification.reason, "/".join(path.split("/")[:4])),
            "policy_shadow ip=%s identity=%s class=%s reason=%s new=%s legacy=%s path=%s",
            ip, state.identity, classification.cls, classification.reason,
            new_kind or "pass", legacy_kind or "pass", path,
        )

    decision = "block:" + kind if kind else "pass"
    _log_once(
        (ip, "anon", decision),
        "access_decision ip=%s tier=anon decision=%s class=%s mode=%s identity=%s path=%s via=%s",
        ip, decision, classification.cls, mode, state.identity, path, via,
    )
    return AccessDecision(
        ip, "anon", kind is not None, kind, classification.cls, classification.reason
    )


def segundos_ate_meia_noite_utc(agora: Optional[datetime] = None) -> int:
    """Segundos até a próxima 00:00 UTC, quando o orçamento de quem é identificado pela rede é renovado (`anon_session.hash_rede` usa a data UTC)."""
    agora = agora or datetime.now(timezone.utc)
    proxima = (agora + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, int((proxima - agora).total_seconds()))


ALTERNATIVA_LOGIN = "Entre no site com uma conta gratuita: o login libera listas completas, histórico e contatos."
ALTERNATIVA_CHAVE_MCP = "Use o servidor MCP com chave de MCP (gerada em /perfil), que tem cota própria."


def alternativas_limite() -> list[str]:
    """Saídas oferecidas no 429. A chave de MCP só é sugerida quando está ligada, pela mesma regra de `GET /api/v1/limites`
    (`chaves_mcp.ativa()`: `MCP_KEY_ATIVA` e `MCP_KEY_PEPPER`); o gate roda noutro processo e lê o mesmo ambiente a cada resposta."""
    from api.auth import chaves_mcp

    return [ALTERNATIVA_LOGIN, ALTERNATIVA_CHAVE_MCP] if chaves_mcp.ativa() else [ALTERNATIVA_LOGIN]


def corpo_limite_anonimo(retry_after: int) -> dict:
    """Corpo do 429 do orçamento anônimo esgotado: o limite, quando renova e a saída. `anon_limit_reached` é o campo que o site lê."""
    return {
        "detail": "O orçamento diário de uso sem login desta rede acabou (a rede é o IPv4 inteiro ou o prefixo IPv6 /64). "
                  "Ele é renovado à meia-noite UTC; entre com uma conta para continuar agora.",
        "anon_limit_reached": True,
        "janela": "dia",
        "retry_after": retry_after,
        "alternativas": alternativas_limite(),
    }


def limite_anonimo(cors: Optional[dict] = None):
    """Resposta do orçamento anônimo esgotado: 429 com `Retry-After` (segundos até a meia-noite UTC) e o corpo de `corpo_limite_anonimo`.
    Nunca cacheável. O nginx a obtém do processo do gate (`GET /auth/limite`), porque o `auth_request` só distingue 401 e 403."""
    from starlette.responses import JSONResponse

    segundos = segundos_ate_meia_noite_utc()
    return JSONResponse(
        corpo_limite_anonimo(segundos), status_code=429,
        headers={"Retry-After": str(segundos), "X-Anon-Limit-Reached": "true", "Cache-Control": "private, no-store", **(cors or {})},
    )


def gate_response(request: Request):
    """Resposta do `GET /auth/gate` (usada pela API e pelo processo `gate_app`).

    204 = liberar; 403 = orçamento esgotado (o nginx o converte em 429 com `Retry-After`, `limite_anonimo`); 401 = ação que exige login. A rota
    original vem de `X-Original-URI`/`X-Original-Method` (preenchidos pelo nginx).
    """
    from urllib.parse import parse_qsl, urlsplit

    from starlette.responses import Response

    parts = urlsplit(request.headers.get("X-Original-URI", ""))
    decision = evaluate_access(
        request,
        parts.path or "/",
        via="gate",
        method=request.headers.get("X-Original-Method", "GET"),
        query=dict(parse_qsl(parts.query)),
    )
    headers = {"Cache-Control": "private, no-store"}
    if decision is not None and decision.blocked:
        status = 401 if decision.kind == BLOCK_LOGIN else 403
        return Response(status_code=status, headers=headers)
    return Response(status_code=204, headers=headers)
