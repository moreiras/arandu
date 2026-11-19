# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Router de autenticação — OAuth (Google/LinkedIn/PeeringDB), GET /auth/me,
POST /auth/heartbeat, GET /auth/logout.

Login é feito via OAuth de terceiros; ao completar o fluxo, o usuário recebe
um cookie JWT. Não há sessão server-side para usuários logados — o token é
stateless e verificado em cada requisição protegida.

Para quem navega sem login e fora de ALLOWED_IPS, há uma sessão anônima com
estado (ver `api/auth/anon_session.py`), resolvida em /auth/me e avançada a
cada /auth/heartbeat.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
from typing import Optional
from urllib.parse import urlencode, urlsplit

import httpx
from fastapi import APIRouter, Request

_log = logging.getLogger("arandurape.auth")
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel

from api.auth import anon_session
from api.auth.access import evaluate_access, gate_response, policy_mode
from api.auth.config import get_auth_config
from api.auth.deps import client_ip, ip_diagnostics, resolve_identity
from api.auth import contas
from api.auth import sessao
from api.auth.jwt_utils import create_token
from api.auth.storage import log_access, upsert_user
from api.ratelimit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

_LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
_LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
_LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"

_PEERINGDB_AUTH_URL = "https://www.peeringdb.com/oauth2/authorize/"
_PEERINGDB_TOKEN_URL = "https://www.peeringdb.com/oauth2/token/"
_PEERINGDB_USERINFO_URL = "https://www.peeringdb.com/oauth2/userinfo/"


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_state(secret: str, next_url: str) -> str:
    """Estado HMAC-assinado: {nonce}:{next_url}:{sig8} — sem cookie server-side."""
    nonce = secrets.token_urlsafe(12)
    data = f"{nonce}:{next_url}"
    sig = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{data}:{sig}"


def _verify_state(secret: str, state: str) -> str | None:
    """Retorna next_url se o estado for válido, None caso contrário."""
    parts = state.rsplit(":", 1)
    if len(parts) != 2:
        return None
    data, sig = parts
    expected = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(sig, expected):
        return None
    # data = "{nonce}:{next_url}"
    _, _, next_url = data.partition(":")
    return _safe_next(next_url)


def _email_confirmado(userinfo: dict, campo: str) -> tuple[Optional[str], Optional[str]]:
    """(e-mail normalizado, erro) a partir do userinfo do provedor. a conta é achada pelo e-mail, então
    um e-mail que o provedor diz NÃO ter confirmado (`email_verified` no Google e no LinkedIn, `verified_email` no PeeringDB) é recusado.
    Sem o campo, aceita (os três provedores só cadastram e-mail confirmado)."""
    email = contas.normalizar_email(userinfo.get("email") or "")
    if not email:
        return None, "no_email"
    if userinfo.get(campo) is False or str(userinfo.get(campo)).lower() == "false":
        return None, "email_nao_verificado"
    return email, None


def _safe_next(url: str) -> str:
    """Garante que o redirect pós-login seja uma rota relativa deste site (sem open redirect).

    `//host` e `/\\host` começam com `/`, mas o navegador os lê como outro site. Só passa caminho
    absoluto sem esquema nem host, sem barra invertida e sem caractere de controle."""
    if not url or not url.startswith("/") or url.startswith("//") or "\\" in url or any(ord(c) < 0x20 or ord(c) == 0x7f for c in url):
        return "/"
    partes = urlsplit(url)
    if partes.scheme or partes.netloc:
        return "/"
    return url


