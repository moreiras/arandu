# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Limite de concorrência da API: no máximo N pedidos *calculando* ao mesmo tempo, os demais esperam na fila e, passado o tempo, recebem 503.

Por quê: a rota de ASN fria, o mapa e as análises carregam e montam objetos grandes; dezenas de pedidos assim ao mesmo tempo (a página de uma
CDN pede um documento por ASN) somam o pico de memória de todos e matam o processo por OOM. O limite por IP (slowapi) não
ajuda: o problema é a soma de muitos clientes. Aqui o teto é global e a espera é limitada.

- A vaga é devolvida quando a aplicação começa a responder (`http.response.start`): o custo de memória é o de montar a resposta; mandar os
  bytes (ex.: um download de 120 MB por um cliente lento) não segura a vaga.
- Resposta do cache de bytes do latest nem chega aqui (o middleware do cache é mais externo).
- `/health`, `/auth/*` e o diagnóstico interno ficam de fora: o healthcheck e o login não podem entrar na fila.
- Variáveis: `API_MAX_INFLIGHT` (padrão 8; 0 desliga) e `API_QUEUE_TIMEOUT_S` (padrão 20).
- **Por cliente:** no máximo `API_MAX_INFLIGHT_POR_CLIENTE` (padrão 4; 0 desliga) pedidos do mesmo
  cliente calculando ao mesmo tempo. O cliente é a identidade que o orçamento (api/limites.py) põe no escopo: conta ou rede (IPv6 pelo /64).
  Sem isto, um cliente só, com consultas caras em paralelo, ocupava todas as vagas globais. A vaga do cliente é pedida ANTES da global, para
  quem espera a própria vez não segurar vaga de ninguém. O MCP usa a mesma classe com o prefixo `MCP_`.
- **Fila das pesadas (desligada por padrão):** perfis com `include=` e as rotas de `ROTAS_PESADAS` pegariam antes uma vaga numa fila
  própria, `API_MAX_INFLIGHT_PESADAS` (padrão 0 = desligada), com espera de até `API_QUEUE_TIMEOUT_PESADAS_S` (30). A ideia era limitar
  quantos cálculos pesados disputam o GIL com as rotas leves. **Medido e recusado** (teste de carga `misto`, com 2 vagas):
  a 700 usuários `/query` foi de p50 0,5 s a 60 s e as rotas leves de p95 5,7 s a 60 s. O endereço não diz se o pedido é caro (com o
  aquecimento, os perfis saem do cache em ~0 ms e ainda assim esperavam na fila), e a vaga por cliente, pega antes, prendia as leves do
  mesmo visitante atrás das pesadas dele. O que resolveu a cauda foi o aquecimento (api/cache.py, `prewarm_perfis`).
