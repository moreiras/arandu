# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Orçamento de requisições por cliente, comum à API e ao MCP.

Quem é o cliente:
- **conta** (cookie de login na API; chave de MCP no MCP): a chave do orçamento é o `conta_id`, não o IP. Quem navega de trás do NAT de uma
  universidade não divide o limite com os colegas, e trocar de IP não renova o orçamento;
- **allowlist** (`ALLOWED_IPS`): orçamento de conta, contado pela rede;
- **anônimo**: a rede do IP, IPv4 inteiro e **IPv6 pelo /64** (trocar o sufixo dentro do prefixo do assinante não vira outro cliente).
  A rede entra em hash com um sal só em memória: o contador nunca guarda o IP.

Como conta: várias janelas ao mesmo tempo (rajada por minuto, teto por hora e por dia), tolerante a rajada e restritivo no acumulado. Cada
requisição custa unidades conforme a rota (`/query` 3; `/map/query` e `.../paths` 5; o resto 1). O contador é por processo e em memória (um
processo de API e um de MCP por contêiner); reiniciar zera as janelas, o que não muda a ordem de grandeza da proteção. Acima do teto: 429 com
`Retry-After`, `RateLimit-*` e o nome da janela; o 429 nunca é cacheável.

Variáveis (vazio ou `0` desliga a classe): `API_ORCAMENTO_ANON`, `API_ORCAMENTO_CONTA`, `MCP_ORCAMENTO_ANON`, `MCP_ORCAMENTO_CONTA`, na sintaxe
da biblioteca `limits` (`"120/minute;1500/hour;6000/day"`).
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import os
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Optional

import structlog
from limits import parse_many
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter

_log = structlog.get_logger("arandurape.limites")
_SAL = secrets.token_hex(16)

PADROES = {
    "api": {"anon": "120/minute;1500/hour;6000/day", "conta": "240/minute;4000/hour;20000/day"},
    # A cota diária do MCP com chave (`MCP_COTA_DIARIA`, mcp_server/chave.py) já é o teto do dia. O anônimo é mais largo que a proposta
    # inicial (30/min, 200/h, 500/dia) porque conectores de assistentes (claude.ai e afins) saem de poucos IPs compartilhados por todos os usuários
    # deles: sem a chave de MCP ligada (`MCP_KEY_ATIVA=1`), um teto apertado por rede barraria todos de uma vez.
    "mcp": {"anon": "60/minute;1000/hour;5000/day", "conta": "60/minute;400/hour"},
}
_ISENTOS_API = ("/health", "/auth/", "/api/v1/internal/")
_NOME_JANELA = {1: "segundo", 60: "minuto", 3600: "hora", 86400: "dia"}


def itens_efetivos(perfil: str, classe: str) -> list:
    """Janelas em vigor de uma classe: a variável `<PERFIL>_ORCAMENTO_<CLASSE>` se existir, senão `PADROES`. Vazio = classe desligada.
    É a única leitura: o middleware e `GET /api/v1/limites` partem daqui."""
    bruto = os.environ.get(f"{perfil.upper()}_ORCAMENTO_{classe.upper()}")
    bruto = PADROES[perfil][classe] if bruto is None else bruto.strip()
    if not bruto or bruto == "0":
        return []
    return list(parse_many(bruto))


def janelas_efetivas(perfil: str, classe: str) -> list[dict]:
    """`itens_efetivos` como `[{"janela": "minuto", "segundos": 60, "limite": 120}, ...]`."""
    return [{"janela": _NOME_JANELA.get(i.get_expiry(), f"{i.get_expiry()} s"), "segundos": i.get_expiry(), "limite": i.amount}
            for i in itens_efetivos(perfil, classe)]


def rede_do_ip(ip: str) -> str:
    """IPv4 inteiro; IPv6 pelo /64."""
    try:
        end = ipaddress.ip_address((ip or "").strip())
    except ValueError:
        return ip or "?"
    if end.version == 6 and end.ipv4_mapped:
        return str(end.ipv4_mapped)
    return str(ipaddress.ip_network(f"{end}/64", strict=False)) if end.version == 6 else str(end)


