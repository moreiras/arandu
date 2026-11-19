# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cache de respostas em memória, escopado ao snapshot mais recente (latest).

Contexto e estratégia (deploy com **1 worker uvicorn**):

- O `Store` já cacheia os dicts JÁ PARSEADOS, eliminando disco + ``json.loads``.
- O custo por request que sobra é **re-serializar o JSON** (o índice de ASNs tem
  38 MB) e **re-gzipar** os bytes a cada hit — o ``GZipMiddleware`` não cacheia.
- Este módulo cacheia os **bytes finais** (JSON já serializado e já gzipado),
  keyed por URL, **apenas para o snapshot latest** (``date == latest``). Um hit
  vira essencialmente um ``memcpy``.
- Datas antigas **não** entram no cache — a memória é priorizada para o latest.
- Invalidação **automática** quando o latest muda (novo snapshot publicado): o
  cache inteiro é descartado.

Como é single-process, um dict em memória é compartilhado por todas as requests
e é mais rápido que Redis (sem rede, sem (de)serialização). Se um dia o deploy
passar a usar ``--workers N`` ou múltiplas réplicas, cada processo teria seu
próprio cache — é aí que um cache compartilhado (Redis) passaria a fazer sentido.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

from cachetools import LRUCache
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_log = logging.getLogger("arandurape")

# Cabeçalho recomputado pelo Response a partir do corpo — não replicar literalmente.
_SKIP_HEADERS = {"content-length"}

# Segundos entre re-checagens de qual é o snapshot latest (snapshots são semanais).
_LATEST_TTL = 60.0

# Orçamento padrão do byte-cache (soma dos corpos) e teto por entrada. O limite é
# em BYTES, não em número de entradas: o tamanho das respostas varia de ~1 KB
# (/asns/{asn} gzipado) a ~38 MB (/asns sem gzip), então contar entradas não
# limita a memória. Respostas acima do teto por entrada não são cacheadas.
DEFAULT_MAX_BYTES = 600 * 1024 * 1024
DEFAULT_MAX_ENTRY_BYTES = 16 * 1024 * 1024


class LatestResponseCache:
    """Cache LRU de respostas (bytes) restrito ao snapshot mais recente.

    ``max_bytes`` limita a soma dos corpos armazenados; ``max_entry_bytes`` evita
    que uma única resposta enorme expulse centenas de entradas pequenas.
    """

    def __init__(
        self,
        store,
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_entry_bytes: int = DEFAULT_MAX_ENTRY_BYTES,
    ) -> None:
        self._store = store
        self._max_entry_bytes = min(max_entry_bytes, max_bytes)
        # Valor = (status, headers, body): o custo é o tamanho do corpo.
        self._entries: LRUCache = LRUCache(
            maxsize=max_bytes, getsizeof=lambda v: len(v[2]) or 1
        )
        self._latest: Optional[str] = None
        self._latest_at: float = 0.0

    def current_latest(self) -> Optional[str]:
        """Retorna o latest, re-checando o disco no máximo a cada ``_LATEST_TTL``.

        Quando o latest muda, descarta todo o cache (o conteúdo do snapshot
        anterior não é mais o "quente").
        """
        now = time.monotonic()
        if self._latest is None or now - self._latest_at >= _LATEST_TTL:
            new_latest = self._store.latest()
            if new_latest != self._latest:
                if self._latest is not None:
                    _log.info(
                        "latest mudou (%s → %s): flush do byte-cache (%d entradas)",
                        self._latest, new_latest, len(self._entries),
                    )
                self._entries.clear()
                self._latest = new_latest
            self._latest_at = now
        return self._latest

    def get(self, key):
        return self._entries.get(key)

    def set(self, key, value) -> None:
        if len(value[2]) > self._max_entry_bytes:
            return
        self._entries[key] = value

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._entries)

    @property
    def size_bytes(self) -> int:
        return int(self._entries.currsize)


class LatestCacheMiddleware(BaseHTTPMiddleware):
    """Serve/armazena bytes de respostas do latest. Lê o cache de ``app.state``."""

    async def dispatch(self, request: Request, call_next):
        cache: Optional[LatestResponseCache] = getattr(
            request.app.state, "latest_cache", None
        )
        if cache is None or not self._is_cacheable(request, cache):
            return await call_next(request)

        accepts_gzip = "gzip" in request.headers.get("accept-encoding", "")
        key = (request.url.path, request.url.query, accepts_gzip)

        hit = cache.get(key)
        if hit is not None:
            status, headers, body = hit
            return Response(content=body, status_code=status, headers=dict(headers))

        response = await call_next(request)
        if response.status_code != 200:
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        headers = [
            (k, v) for k, v in response.headers.items()
            if k.lower() not in _SKIP_HEADERS
        ]
        cache.set(key, (response.status_code, headers, body))
        return Response(content=body, status_code=response.status_code, headers=dict(headers))

    @staticmethod
    def _is_cacheable(request: Request, cache: LatestResponseCache) -> bool:
        if request.method != "GET":
            return False
        if not request.url.path.startswith("/api/v1/"):
            return False
        # Endpoints autenticados (contatos) NUNCA entram no byte-cache compartilhado
        # — o cache é por path, e serviria a resposta a usuários anônimos.
        if request.url.path.endswith("/contacts"):
            return False
        date = request.query_params.get("date")
        if not date:
            # Sem date: resolve latest no servidor e pode virar a cada publicação;
            # mantemos fora do cache de longa duração.
            return False
        return date == cache.current_latest()


