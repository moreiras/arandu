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

import json
import logging
import re
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
    return _consultar(request, collection, body or {}, date)


# A linha da requisição passa pelo nginx (~8 KB); corpo maior vai pelo POST (até `_MAX_CORPO_QUERY`, api/main.py). O site manda até
# MAX_CORPO_NA_URL (frontend/src/services/api.ts) por GET.
# 5 KiB de caracteres: cobre os 5.000 do site (MAX_CORPO_NA_URL) e, no pior caso (UTF-8 de 4 bytes, percentual: 12 caracteres na URL
# por caractere), a URL fica em ~60 KiB, abaixo do teto de 64 KiB do httpx (o fuzz do T4 gerava URLs que o cliente nem montava).
_MAX_CORPO_GET = 5 * 1024


@router.get(
    "/query/{collection}",
    summary="Consulta genérica por GET (o mesmo motor, cacheável)",
    description="""
O mesmo motor e as mesmas regras de `POST /query/{collection}`, com o corpo da consulta em `corpo` (JSON, codificado na URL). Por ser GET,
a resposta entra no cache do navegador, do nginx e da API: com `date` de snapshot publicado sai `immutable`. É o que o site usa nas
perguntas prontas da página inicial, que todos os visitantes repetem. Corpo grande demais para uma URL vai pelo POST.

Exemplo: `GET /api/v1/query/operadoras?date=2026-11-15&corpo={"select":["empresa","acessos"],"sort":[{"field":"acessos","dir":"desc"}],"limit":5}`
""",
)
@limiter.limit(LIMIT_QUERY)
def get_query(
    collection: str,
    request: Request,
    corpo: str = Query("{}", max_length=_MAX_CORPO_GET, description="Corpo da consulta em JSON (o mesmo do POST)."),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    try:
        body = json.loads(corpo or "{}")
    except ValueError:
        raise HTTPException(400, "corpo: JSON inválido")
    if not isinstance(body, dict):
        raise HTTPException(400, "corpo: deve ser um objeto JSON")
    return _consultar(request, collection, body, date)


def _consultar(request: Request, collection: str, body: dict, date: Optional[str]):
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    bloqueio = _previa_anonima(request, collection, body, date)
    if bloqueio is not None:
        return bloqueio
    try:
        return store.query(date_str, collection, body)
    except q.QueryError as exc:
        raise HTTPException(400, str(exc))


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------

_UFS = frozenset("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split())
_NOME_UF = re.compile(r"^(.*?)\s*(?:/|,|-|\()\s*([A-Za-z]{2})\s*\)?$")


@router.get(
    "/resolve/place",
    summary="Resolve um lugar (município) em coordenadas",
    description="Centroide do município (IBGE); sem o nome na tabela do IBGE, a mediana das sedes geolocalizadas no município "
                "arredondada a 0,1° (`posicao` diz qual). A UF vem de `uf` ou do próprio `q` (`Bom Jesus/PI`, `Bom Jesus, PI`). Sem "
                "UF, um nome que existe em mais de uma UF não é resolvido: a resposta traz `ambiguo: true`, `ufs` e `lat`/`lon` "
                "nulos, em vez de misturar os homônimos. Use o resultado em `near.point` ou diretamente para consultas geográficas.",
    tags=["resolve"],
)
def resolve_place(
    request: Request,
    q_: str = Query(..., alias="q", description="Nome do município (ex.: Vitória ou Bom Jesus/PI)."),
    uf: Optional[str] = Query(None, min_length=2, max_length=2, description="UF do município (sigla)."),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    nome, sigla = q_.strip(), (uf or "").upper() or None
    m = _NOME_UF.match(nome)
    if m and sigla is None and m.group(2).upper() in _UFS:
        nome, sigla = m.group(1).strip(), m.group(2).upper()
    if sigla is None:
        ufs = store.place_ufs(date_str, nome)
        if len(ufs) > 1:                        # homônimos (LOC-E4): a mediana de pontos de UFs diferentes caía a centenas de km de todos
            return {"snapshot_date": date_str, "place": q_, "ambiguo": True, "ufs": ufs, "lat": None, "lon": None, "n": sum(ufs.values())}
    r = store.resolve_place(date_str, nome, sigla)
    if r is None:
        raise HTTPException(404, f"Local '{q_}' não encontrado")
    return {"snapshot_date": date_str, "place": q_, **({"uf": sigla} if sigla else {}), **r}


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
