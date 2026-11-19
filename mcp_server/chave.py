# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Autenticação do MCP por chave: `Authorization: Bearer arandu_mcp_…` → nível *user*.

O MCP roda num contêiner somente leitura e não guarda hash nem pepper: pergunta à API (`/internal/mcp-chave/verificar`, token interno) e guarda o
resultado em memória por 30 s (válida) ou 5 s (inválida), por `sha256(chave)` — nunca a chave. Sem chave, o MCP atende como anônimo (como antes).
Chave inválida ou revogada: 401 (nunca cai para anônimo). API fora do ar: 401 com `Retry-After` (falha fechada só para quem usa chave).
Cota diária por conta (`MCP_COTA_DIARIA`, padrão 1.000 requisições POST ao MCP por dia UTC; 0 desliga): acima dela, 429 com `Retry-After`, sem suspensão.
Os eventos de uso por conta vão em lote à API (o MCP não escreve em `data/`). Desligado por padrão: `MCP_KEY_ATIVA=1` liga.
"""
from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import os
import secrets
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import structlog

_log = structlog.get_logger(__name__)
PREFIXO = "arandu_mcp_"
TTL_VALIDA_S = 30.0
TTL_INVALIDA_S = 5.0
MAX_CACHE = 1000
_SAL = secrets.token_hex(16)        # só em memória: o cliente do limite de tentativas não é ligável entre execuções


def ligada() -> bool:
    return os.environ.get("MCP_KEY_ATIVA", "0").strip().lower() in ("1", "true", "sim")


def cota_diaria() -> int:
    try:
        return max(0, int(os.environ.get("MCP_COTA_DIARIA", "1000")))
    except ValueError:
        return 1000


def _segundos_ate_meia_noite_utc() -> int:
    agora = datetime.now(timezone.utc)
    return max(1, int((agora.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1) - agora).total_seconds()))


async def _resposta(send, status: int, detalhe: str, extra: Optional[dict] = None) -> None:
    corpo = json.dumps({"detail": detalhe}).encode()
    cab = [(b"content-type", b"application/json"), (b"content-length", str(len(corpo)).encode())]
    for k, v in (extra or {}).items():
        cab.append((k.lower().encode(), str(v).encode()))
    await send({"type": "http.response.start", "status": status, "headers": cab})
    await send({"type": "http.response.body", "body": corpo})




def _rede_do_cliente(ip: str) -> str:
    """IPv4 inteiro; IPv6 pelo /64 (o prefixo que identifica o assinante: trocar o sufixo não vira outro cliente)."""
    try:
        end = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    return str(ipaddress.ip_network(f"{end}/64", strict=False)) if end.version == 6 else str(end)

class ChaveMiddleware:
    def __init__(self, app, api_url: Optional[str] = None, token: Optional[str] = None, cliente: Optional[httpx.AsyncClient] = None):
        self.app = app
        self.api_url = (api_url or os.environ.get("MCP_API_URL", "http://api:8000")).rstrip("/")
        self.token = token if token is not None else os.environ.get("INTERNAL_API_TOKEN", "")
        self._http = cliente
        self._cache: OrderedDict[str, tuple[float, Optional[str]]] = OrderedDict()
        self._contagem: dict[tuple[str, str], int] = {}
        self._fila: list[dict] = []
        self._envio: Optional[asyncio.Task] = None

    def _cliente_http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=1.0)
        return self._http

    def _do_cache(self, chave_hash: str) -> tuple[bool, Optional[str]]:
        hit = self._cache.get(chave_hash)
        if hit and hit[0] > time.monotonic():
            return True, hit[1]
        return False, None

    def _guardar(self, chave_hash: str, conta: Optional[str]) -> None:
        self._cache[chave_hash] = (time.monotonic() + (TTL_VALIDA_S if conta else TTL_INVALIDA_S), conta)
        self._cache.move_to_end(chave_hash)
        while len(self._cache) > MAX_CACHE:
            self._cache.popitem(last=False)

    async def _verificar_na_api(self, chave: str, cliente: str) -> tuple[str, Optional[str], int]:
        """('ok'|'invalida'|'limitada'|'indisponivel', conta_id, retry_after)"""
        try:
            r = await self._cliente_http().post(f"{self.api_url}/internal/mcp-chave/verificar", json={"chave": chave, "cliente": cliente}, headers={"X-Internal-Token": self.token})
        except httpx.HTTPError:
            return "indisponivel", None, 5
        if r.status_code == 429:
            return "limitada", None, int(r.headers.get("Retry-After", "60"))
        if r.status_code != 200:
            return "indisponivel", None, 5
        j = r.json()
        return ("ok", j.get("conta_id"), 0) if j.get("valida") else ("invalida", None, 0)

    def _contar(self, conta: str) -> bool:
        """True se ainda cabe na cota do dia (UTC)."""
        dia = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for k in [k for k in self._contagem if k[1] != dia]:
            del self._contagem[k]
        n = self._contagem.get((conta, dia), 0) + 1
        self._contagem[(conta, dia)] = n
        limite = cota_diaria()
        return limite == 0 or n <= limite

    def _evento(self, conta: str, rota: str, status: int, ms: float) -> None:
        self._fila.append({"conta": conta, "rota": rota, "status": status, "ms": round(ms, 1), "classe": "mcp"})
        if len(self._fila) >= 50 or self._envio is None or self._envio.done():
            self._envio = asyncio.create_task(self._enviar())

    async def _enviar(self) -> None:
        await asyncio.sleep(2.0)
        lote, self._fila = self._fila[:500], self._fila[500:]
        if not lote:
            return
        try:
            await self._cliente_http().post(f"{self.api_url}/internal/uso-conta", json={"eventos": lote}, headers={"X-Internal-Token": self.token})
        except httpx.HTTPError:
            _log.debug("uso_conta_nao_enviado", eventos=len(lote))      # perde o lote: o registro é de controle, não de cobrança

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not ligada():
            return await self.app(scope, receive, send)
        cab = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        auth = cab.get("authorization", "")
        if not auth:
            return await self.app(scope, receive, send)                 # anônimo
        chave = auth[7:].strip() if auth[:7].lower() == "bearer " else ""
        if not chave.startswith(PREFIXO) or len(chave) > 200:
            return await _resposta(send, 401, "Chave de MCP inválida ou revogada.", {"WWW-Authenticate": 'Bearer realm="mcp"'})
        h = hashlib.sha256(chave.encode()).hexdigest()
        achou, conta = self._do_cache(h)
        if not achou:
            ip = (cab.get("x-real-ip") or (scope.get("client") or ("?",))[0]).split(",")[0].strip()
            # o cliente é o IP (IPv6 por /64), não IP+User-Agent: variar o User-Agent escapava do limite por cliente.
            cliente = hashlib.sha256(f"{_SAL}|{_rede_do_cliente(ip)}".encode()).hexdigest()[:16]
            estado, conta, espera = await self._verificar_na_api(chave, cliente)
            if estado in ("indisponivel", "limitada"):
                return await _resposta(send, 429 if estado == "limitada" else 401, "Verificação da chave indisponível no momento." if estado == "indisponivel" else "Muitas tentativas inválidas.",
                                       {"Retry-After": espera, "WWW-Authenticate": 'Bearer realm="mcp"'})
            self._guardar(h, conta)
        if not conta:
            return await _resposta(send, 401, "Chave de MCP inválida ou revogada.", {"WWW-Authenticate": 'Bearer realm="mcp"'})
        if scope.get("method") == "POST" and not self._contar(conta):
            return await _resposta(send, 429, "Limite diário de chamadas ao MCP atingido para a sua conta. Tente novamente depois da meia-noite (UTC).", {"Retry-After": _segundos_ate_meia_noite_utc()})
        estado = scope.setdefault("state", {})
        estado["access_tier"] = "user"
        estado["conta_id"] = conta
        t0 = time.perf_counter()
        status = 0

        async def _enviar_resp(msg):
            nonlocal status
            if msg["type"] == "http.response.start":
                status = msg["status"]
            await send(msg)

        try:
            await self.app(scope, receive, _enviar_resp)
        finally:
            if scope.get("method") == "POST":
                self._evento(conta, scope.get("path", "/mcp").split("?", 1)[0], status, (time.perf_counter() - t0) * 1000)