# Endpoints de chave fixa (sem paginação) que vale pré-materializar no warm-up.
# Os parametrizados/paginados (ex.: /asns?page=N) populam o cache sob demanda.
_PREWARM_PATHS = (
    "/api/v1/ixps",
    "/api/v1/external-ixps",
    "/api/v1/cdns/presence",
    "/api/v1/asns",
    "/api/v1/asns/names",
    "/api/v1/hilbert/v4",
    "/api/v1/hilbert/v6",
    "/api/v1/map/asns",
    "/api/v1/map/prefixes",
    "/api/v1/bgp-stability/summary",
    "/api/v1/ufs",   # /estados é página de entrada; o MISS leva segundos (distâncias de 5.570 municípios)
)


async def prewarm_latest(app, date_str: str) -> None:
    """Pré-materializa o byte-cache dos endpoints fixos do latest via ASGI interno.

    Faz requests internas (sem rede) através do próprio app, passando
    ``?date={latest}`` e ``Accept-Encoding: gzip`` para gravar exatamente a
    variante que os browsers recebem.
    """
    import httpx

    transport = httpx.ASGITransport(app=app)
    headers = {"accept-encoding": "gzip", "x-arandu-internal": "prewarm"}   # fora do log de uso
    populated = 0
    async with httpx.AsyncClient(transport=transport, base_url="http://prewarm") as client:
        for path in _PREWARM_PATHS:
            try:
                r = await client.get(path, params={"date": date_str}, headers=headers)
                if r.status_code == 200:
                    populated += 1
                else:
                    _log.info("prewarm %s -> HTTP %d (pulado)", path, r.status_code)
            except Exception as exc:  # pragma: no cover - resiliência
                _log.warning("prewarm falhou %s: %s", path, exc)
    _log.info("prewarm do latest (%s) concluído: %d endpoints", date_str, populated)


async def prewarm_top_asns(app, date_str: str, limit: int = 1000) -> None:
    """Pré-aquece o byte-cache dos top-N ASNs por número estimado de clientes.

    Ordena o índice por `apnic_users` (desc) e popula `/asns/{asn}` para os mais
    acessados, em background e com baixa concorrência (não satura a CPU no startup).
    Complementa o #1: com o doc já pré-computado no publish, cada request é só
    leitura+serialização — aqui evitamos também o 1º serialize+gzip desses ASNs.
    """
    import asyncio
    import httpx

    store = app.state.store
    try:
        index = store.asn_index(date_str)
    except Exception as exc:  # pragma: no cover - resiliência
        _log.warning("prewarm_top_asns: índice indisponível: %s", exc)
        return

    ranked = sorted(
        (a for a in index if a.get("asn") is not None),
        key=lambda a: a.get("apnic_users") or 0,
        reverse=True,
    )[:limit]
    asns = [a["asn"] for a in ranked]
    if not asns:
        return

    transport = httpx.ASGITransport(app=app)
    headers = {"accept-encoding": "gzip", "x-arandu-internal": "prewarm"}   # fora do log de uso
    sem = asyncio.Semaphore(4)  # baixa prioridade — não saturar a CPU no startup
    warmed = 0

    async with httpx.AsyncClient(transport=transport, base_url="http://prewarm") as client:
        async def _one(asn: int) -> None:
            nonlocal warmed
            async with sem:
                try:
                    r = await client.get(
                        f"/api/v1/asns/{asn}", params={"date": date_str}, headers=headers
                    )
                    if r.status_code == 200:
                        warmed += 1
                except Exception:  # pragma: no cover - resiliência
                    pass

        await asyncio.gather(*(_one(a) for a in asns))

    _log.info("prewarm dos top %d ASNs concluído: %d aquecidos (%s)", len(asns), warmed, date_str)


