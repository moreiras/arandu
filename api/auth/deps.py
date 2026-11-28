# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Dependencies de autenticação para proteger endpoints sensíveis (ex.: contatos).

`current_user()` é o guard de entrada único: aceita um JWT válido no cookie
`auth_token` OU um IP na allowlist (`ALLOWED_IPS`). Não há sessão server-side
para usuários logados — a única sessão com estado é a anônima, tratada
separadamente em `anon_session.py` e resolvida por `resolve_identity()`.
"""

from __future__ import annotations

import ipaddress
from typing import Optional

from fastapi import HTTPException, Request

from api.auth import anon_session
from api.auth.config import get_auth_config
from api.auth import sessao


def normalize_ip(raw: Optional[str]) -> str:
    """Normaliza o IP recebido nos headers de proxy para comparação com CIDRs.

    Aceita lista (`a, b` → primeiro), porta (`1.2.3.4:5678`, `[::1]:443`),
    colchetes e IPv4 mapeado em IPv6 (`::ffff:1.2.3.4` → `1.2.3.4`, que de outro
    modo não casaria com nenhum CIDR IPv4). Valor inválido volta como veio.
    """
    if not raw:
        return ""
    value = raw.split(",")[0].strip()
    if value.startswith("["):
        value = value[1:].split("]", 1)[0]
    elif value.count(":") == 1:  # IPv4 com porta
        value = value.split(":", 1)[0]
    try:
        addr = ipaddress.ip_address(value)
    except ValueError:
        return value
    if addr.version == 6 and addr.ipv4_mapped is not None:
        return str(addr.ipv4_mapped)
    return str(addr)


def _client_ip(request: Request) -> str:
    raw = request.headers.get("X-Real-IP") or (request.client.host if request.client else "?")
    return normalize_ip(raw) or "?"


def _ip_in_allowlist(ip: str, allowed: list[str]) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for entry in allowed:
        try:
            if "/" in entry:
                if addr in ipaddress.ip_network(entry, strict=False):
                    return True
            elif addr == ipaddress.ip_address(entry):
                return True
        except ValueError:
            pass
    return False


# Aliases públicos — usados fora de api.auth (ex.: middleware em api/main.py)
# para não depender de nomes "privados" (prefixo _) de outro módulo.
client_ip = _client_ip
ip_in_allowlist = _ip_in_allowlist


def ip_diagnostics(request: Request, allowed: list[str]) -> dict:
    """Como a API enxerga o cliente — para diagnosticar a allowlist (GET /auth/diag).

    Devolve só dados da própria requisição (IP visto, headers de proxy, versão,
    se é IPv4 mapeado em IPv6 e se casa com a allowlist). Não revela o conteúdo
    da allowlist.
    """
    seen = _client_ip(request)
    raw = request.headers.get("X-Real-IP") or (request.client.host if request.client else "?")
    info: dict = {
        "ip_visto": seen,
        "x_real_ip": request.headers.get("X-Real-IP"),
        "x_forwarded_for": request.headers.get("X-Forwarded-For"),
        "peer": request.client.host if request.client else None,
        "versao": None,
        "ipv4_mapeado": False,
        "na_allowlist": False,
    }
    try:
        addr = ipaddress.ip_address(seen)
    except ValueError:
        return info
    info["versao"] = addr.version
    try:
        raw_addr = ipaddress.ip_address(raw.split(",")[0].strip().strip("[]"))
        info["ipv4_mapeado"] = bool(raw_addr.version == 6 and raw_addr.ipv4_mapped is not None)
    except ValueError:
        pass
    info["na_allowlist"] = _ip_in_allowlist(seen, allowed)
    return info


def current_user(request: Request) -> Optional[dict]:
    """Retorna o usuário autenticado ({email, name, provider, conta_id}) ou None.

    Isento de qualquer lógica de sessão anônima: IP na allowlist ou JWT válido
    tratam a requisição sem orçamento nem sessão anônima.
    """
    cfg = get_auth_config(request)
    user = sessao.usuario_do_cookie(request.cookies.get("auth_token"), cfg.jwt_secret, cfg.data_dir)
    if user:
        return user
    if _ip_in_allowlist(_client_ip(request), cfg.allowed_ips):
        return {"email": None, "name": "Visitante", "provider": "ip"}
    return None


def require_user(request: Request) -> dict:
    """Dependency: exige usuário autenticado; 401 caso contrário."""
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Esta ação exige login. Faça login para continuar.")
    return user


def resolve_identity(request: Request) -> dict:
    """Resolve a identidade completa da requisição, incluindo sessão anônima.

    Usado por `GET /auth/me` e `POST /auth/heartbeat` — ambos precisam do
    resultado completo (usuário OU estado anônimo) e, no caso anônimo, avançar
    o heartbeat. Retorna um dict com:
      - authenticated: bool
      - user: {email, name, provider} | None
      - anon: {active_seconds, limit_seconds, limit_reached, bloqueio_rede,
               heartbeat_interval_seconds, inactivity_timeout_seconds} | None
      - set_cookie: session_id a gravar no cookie de resposta, ou None
    """
    user = current_user(request)
    if user is not None:
        return {"authenticated": True, "user": user, "anon": None, "set_cookie": None}

    cfg = get_auth_config(request)
    anon_cfg: anon_session.AnonSessionConfig = request.app.state.anon_config
    cookie_sid = request.cookies.get(anon_session.COOKIE_NAME)
    fp_raw = request.headers.get(anon_session.FINGERPRINT_HEADER)
    rede = anon_session.hash_rede(client_ip(request), cfg.jwt_secret)
    fp_hash = anon_session.hash_fingerprint(fp_raw, rede) if fp_raw else None     # restrito à rede: aparelhos iguais não se misturam
    fp_est_raw = request.headers.get(anon_session.FINGERPRINT_ESTAVEL_HEADER)      # cliente antigo não manda
    fp_est_hash = anon_session.hash_fingerprint_estavel(fp_est_raw, rede) if fp_est_raw else None

    # Área da página em uso (o front informa `open` nas páginas de entrada: o
    # relógio do orçamento só anda em `metered`). Ausente = metered (cliente legado).
    area = request.headers.get(anon_session.AREA_HEADER, anon_session.AREA_METERED).lower()
    if area not in ("open", anon_session.AREA_METERED):
        area = anon_session.AREA_METERED

    r = anon_session.resolver_sessao(cfg.data_dir, anon_cfg, cookie_sid, fp_hash, area, rede, fp_est_hash)
    return {
        "authenticated": False,
        "user": None,
        "anon": {
            "active_seconds": r.active_seconds,
            "limit_seconds": anon_cfg.limit_seconds,
            "limit_reached": r.limit_reached,
            "bloqueio_rede": r.bloqueio_rede,
            "heartbeat_interval_seconds": anon_cfg.heartbeat_interval_seconds,
            "inactivity_timeout_seconds": anon_cfg.inactivity_timeout_seconds,
        },
        "set_cookie": r.session_id if (r.needs_cookie and r.session_id) else None,
    }
