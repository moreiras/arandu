# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Camada de consulta genérica do MCP: `describe_schema`, `query`, `get_asns`, resolvedores e analíticos de PTT."""
from __future__ import annotations

from typing import Optional

from api.query import QueryError
from mcp_server.contexto import _resolve, _store, mcp

# ---------------------------------------------------------------------------
# Camada de consulta genérica (a forma preferida para cruzamentos/filtros/agg)
# ---------------------------------------------------------------------------

@mcp.tool()
def describe_schema(collection: Optional[str] = None) -> dict:
    """Campos, tipos, enums e exemplos de UMA collection de `query`, com as receitas dela. Sem `collection`, o índice das collections.

    Chame com collection (ex.: "municipios") antes de filtrar campos que você não conhece.

    Args:
        collection: A collection (ex.: "asns", "municipios", "operadoras"). Omita para o índice (nome e descrição de cada uma).
    """
    from api.query_catalogo import COLECOES_ALIAS, OPS_GUIDE, RECIPES, SCHEMA
    from mcp_server import guia
    sintaxe = {
        "filter": '{"field": "uf", "op": "eq", "value": "SC"} ou {"and": [...]} / {"or": [...]} / {"not": ...}',
        "ops": OPS_GUIDE,
        "sort": '[{"field": "apnic_users", "dir": "desc"}]',
        "aggregate": '[{"fn": "count"}, {"fn": "sum", "field": "apnic_users"}] com group_by: ["uf"]. count sem field conta linhas, com field conta valores não nulos; '
                     'sort, limit e page valem para os grupos (sort pelo alias, ex. sum_apnic_users, ou por campo de group_by); total_grupos na resposta',
        "near": '{"ixp": "vix", "radius_km": 50} | {"place": "Mossoró", "radius_km": 100} | {"point": [lat, lon], "radius_km": N}',
    }
    if collection is None:
        # o catálogo inteiro tinha 126 KB: não cabe no contexto de um modelo pequeno
        return {"collections": {k: _primeira_frase(v.get("description", "")) for k, v in SCHEMA.items()}, "sintaxe": sintaxe,
                "ferramenta_detalhe": guia.DETALHE_DA_COLLECTION,
                "_nota": "Chame describe_schema(collection=...) para os campos de uma collection."}
    r = _store.query_schema(collection)                       # valida o nome e traz o bloco da collection
    # campos primeiro e só as receitas desta collection: com as 26 receitas de todas na frente (~20 KB), um cliente que corta a
    # resposta nunca veria os campos
    atual = COLECOES_ALIAS.get(collection, collection)          # nome antigo (D12): descreve a collection nova e avisa
    receitas = [x for x in RECIPES if (x.get("args") or {}).get("collection") == atual]
    return {"collection": atual, **({"aviso_obsoleta": r["aviso_obsoleta"]} if r.get("aviso_obsoleta") else {}), "descricao": r.get("description"), "chave": r.get("key"), "campos": r.get("fields"),
            **({"geo": r["geo"]} if r.get("geo") else {}), "sintaxe": sintaxe, "receitas": receitas,
            "ferramenta_detalhe": guia.DETALHE_DA_COLLECTION.get(atual)}


def _primeira_frase(texto: str, teto: int = 140) -> str:
    frase = texto.split(". ")[0].strip()
    return frase if len(frase) <= teto else frase[: teto - 1].rstrip() + "…"


@mcp.tool()
def query(
    collection: str,
    filter: Optional[dict] = None,
    select: Optional[list] = None,
    sort: Optional[list] = None,
    group_by: Optional[list] = None,
    aggregate: Optional[list] = None,
    near: Optional[dict] = None,
    page: Optional[int] = None,
    limit: Optional[int] = None,
    date: Optional[str] = None,
    de: Optional[str] = None,
) -> dict:
    """Consulta genérica sobre os dados — filtre, ordene, agregue e cruze.

    A forma preferida para perguntas analíticas. Veja os campos com describe_schema.

    - filter: and/or/not + predicados {field, op, value}. Ops: eq, ne, gt, gte, lt,
      lte, in, nin, contains (substring/pertinência em arrays), ncontains, exists.
      Dot-path suportado (ex.: "v4.br_prefix_coverage_pct").
    - group_by + aggregate (fn: count/sum/avg/min/max/distinct) → modo agregação.
    - near: {"ixp":code | "place":nome | "point":[lat,lon], "radius_km":N} — filtro
      geográfico (ANDado ao filter); raio em km a partir do PIX do PTT, do centroide
      do município, ou de um ponto.

    Álgebra de conjuntos na mesma collection sai via filtro composto — ex.: diretos no
    SP mas não no RJ: ixps_direct contains "sp" AND ncontains "rj".

    Args:
        collection: asns | ixps | external_ixps | cdns | prefixes | global_prefixes | scms | smps | stfcs | seacs |
            operadoras | acessos_municipio | operadoras_movel | acessos_movel_municipio | socios.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
        de: Só para `eventos` e `series_asn` (histórico, que não depende de `date`): data inicial (AAAA-MM-DD). Sem chave de MCP é obrigatório e
            não pode ser anterior ao snapshot atual mais antigo.
    """
    d = _resolve(date)
    body: dict = {}                       # sem `limit`/`page` a lista vale 100 por página e a agregação devolve todos os grupos
    if page is not None:
        body["page"] = page
    if limit is not None:
        body["limit"] = limit
    if de is not None:
        body["de"] = de
    if filter is not None:
        body["filter"] = filter
    if select is not None:
        body["select"] = select
    if sort is not None:
        body["sort"] = sort
    if group_by is not None:
        body["group_by"] = group_by
    if aggregate is not None:
        body["aggregate"] = aggregate
    if near is not None:
        body["near"] = near
    try:
        return _store.query(d, collection, body)
    except QueryError as exc:
        raise ValueError(str(exc))