# Perfis consolidados como a interface os pede (frontend/src/services/api.ts): mesma rota, mesma lista de blocos, mesma ordem de
# parâmetros (`date`, `include`, `opcional`) e a vírgula codificada como o navegador (`%2C`), para cair na mesma chave do cache.
# `tests/unit/test_prewarm_perfis.py` confere estas listas contra o frontend.
PERFIS_DA_INTERFACE = {
    "ptt": ("/api/v1/ixps/{id}", "membros,usuarios_estimados,potencial,assinantes,indice,totais,historico,route_servers,rejeicoes,facilities,portas", False),
    "asn": ("/api/v1/asns/{id}", "paths,ixp_peers,estabilidade,historico,seguranca,prontidao,route_servers,politica_rs,organizacao,abuso,bloqueios,radar,exposicao,facilities,peering,transito,referencias", False),
    "operadora": ("/api/v1/operadoras/{id}", "historico,indicadores,erbs,multas,prontidao,qualidade,reclamacoes,consumidor,mercado_grupos", True),
    "municipio": ("/api/v1/municipios/{id}", "indicadores,territorio,erbs,fust,qualidade,reclamacoes,consumidor,serie_mercado,mercado_grupos,rede_territorio", True),
    "uf": ("/api/v1/ufs/{id}", "historico,territorio,cetic,erbs,fust,prontidao,qualidade,reclamacoes,consumidor,transito,radar,exposicao,mercado_grupos,rede_territorio", False),
}


def url_do_perfil(tipo: str, ident, date_str: str) -> str:
    rota, blocos, opcional = PERFIS_DA_INTERFACE[tipo]
    q = f"date={date_str}&include={blocos.replace(',', '%2C')}" + ("&opcional=true" if opcional else "")
    return rota.format(id=ident) + "?" + q


async def prewarm_perfis(app, date_str: str) -> None:
    """Aquece os perfis que as páginas de entidade pedem (com `include=`), dos mais procurados: todos os PTTs e UFs, e os N primeiros
    ASNs (por usuários), operadoras (por acessos) e municípios (por acessos). Um de cada vez: passa pela fila das pesadas
    (api/concurrency.py) e deixa a outra vaga para os visitantes. `PREWARM_PERFIS=0` desliga; `PREWARM_PERFIS_ASNS`,
    `PREWARM_PERFIS_OPERADORAS` e `PREWARM_PERFIS_MUNICIPIOS` (padrão 100 cada) mudam o tamanho.

    Por quê: o aquecimento de `/asns/{asn}` sem `include` não cobre o que a página pede, e o primeiro visitante pagaria o cálculo a frio
    (perfil do PTT de SP: 24,5 s no teste de carga, segurando as rotas leves)."""
    import httpx

    n = {k: int(os.environ.get(f"PREWARM_PERFIS_{k.upper()}", "100")) for k in ("asns", "operadoras", "municipios")}
    transport = httpx.ASGITransport(app=app)
    headers = {"accept-encoding": "gzip", "x-arandu-internal": "prewarm"}   # fora do log de uso
    aquecidos, falhas, t0 = 0, 0, time.monotonic()
    async with httpx.AsyncClient(transport=transport, base_url="http://prewarm", timeout=300) as client:
        async def lista(url, chave):
            try:
                r = await client.get(url, headers=headers)
                return r.json().get(chave) or [] if r.status_code == 200 else []
            except Exception:  # pragma: no cover - resiliência
                return []
        alvos = [("ptt", i["code"]) for i in await lista(f"/api/v1/ixps?date={date_str}", "ixps")]
        alvos += [("uf", u["uf"]) for u in await lista(f"/api/v1/ufs?date={date_str}", "items") if u.get("uf")]
        try:
            idx = app.state.store.asn_index(date_str)
            top = sorted((a for a in idx if a.get("asn") is not None and a.get("is_br")), key=lambda a: a.get("apnic_users") or 0, reverse=True)
            alvos += [("asn", a["asn"]) for a in top[:n["asns"]]]
        except Exception:  # pragma: no cover - resiliência
            pass
        if n["operadoras"] > 0:
            alvos += [("operadora", o["cnpj"]) for o in await lista(f"/api/v1/acessos/operadoras?date={date_str}&limit={min(n['operadoras'], 100)}", "items")]
        if n["municipios"] > 0:
            alvos += [("municipio", m["ibge"]) for m in (await lista(f"/api/v1/acessos/municipios?date={date_str}", "items"))[:n["municipios"]]]
        for tipo, ident in alvos:
            try:
                r = await client.get(url_do_perfil(tipo, ident, date_str), headers=headers)
                if r.status_code in (200, 204):
                    aquecidos += 1
                else:
                    falhas += 1
            except Exception:  # pragma: no cover - resiliência
                falhas += 1
    _log.info("prewarm dos perfis (%s) concluído: %d aquecidos, %d sem resposta, %.0f s", date_str, aquecidos, falhas, time.monotonic() - t0)