"""
from __future__ import annotations

import asyncio
import json
import os

import structlog

_log = structlog.get_logger("arandurape.concurrency")

_ISENTOS = ("/health", "/auth/", "/api/v1/internal/")
#: trechos de caminho das rotas caras mesmo sem `include=` (ver também `api.limites.custo_api`)
ROTAS_PESADAS = ("/paths", "/map/query", "/api/v1/query/", "/potential")


def e_pesada(scope) -> bool:
    """Perfil consolidado (`include=` na query) ou rota de `ROTAS_PESADAS`."""
    if b"include=" in (scope.get("query_string") or b""):
        return True
    caminho = scope.get("path", "")
    return any(t in caminho for t in ROTAS_PESADAS)


class ConcurrencyLimitMiddleware:
    def __init__(self, app, max_inflight: int | None = None, queue_timeout_s: float | None = None, por_cliente: int | None = None,
                 prefixo: str = "API", isentos: tuple = _ISENTOS):
        self.app = app
        n = int(os.environ.get(f"{prefixo}_MAX_INFLIGHT", "8" if prefixo == "API" else "4")) if max_inflight is None else max_inflight
        self.timeout = float(os.environ.get(f"{prefixo}_QUEUE_TIMEOUT_S", "20")) if queue_timeout_s is None else queue_timeout_s
        pc = int(os.environ.get(f"{prefixo}_MAX_INFLIGHT_POR_CLIENTE", "4" if prefixo == "API" else "2")) if por_cliente is None else por_cliente
        self.sem = asyncio.Semaphore(n) if n > 0 else None
        self.max_inflight = n
        self.por_cliente = pc
        self.isentos = isentos
        np = int(os.environ.get(f"{prefixo}_MAX_INFLIGHT_PESADAS", "0"))
        self.sem_pesadas = asyncio.Semaphore(np) if np > 0 else None
        self.timeout_pesadas = float(os.environ.get(f"{prefixo}_QUEUE_TIMEOUT_PESADAS_S", "30"))
        self._clientes: dict[str, list] = {}        # chave → [Semaphore, nº de pedidos usando]
        self.rejeitados = 0

    async def _ocupado(self, send, motivo: str) -> None:
        self.rejeitados += 1
        corpo = json.dumps({"detail": "Servidor ocupado; tente novamente em instantes.", "busy": True}).encode()
        await send({"type": "http.response.start", "status": 503,
                    "headers": [(b"content-type", b"application/json"), (b"retry-after", b"5"),
                                (b"content-length", str(len(corpo)).encode()), (b"cache-control", b"no-store")]})
        await send({"type": "http.response.body", "body": corpo})

    def _sem_do_cliente(self, scope):
        ident = (scope.get("state") or {}).get("identidade")
        if self.por_cliente <= 0 or ident is None:
            return None, None
        par = self._clientes.get(ident.chave)
        if par is None:
            par = self._clientes[ident.chave] = [asyncio.Semaphore(self.por_cliente), 0]
        par[1] += 1
        return ident.chave, par

    def _soltar_cliente(self, chave, par) -> None:
        par[1] -= 1
        if par[1] <= 0:
            self._clientes.pop(chave, None)

    async def __call__(self, scope, receive, send):
        if self.sem is None or scope["type"] != "http" or scope["path"].startswith(self.isentos):
            return await self.app(scope, receive, send)

        chave, par = self._sem_do_cliente(scope)
        inicio = asyncio.get_running_loop().time()
        if par is not None:
            try:
                await asyncio.wait_for(par[0].acquire(), timeout=self.timeout)
            except asyncio.TimeoutError:
                self._soltar_cliente(chave, par)
                _log.warning("cliente com pedidos demais em andamento: recusado", path=scope["path"], por_cliente=self.por_cliente)
                return await self._ocupado(send, "cliente")
        pesada = self.sem_pesadas is not None and e_pesada(scope)
        if pesada:
            try:
                await asyncio.wait_for(self.sem_pesadas.acquire(), timeout=self.timeout_pesadas)
            except asyncio.TimeoutError:
                if par is not None:
                    par[0].release()
                    self._soltar_cliente(chave, par)
                _log.warning("api ocupada: pedido pesado recusado", path=scope["path"], espera_s=self.timeout_pesadas)
                return await self._ocupado(send, "pesadas")
            inicio = asyncio.get_running_loop().time()      # a espera da fila pesada não conta contra a global
        restante = max(0.1, self.timeout - (asyncio.get_running_loop().time() - inicio))
        try:
            await asyncio.wait_for(self.sem.acquire(), timeout=restante)
        except asyncio.TimeoutError:
            if pesada:
                self.sem_pesadas.release()
            if par is not None:
                par[0].release()
                self._soltar_cliente(chave, par)
            _log.warning("api ocupada: pedido recusado", path=scope["path"], espera_s=self.timeout, rejeitados=self.rejeitados + 1)
            return await self._ocupado(send, "global")

        liberada = False

        def liberar() -> None:
            nonlocal liberada
            if not liberada:
                liberada = True
                self.sem.release()
                if pesada:
                    self.sem_pesadas.release()
                if par is not None:
                    par[0].release()
                    self._soltar_cliente(chave, par)

        async def send_liberando(msg):
            if msg["type"] == "http.response.start":
                liberar()
            await send(msg)

        try:
            await self.app(scope, receive, send_liberando)
        finally:
            liberar()