def _pkce_challenge(verifier: str) -> str:
    """S256 code_challenge = BASE64URL(SHA256(verifier))."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _set_auth_cookie(response: RedirectResponse, token: str, secure: bool) -> None:
    response.set_cookie(
        "auth_token",
        token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=60 * 60 * 24 * 30,  # 30 dias (alinhado ao TTL do JWT)
        path="/",
    )


def _set_anon_cookie(response, session_id: str, secure: bool, ttl_hours: int) -> None:
    response.set_cookie(
        anon_session.COOKIE_NAME,
        session_id,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=ttl_hours * 60 * 60,
        path="/",
    )


# ── rotas ─────────────────────────────────────────────────────────────────────

@router.get("/google", include_in_schema=False)
async def google_login(request: Request, next: str = "/"):
    cfg = get_auth_config(request)
    state = _make_state(cfg.jwt_secret, _safe_next(next))
    redirect_uri = f"{cfg.app_base_url}/auth/google/callback"
    params = {
        "client_id": cfg.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
    }
    return RedirectResponse(_GOOGLE_AUTH_URL + "?" + urlencode(params))


@router.get("/google/callback", include_in_schema=False)
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    cfg = get_auth_config(request)

    if error or not code or not state:
        _log.warning("google callback falhou: error=%r description=%r code=%s state=%s",
                     error, error_description, bool(code), bool(state))
        return RedirectResponse("/login?error=cancelled")

    next_url = _verify_state(cfg.jwt_secret, state)
    if next_url is None:
        return RedirectResponse("/login?error=invalid_state")

    redirect_uri = f"{cfg.app_base_url}/auth/google/callback"

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(_GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": cfg.google_client_id,
            "client_secret": cfg.google_client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return RedirectResponse("/login?error=token_failed")

        userinfo_resp = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        userinfo = userinfo_resp.json()

    email, erro = _email_confirmado(userinfo, "email_verified")
    if erro:
        return RedirectResponse(f"/login?error={erro}")
    name: str = userinfo.get("name") or email

    conta = contas.registrar_login(cfg.data_dir, email, name, "google")
    if conta is None:                      # exclusão pedida: a conta fica desativada até o apagamento (30 dias)
        return RedirectResponse("/login?error=conta_em_exclusao")
    upsert_user(cfg.data_dir, email, name, "google")

    jwt_token = create_token(email, name, "google", cfg.jwt_secret, conta.conta_id)
    secure = cfg.app_base_url.startswith("https")
    response = RedirectResponse(next_url)
    _set_auth_cookie(response, jwt_token, secure)
    return response


@router.get("/linkedin", include_in_schema=False)
async def linkedin_login(request: Request, next: str = "/"):
    cfg = get_auth_config(request)
    if not cfg.linkedin_client_id:
        return RedirectResponse("/login?error=provider_not_configured")
    state = _make_state(cfg.jwt_secret, _safe_next(next))
    redirect_uri = f"{cfg.app_base_url}/auth/linkedin/callback"
    params = {
        "client_id": cfg.linkedin_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    return RedirectResponse(_LINKEDIN_AUTH_URL + "?" + urlencode(params))


@router.get("/linkedin/callback", include_in_schema=False)
async def linkedin_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    cfg = get_auth_config(request)

    if error or not code or not state:
        _log.warning("linkedin callback falhou: error=%r description=%r code=%s state=%s",
                     error, error_description, bool(code), bool(state))
        return RedirectResponse("/login?error=cancelled")

    next_url = _verify_state(cfg.jwt_secret, state)
    if next_url is None:
        return RedirectResponse("/login?error=invalid_state")

    redirect_uri = f"{cfg.app_base_url}/auth/linkedin/callback"

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(_LINKEDIN_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": cfg.linkedin_client_id,
            "client_secret": cfg.linkedin_client_secret,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return RedirectResponse("/login?error=token_failed")

        userinfo_resp = await client.get(
            _LINKEDIN_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        userinfo = userinfo_resp.json()

    email, erro = _email_confirmado(userinfo, "email_verified")
    if erro:
        return RedirectResponse(f"/login?error={erro}")
    name: str = userinfo.get("name") or email

    conta = contas.registrar_login(cfg.data_dir, email, name, "linkedin")
    if conta is None:                      # exclusão pedida: a conta fica desativada até o apagamento (30 dias)
        return RedirectResponse("/login?error=conta_em_exclusao")
    upsert_user(cfg.data_dir, email, name, "linkedin")

    jwt_token = create_token(email, name, "linkedin", cfg.jwt_secret, conta.conta_id)
    secure = cfg.app_base_url.startswith("https")
    response = RedirectResponse(next_url)
    _set_auth_cookie(response, jwt_token, secure)
    return response


@router.get("/peeringdb", include_in_schema=False)
async def peeringdb_login(request: Request, next: str = "/"):
    cfg = get_auth_config(request)
    if not cfg.peeringdb_client_id:
        return RedirectResponse("/login?error=provider_not_configured")
    # Nonce de 48 bytes (64 chars base64url) — usado também como PKCE code_verifier.
    nonce = secrets.token_urlsafe(48)
    next_safe = _safe_next(next)
    data = f"{nonce}:{next_safe}"
    sig = hmac.new(cfg.jwt_secret.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
    state = f"{data}:{sig}"
    redirect_uri = f"{cfg.app_base_url}/auth/peeringdb/callback"
    params = {
        "client_id": cfg.peeringdb_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": _pkce_challenge(nonce),
        "code_challenge_method": "S256",
    }
    return RedirectResponse(_PEERINGDB_AUTH_URL + "?" + urlencode(params))


@router.get("/peeringdb/callback", include_in_schema=False)
async def peeringdb_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    cfg = get_auth_config(request)

    if error or not code or not state:
        _log.warning("peeringdb callback falhou: error=%r description=%r code=%s state=%s",
                     error, error_description, bool(code), bool(state))
        return RedirectResponse("/login?error=cancelled")

    next_url = _verify_state(cfg.jwt_secret, state)
    if next_url is None:
        _log.warning("peeringdb callback: state inválido")
        return RedirectResponse("/login?error=invalid_state")

    redirect_uri = f"{cfg.app_base_url}/auth/peeringdb/callback"

    # Extrai o nonce (primeiro segmento do state) para usar como PKCE code_verifier.
    code_verifier = state.split(":")[0]

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_resp = await client.post(_PEERINGDB_TOKEN_URL, data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": cfg.peeringdb_client_id,
                "client_secret": cfg.peeringdb_client_secret,
                "code_verifier": code_verifier,
            }, headers={"Content-Type": "application/x-www-form-urlencoded"})
            try:
                token_data = token_resp.json()
            except Exception:
                _log.error("peeringdb token: resposta não-JSON — status=%s body=%r",
                           token_resp.status_code, token_resp.text[:200])
                return RedirectResponse("/login?error=token_failed")
            access_token = token_data.get("access_token")
            if not access_token:
                _log.warning("peeringdb token falhou: status=%s error=%r",
                             token_resp.status_code, token_data.get("error"))
                return RedirectResponse("/login?error=token_failed")

            userinfo_resp = await client.get(
                _PEERINGDB_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            try:
                userinfo = userinfo_resp.json()
            except Exception:
                _log.error("peeringdb userinfo: resposta não-JSON — status=%s body=%r",
                           userinfo_resp.status_code, userinfo_resp.text[:200])
                return RedirectResponse("/login?error=token_failed")
    except Exception as exc:
        _log.error("peeringdb callback: exceção inesperada: %s", exc, exc_info=True)
        return RedirectResponse("/login?error=token_failed")

    email, erro = _email_confirmado(userinfo, "verified_email")
    if erro:
        _log.warning("peeringdb userinfo sem e-mail confirmado (%s; campos recebidos: %s)", erro, sorted(userinfo)[:20])     # nunca o conteúdo
        return RedirectResponse(f"/login?error={erro}")
    name: str = userinfo.get("name") or email

    conta = contas.registrar_login(cfg.data_dir, email, name, "peeringdb")
    if conta is None:                      # exclusão pedida: a conta fica desativada até o apagamento (30 dias)
        return RedirectResponse("/login?error=conta_em_exclusao")
    upsert_user(cfg.data_dir, email, name, "peeringdb")

    jwt_token = create_token(email, name, "peeringdb", cfg.jwt_secret, conta.conta_id)
    secure = cfg.app_base_url.startswith("https")
    response = RedirectResponse(next_url)
    _set_auth_cookie(response, jwt_token, secure)
    return response


@router.get("/me", include_in_schema=False)
async def auth_me(request: Request):
    """Resolve a identidade da requisição: usuário autenticado, IP na allowlist,
    ou sessão anônima (cria/atualiza o estado e reemite o cookie se preciso).
    """
    cfg = get_auth_config(request)
    identity = resolve_identity(request)

    if identity["authenticated"]:
        return JSONResponse({"authenticated": True, **identity["user"]})

    body = {"authenticated": False, "anon": identity["anon"]}
    response = JSONResponse(body)
    if identity["set_cookie"]:
        anon_cfg = request.app.state.anon_config
        secure = cfg.app_base_url.startswith("https")
        _set_anon_cookie(response, identity["set_cookie"], secure, anon_cfg.ttl_hours)
    return response


@router.get("/gate", include_in_schema=False)
@limiter.exempt
async def auth_gate(request: Request):
    """Subrequisição `auth_request` (ver `api/auth/access.py::gate_response`).

    Em produção o nginx consulta o processo dedicado `api/gate_app.py` (porta 8001),
    que não disputa o event loop com as consultas pesadas da API; esta rota existe
    para dev e para chamadas que não passam pelo nginx.
    """
    return gate_response(request)


@router.get("/diag", include_in_schema=False)
async def auth_diag(request: Request, path: str | None = None, query: str = ""):
    """Diagnóstico de identificação do cliente (IP visto, tier). Sem efeitos colaterais:
    não cria nem atualiza sessão anônima. Responde só sobre a própria requisição.
    """
    cfg = get_auth_config(request)
    info = ip_diagnostics(request, cfg.allowed_ips)
    # sessão revogável (JWT de conta excluída ou "sair de todos" não conta mais como logado)
    has_jwt = sessao.usuario_do_cookie(request.cookies.get("auth_token"), cfg.jwt_secret, cfg.data_dir) is not None
    if info["na_allowlist"]:
        tier = "allowed"
    elif has_jwt:
        tier = "user"
    else:
        tier = "anon"
    body = {**info, "tier": tier, "allowlist_entradas": len(cfg.allowed_ips)}
    body["politica_modo"] = policy_mode()
    if path:
        # Explica como a política classifica uma rota (depuração): /auth/diag?path=/api/v1/asns&query=page%3D2
        from urllib.parse import parse_qsl

        from api.auth import access_policy
        from api.auth.access import recent_dates

        c = access_policy.classify("GET", path, dict(parse_qsl(query)), recent_dates(request))
        body["rota"] = {"path": path, "query": query, "classe": c.cls, "motivo": c.reason}
    return JSONResponse(
        body,
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/heartbeat", include_in_schema=False)
@limiter.limit("20/minute")
async def heartbeat(request: Request):
    """Registra um heartbeat de sessão anônima (usuário ativo há N segundos).

    Enviado periodicamente pelo frontend apenas enquanto a aba está visível e
    houve interação recente — não é chamado a cada requisição de dados, então
    o delta somado reflete atividade real do usuário, não tráfego de rede.
    Usuários autenticados ou em IP na allowlist recebem `anon: null` (isentos).
    """
    cfg = get_auth_config(request)
    identity = resolve_identity(request)

    if identity["authenticated"]:
        return JSONResponse({"authenticated": True, "anon": None})

    body = {"authenticated": False, "anon": identity["anon"]}
    response = JSONResponse(body)
    if identity["set_cookie"]:
        anon_cfg = request.app.state.anon_config
        secure = cfg.app_base_url.startswith("https")
        _set_anon_cookie(response, identity["set_cookie"], secure, anon_cfg.ttl_hours)
    return response


_LOG_PATH_MAX = 512


class _LogRequest(BaseModel):
    path: str


@router.post("/log", include_in_schema=False)
@limiter.limit("30/minute")
async def log_page(request: Request, body: _LogRequest):
    """Registra acesso a uma rota do frontend (somente usuários autenticados)."""
    cfg = get_auth_config(request)

    # sessão revogável e a identidade é o conta_id (o log nunca guarda e-mail)
    usuario = sessao.usuario_do_cookie(request.cookies.get("auth_token"), cfg.jwt_secret, cfg.data_dir)
    if not usuario:
        return {"ok": True}

    # Sanitize: remove CR/LF (log injection) e limita comprimento.
    path = body.path.replace("\r", "").replace("\n", "")[:_LOG_PATH_MAX]
    ip = client_ip(request)
    log_access(cfg.data_dir, ip, usuario["conta_id"], path)
    return {"ok": True}


@router.get("/logout", include_in_schema=False)
async def logout():
    response = RedirectResponse("/")
    response.delete_cookie("auth_token", path="/")
    return response