def hash_da_rede(ip: str) -> str:
    return hashlib.sha256(f"{_SAL}|{rede_do_ip(ip)}".encode()).hexdigest()[:24]


def _allowlist() -> list:
    redes = []
    for e in os.environ.get("ALLOWED_IPS", "").split(","):
        e = e.strip()
        if not e:
            continue
        try:
            redes.append(ipaddress.ip_network(e, strict=False))
        except ValueError:
            continue
    return redes


def na_allowlist(ip: str, redes: Optional[list] = None) -> bool:
    try:
        end = ipaddress.ip_address((ip or "").strip())
    except ValueError:
        return False
    return any(end in r for r in (redes if redes is not None else _allowlist()))


def ip_do_escopo(scope) -> str:
    """X-Real-IP (posto pelo nginx interno, já com o IP real do cliente) ou o par da conexão."""
    for k, v in scope.get("headers", []):
        if k == b"x-real-ip":
            return v.decode("latin-1").split(",")[0].strip()
    cli = scope.get("client")
    return cli[0] if cli else "?"


def interno(scope) -> bool:
    """Pedido da própria API (aquecimento via `httpx.ASGITransport`): par em loopback, sem `X-Real-IP` (o nginx sempre o põe) e com
    `x-arandu-internal`. Fica fora do orçamento e do limite por cliente; a fila das pesadas e o teto global continuam valendo.
    Sem isto o aquecimento conta como um cliente só da allowlist (240/min): num teste, 964 pedidos recusados e 219 de 1.000 ASNs aquecidos."""
    cli = scope.get("client")
    if not cli or cli[0] not in ("127.0.0.1", "::1"):
        return False
    nomes = {k for k, _ in scope.get("headers", [])}
    return b"x-arandu-internal" in nomes and b"x-real-ip" not in nomes


@dataclass(frozen=True)
class Identidade:
    classe: str          # "conta" | "allowlist" | "anon"
    chave: str           # "conta:<id>" ou "rede:<hash>"
    rede: str            # hash da rede (sempre presente)


def identificar(scope, conta_id: Optional[str] = None, redes_allowlist: Optional[list] = None) -> Identidade:
    ip = ip_do_escopo(scope)
    rede = hash_da_rede(ip)
    if conta_id:
        return Identidade("conta", f"conta:{conta_id}", rede)
    if na_allowlist(ip, redes_allowlist):
        return Identidade("allowlist", f"rede:{rede}", rede)
    return Identidade("anon", f"rede:{rede}", rede)


def custo_api(path: str) -> int:
    if path.startswith("/api/v1/query"):
        return 3
    if path.startswith("/api/v1/map/query") or path.endswith("/paths"):
        return 5
    return 1


class _CacheCookie:
    """Cookie → conta_id por 30 s (sha256 do token na chave), para não abrir o banco de contas a cada requisição. Só serve ao orçamento:
    a autorização de verdade continua sendo feita pela rota."""

    def __init__(self, maximo: int = 5000, ttl_s: float = 30.0):
        self._d: OrderedDict = OrderedDict()
        self.maximo, self.ttl = maximo, ttl_s

    def obter(self, token: str, resolver: Callable[[str], Optional[str]]) -> Optional[str]:
        h = hashlib.sha256(token.encode()).hexdigest()
        agora = time.monotonic()
        hit = self._d.get(h)
        if hit and hit[1] > agora:
            return hit[0]
        try:
            conta = resolver(token)
        except Exception:                                   # noqa: BLE001 — o orçamento nunca derruba a requisição
            conta = None
        self._d[h] = (conta, agora + self.ttl)
        self._d.move_to_end(h)
        while len(self._d) > self.maximo:
            self._d.popitem(last=False)
        return conta


def _cookie(scope, nome: str) -> Optional[str]:
    for k, v in scope.get("headers", []):
        if k == b"cookie":
            for parte in v.decode("latin-1").split(";"):
                n, _, val = parte.strip().partition("=")
                if n == nome and val:
                    return val
    return None


