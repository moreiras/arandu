# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoint de consulta genérica — POST /query.

Expõe o motor de filtro/agregação/geoproximidade de api/query.py via HTTP.
Aceita um body JSON com collection, filter, agg, sort, limit e near.
Mesmo motor usado pelo servidor MCP.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from api import query as q
from api.ratelimit import limiter, LIMIT_QUERY
from api.store import Store

_log = logging.getLogger("arandurape")

router = APIRouter()


@router.get(
    "/schema",
    summary="Catálogo de campos consultáveis (descoberta para a query DSL)",
    description="""
Lista, por collection, os campos consultáveis, tipos e descrições, além dos operadores
e funções de agregação suportados pela query DSL (`POST /query/{collection}`).

Use `?collection=asns` para obter apenas uma collection. Collections disponíveis:
`asns`, `ixps`, `external_ixps`, `cdns`, `prefixes`.
""",
)
def get_schema(
    collection: Optional[str] = Query(None, description="Filtra por uma collection."),
) -> dict:
    try:
        return q.schema(collection)
    except q.QueryError as exc:
        raise HTTPException(400, str(exc))


_EXAMPLE = {
    "filter": {"and": [
        {"field": "is_br", "op": "eq", "value": True},
        {"field": "has_ipv6", "op": "eq", "value": True},
        {"field": "has_rpki", "op": "eq", "value": False},
        {"field": "ixps_direct_count", "op": "gte", "value": 3},
    ]},
    "select": ["asn", "name", "apnic_users", "uf"],
    "sort": [{"field": "apnic_users", "dir": "desc"}],
    "limit": 50,
}


def _previa_anonima(request: Request, collection: str, body: dict, date: Optional[str]):
    """o `classify` só vê a query string; `limit`/`page` no corpo e as coleções de histórico ganham
    aqui a mesma prévia do site para quem não tem login nem allowlist. Segue o `ACCESS_POLICY_MODE` (em `shadow` só registra)."""
    if getattr(request.state, "access_tier", None) != "anon" or not isinstance(body, dict):
        return None
    from api.auth.access import policy_mode, recent_dates
    from api.auth.previa import COMO_FAZER_LOGIN, PreviaExcedida, conferir
    args = {"collection": collection, "limit": body.get("limit", 100), "page": body.get("page", 1), "date": date,
            "__explicitos__": {k for k in ("limit", "page") if k in body} | ({"date"} if date else set())}
    try:
        conferir("query", args, list(recent_dates(request) or []), COMO_FAZER_LOGIN)
    except PreviaExcedida as exc:
        if policy_mode() != "enforce":
            _log.info("policy_shadow_query_previa motivo=%s", str(exc).split(":")[0])
            return None
        return JSONResponse({"detail": str(exc), "login_required": True, "reason": "lista-expandida"}, status_code=401,
                            headers={"X-Login-Required": "true"})
    return None


@router.post(
    "/query/{collection}",
    summary="Consulta genérica (filtro/seleção/ordenação/agregação)",
    description="""
Primitiva de consulta sobre as tabelas em memória do snapshot. Componível:
filtros and/or/not, seleção, ordenação, paginação **e** agregação (group_by + aggregate).

**Operadores:** `eq ne gt gte lt lte in nin contains ncontains exists`
(`contains` = substring em strings ou pertinência em arrays; dot-path suportado, ex.:
`v4.br_prefix_coverage_pct`).

**Modo lista** → `items`. **Modo agregação** (com `group_by`/`aggregate`) → `groups`.

Veja os campos por collection em `GET /schema`. Collections: `asns`, `ixps`,
`external_ixps`, `cdns`, `prefixes`.

Álgebra de conjuntos na mesma collection sai de graça via filtro composto — ex.:
ASes diretos no SP mas não no RJ: `ixps_direct contains "sp" AND ncontains "rj"`.
""",
)
@limiter.limit(LIMIT_QUERY)
def post_query(
    collection: str,
    request: Request,
    body: dict = Body(default_factory=dict, examples=[_EXAMPLE]),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    bloqueio = _previa_anonima(request, collection, body or {}, date)
    if bloqueio is not None:
        return bloqueio
    try:
        return store.query(date_str, collection, body or {})
    except q.QueryError as exc:
        raise HTTPException(400, str(exc))


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------

@router.get(
    "/resolve/place",
    summary="Resolve um lugar (município) em coordenadas",
    description="Centroide (mediana) das organizações geolocalizadas no município. "
                "Use o resultado em `near.point` ou diretamente para consultas geográficas.",
    tags=["resolve"],
)
def resolve_place(
    request: Request,
    q_: str = Query(..., alias="q", description="Nome do município (ex.: Vitória)."),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    r = store.resolve_place(date_str, q_)
    if r is None:
        raise HTTPException(404, f"Local '{q_}' não encontrado")
    return {"snapshot_date": date_str, "place": q_, **r}


@router.get(
    "/resolve/operator",
    summary="Resolve uma marca/operador em ASNs",
    description="Casa CDN/CAP (cdns.json), nomes de AS e agrupa por raiz de CNPJ. "
                "Útil para alimentar /operators/reach com marcas multi-ASN.",
    tags=["resolve"],
)
def resolve_operator(
    request: Request,
    name: str = Query(..., description="Marca/operador (ex.: Globo, Claro)."),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return store.resolve_operator(date_str, name)


# ---------------------------------------------------------------------------
# Analíticos parametrizados
# ---------------------------------------------------------------------------

@router.get(
    "/analytics/ixps/{code}/nearby",
    summary="ASes com prefixos próximos a um PTT, por status e gap de anúncio",
    description="""
Para o PTT `code`, lista os ASes cujos prefixos BR geolocalizados estão a ≤ `radius_km`
de algum PIX, classificados por presença no PTT (direct / origin / absent) e com a
contagem de prefixos próximos **ainda não anunciados** no PTT.

Generaliza a seção "Potencial" com raio parametrizável e quebra por AS.
""",
    tags=["analytics"],
)
def ixp_nearby(
    code: str,
    request: Request,
    radius_km: float = Query(80.0, gt=0, le=2000, description="Raio em km a partir dos PIX."),
    limit: int = Query(500, ge=1, le=5000, description="Máximo de ASes retornados."),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    try:
        return store.ixp_nearby_breakdown(date_str, code, radius_km, limit)
    except q.QueryError as exc:
        raise HTTPException(404, str(exc))


@router.get(
    "/analytics/operators/reach",
    summary="Alcance de usuários finais BR de um operador via os PTTs",
    description="""
Dado um conjunto de ASNs (`asns=28604,26645`), calcula em quantos PTTs o operador está
presente e quantos usuários finais BR alcança por esse caminho — usuários visíveis via
os prefixos anunciados em cada PTT (metodologia de `estimated_users`), de-duplicados
entre PTTs (máx. fração por AS-olho). Use `/resolve/operator` para obter os ASNs de
uma marca.
""",
    tags=["analytics"],
)
def operator_reach(
    request: Request,
    asns: str = Query(..., description="ASNs separados por vírgula (ex.: 28604,26645)."),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    try:
        asn_list = [int(a) for a in asns.replace(" ", "").split(",") if a]
    except ValueError:
        raise HTTPException(400, "asns deve ser uma lista de inteiros separados por vírgula")
    if not asn_list:
        raise HTTPException(400, "informe ao menos um ASN")
    return store.operator_reach(date_str, asn_list)