@mcp.tool()
def get_asns(asns: list, fields: Optional[list[str]] = None, date: Optional[str] = None) -> dict:
    """Busca vários documentos de ASN numa única chamada (eficiência de tokens).

    Args:
        asns: Lista de números de AS (máx. 100 por chamada).
        fields: Campos do primeiro nível a manter em cada documento (ex.: ["name", "ixp_presence"]); `asn` sempre fica.
            Omita para o documento completo — que é grande: projete quando só precisar de alguns campos.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    if len(asns) > 100:
        raise ValueError("Máximo de 100 ASNs por chamada de get_asns. Pagine a lista.")
    from api.privacidade import sem_contatos
    from api.routes.asns import documento_asn
    d = _resolve(date)
    docs = []
    missing = []
    for a in asns:
        doc = documento_asn(_store, d, int(a))                   # o de GET /asns/{asn}; contatos só em contagem (`contacts_available`)
        if doc is not None:
            doc = sem_contatos(doc)
        if doc is not None and fields:
            doc = {k: v for k, v in doc.items() if k in fields or k == "asn"}
        (docs.append(doc) if doc is not None else missing.append(int(a)))
    return {"snapshot_date": d, "count": len(docs), "asns": docs, "not_found": missing}


@mcp.tool()
def resolve_place(place: str, date: Optional[str] = None) -> dict:
    """Resolve um município em coordenadas (centroide do IBGE; sem ele, a mediana das sedes arredondada a 0,1°; `posicao` diz qual).

    Útil para alimentar `near.point` ou consultas geográficas por cidade.

    Args:
        place: Nome do município (ex.: "Vitória"; com homônimos, "Bom Jesus, PI").
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    from mcp_server.entrada import separa_uf
    d = _resolve(date)
    nome, uf = separa_uf(place)                          # "Mossoró, RN" e "Boa Vista (Roraima)" falhavam
    if not uf:
        ufs = _store.place_ufs(d, nome)
        if len(ufs) > 1:                                 # homônimos: a mediana das UFs juntas cai longe de todas (LOC-E4)
            raise ValueError(f"'{place}' existe em mais de uma UF ({', '.join(ufs)}): informe a UF, por exemplo '{nome}, {next(iter(ufs))}'.")
    r = _store.resolve_place(d, nome, uf) if uf else _store.resolve_place(d, nome)
    if r is None:
        raise ValueError(f"Local '{place}' não encontrado no snapshot {d}." + _sugestoes_de_municipio(d, place))
    return {"snapshot_date": d, "place": place, **({"uf_informada": uf} if uf else {}), **r}


def _sugestoes_de_municipio(d: str, place: str) -> str:
    try:
        from mcp_server.entrada import casa_municipio
        from mcp_server.tools_mercado import _Sici
        casados, perto = casa_municipio(place, list(_Sici("fixa").municipios(d).values()))
        nomes = [f"{m['nome']} ({m['uf']})" for m in casados[:5]] or perto
        return f" Parecidos: {', '.join(nomes)}." if nomes else ""
    except Exception:
        return ""


@mcp.tool()
def resolve_operator(name: str, date: Optional[str] = None) -> dict:
    """Resolve uma marca/operador em ASNs (CDN/CAP + nome + raiz de CNPJ).

    Use o resultado em operator_reach para marcas com vários ASNs (Claro, Vivo, …).

    Args:
        name: Marca/operador (ex.: "Globo", "Claro").
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    return _store.resolve_operator(d, name)


@mcp.tool()
def ixp_nearby(code: str, radius_km: float = 80.0, limit: int = 500, date: Optional[str] = None) -> dict:
    """ASes com prefixos geolocalizados a ≤ radius_km de um PTT, por status e gap.

    Para cada AS próximo: classificação de presença no PTT (direct/origin/absent) e
    quantos dos seus prefixos próximos ainda NÃO estão anunciados no PTT. Generaliza a
    seção "Potencial" com raio parametrizável.

    Args:
        code: Código do IXP (ex.: "to" = Palmas).
        radius_km: Raio em km a partir dos PIX do PTT.
        limit: Máximo de ASes retornados.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    try:
        return _store.ixp_nearby_breakdown(d, code.lower(), radius_km, limit)
    except QueryError as exc:
        raise ValueError(str(exc))


@mcp.tool()
def operator_reach(asns: list, date: Optional[str] = None) -> dict:
    """Alcance de usuários finais BR de um operador (conjunto de ASes) via seus PTTs.

    Conta em quantos PTTs o operador participa e quantos usuários finais BR alcança —
    usuários visíveis pelos prefixos anunciados em cada PTT (metodologia de
    estimated_users), de-duplicados entre PTTs. Use resolve_operator para obter os ASNs.

    Args:
        asns: Lista de ASNs do operador (ex.: [28604]).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    return _store.operator_reach(d, [int(a) for a in asns])