def _resolver_api(scope) -> Callable[[str], Optional[str]]:
    def resolver(token: str) -> Optional[str]:
        from api.auth import sessao
        cfg = scope["app"].state.auth_config
        u = sessao.usuario_do_cookie(token, cfg.jwt_secret, cfg.data_dir)
        return (u or {}).get("conta_id")
    return resolver


class OrcamentoMiddleware:
    """Middleware ASGI do orçamento. `perfil="api"`: conta pelo cookie `auth_token`; `perfil="mcp"`: conta pelo `conta_id` que o
    `ChaveMiddleware` põe no escopo (este middleware precisa ficar DENTRO dele). Guarda a identidade em `scope["state"]["identidade"]` para o
    limite de concorrência por cliente (api/concurrency.py)."""

    def __init__(self, app, perfil: str = "api"):
        self.app = app
        self.perfil = perfil
        self.limiter = FixedWindowRateLimiter(MemoryStorage())
        self.limites = {c: self._ler(perfil, c) for c in ("anon", "conta")}
        self.cookies = _CacheCookie()
        self.redes = _allowlist()
        self.recusados = 0

    @staticmethod
    def _ler(perfil: str, classe: str) -> list:
        return itens_efetivos(perfil, classe)

    def _isento(self, scope) -> bool:
        if scope.get("method") == "OPTIONS":
            return True
        if self.perfil == "mcp":
            return scope.get("method") != "POST"           # só chamadas (POST) gastam; GET/DELETE de sessão não
        return scope["path"].startswith(_ISENTOS_API)

    def _custo(self, path: str) -> int:
        return custo_api(path) if self.perfil == "api" else 1

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        estado = scope.setdefault("state", {})
        if interno(scope):
            return await self.app(scope, receive, send)      # sem identidade: o limite por cliente (api/concurrency.py) também não vale
        if self.perfil == "mcp":
            conta = estado.get("conta_id")
        else:
            tok = _cookie(scope, "auth_token")
            conta = self.cookies.obter(tok, _resolver_api(scope)) if tok else None
        ident = identificar(scope, conta, self.redes)
        estado["identidade"] = ident
        if self._isento(scope):
            return await self.app(scope, receive, send)
        itens = self.limites["anon" if ident.classe == "anon" else "conta"]
        custo = self._custo(scope["path"])
        for item in itens:
            if not self.limiter.test(item, self.perfil, ident.chave, cost=custo):
                return await self._recusar(send, ident, item, custo)
        for item in itens:
            self.limiter.hit(item, self.perfil, ident.chave, cost=custo)
        return await self.app(scope, receive, send)

    async def _recusar(self, send, ident: Identidade, item, custo: int) -> None:
        self.recusados += 1
        janela = _NOME_JANELA.get(item.get_expiry(), f"{item.get_expiry()} s")
        stats = self.limiter.get_window_stats(item, self.perfil, ident.chave)
        espera = max(1, math.ceil(stats.reset_time - time.time()))
        _log.warning("orcamento_excedido", perfil=self.perfil, classe=ident.classe, janela=janela, limite=item.amount, custo=custo,
                     recusados=self.recusados)
        quem = "sua conta" if ident.classe == "conta" else "sua rede"
        corpo = json.dumps({
            "detail": f"Limite de uso por {janela} atingido para {quem}. Tente novamente em {espera} s.",
            "rate_limited": True, "janela": janela, "limite": item.amount, "retry_after": espera,
        }, ensure_ascii=False).encode()
        await send({"type": "http.response.start", "status": 429, "headers": [
            (b"content-type", b"application/json; charset=utf-8"), (b"content-length", str(len(corpo)).encode()),
            (b"retry-after", str(espera).encode()), (b"cache-control", b"no-store"),
            (b"ratelimit-limit", str(item.amount).encode()), (b"ratelimit-remaining", b"0"), (b"ratelimit-reset", str(espera).encode()),
        ]})
        await send({"type": "http.response.body", "body": corpo})
