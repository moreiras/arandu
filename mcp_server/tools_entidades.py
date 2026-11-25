# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tools de entidade do MCP: snapshots, ASNs, IXPs, PTTs externos, CDNs e prefixos."""
from __future__ import annotations

from typing import Optional

from api.services import decix_rs as _decix_rs
from mcp_server.contexto import _MEMBER_LIST_FIELDS, _SORT_FIELDS, _resolve, _store, mcp

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_snapshots() -> dict:
    """Lista as datas de snapshot disponíveis e qual é a mais recente.

    Cada snapshot é imutável. As demais tools usam a mais recente por padrão.
    """
    snaps = _store.list_snapshots()
    return {"latest": _store.latest(), "count": len(snaps), "snapshots": snaps}


@mcp.tool()
def get_snapshot(date: Optional[str] = None) -> dict:
    """Resumo e metadados de um snapshot do Arandurape.

    Retorna os números agregados do snapshot: totais de ASNs BR/global, cobertura
    IPv6/IPv4 da tabela global e dos IXPs, espaço de endereçamento, e status de
    coleta de cada fonte. Use sem `date` para o snapshot mais recente.

    Args:
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    summary = _store.summary(d)
    if summary is None:
        raise ValueError(f"Snapshot {d} não possui summary.json.")
    return summary


@mcp.tool()
def get_asn(asn: int, date: Optional[str] = None) -> dict:
    """Documento completo de um ASN — o principal objeto de cruzamento do projeto.

    Inclui: prefixos do Registro.br (RIR, autoritativos) vs. prefixos observados na
    tabela global; presença direta (peering físico) vs. originador em cada IXP do
    IX.br; validação RPKI; usuários finais estimados (APNIC); presença em IXPs
    externos; nome e CNPJ (ASNs BR); `relacoes` (provedores/clientes/pares inferidos,
    com probabilidade e nível — ver o glossário). `upstreams_*`/`downstreams_*` são só
    vizinhos observados no AS_PATH (deprecado). Quando disponíveis: campo `scm` (outorgas SCM
    Anatel associadas ao CNPJ do AS; sem telefone/e-mail). Para listar/filtrar outorgas SCM use `outorga_lista` ou `query` com
    collection="scms". Contatos NÃO vêm aqui: `contacts_available` só conta (PeeringDB, Anatel, Receita); os valores saem por
    `asn_contatos`, só com chave de MCP e com a cota de contatos da conta.

    Args:
        asn: Número do Sistema Autônomo (ex.: 22548).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    from api.privacidade import sem_contatos
    from api.routes.asns import documento_asn
    d = _resolve(date)
    doc = documento_asn(_store, d, asn)               # o de GET /asns/{asn}, com `contacts_available`; o `geo_org` (Receita) traz telefone
    if doc is None:
        raise ValueError(f"AS{asn} não encontrado no snapshot {d}.")
    return sem_contatos(doc)


@mcp.tool()
def get_ixp(code: str, date: Optional[str] = None) -> dict:
    """Documento completo de um IXP (ponto de troca) do IX.br.

    Inclui métricas por família (IPv6/IPv4): rotas e prefixos únicos, espaço de
    endereçamento, ASes diretos vs. originadores, cobertura de prefixos BR, e
    comparação com a tabela global. Cada família traz `coleta` (ok, vazia, missing):
    `vazia` é coleta que funcionou com o looking glass respondendo tabela vazia (zero
    rotas; as porcentagens saem null). Não trate como 0% de cobertura nem atribua causa.

    As listas grandes de membros (asn_direct, asn_stub, br_asns_direct,
    br_asns_origin) ficam em `ixp_members` para não inflar a resposta — aqui vêm
    só as métricas escalares + a lista de membros oficiais do IX.br.

    Args:
        code: Código do IXP (ex.: "sp", "rj", "ce"). Ver ixp_lista.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    code = code.lower()
    doc = _store.ixp_detail(d, code)
    if doc is None:
        raise ValueError(f"IXP '{code}' não encontrado no snapshot {d}.")

    # Versão slim — listas grandes vão para ixp_members (paridade com /ixps/{code}).
    slim: dict = {}
    for k, v in doc.items():
        if k in ("v4", "v6") and isinstance(v, dict):
            slim[k] = {fk: fv for fk, fv in v.items() if fk not in _MEMBER_LIST_FIELDS}
        else:
            slim[k] = v
    members = _store._load_ixp_members(d, code)
    if members:
        slim["asn_members"] = sorted(members)
        slim["ixbr_members_count"] = len(members)
    return slim


def _sede_do_asn(d: str, asn: int) -> dict:
    """Município e UF da sede e o centroide do município: a coordenada geocodificada do endereço não sai (D1)."""
    from api.privacidade import geo_org_publico
    from core.geoip import centroide_municipio

    org = geo_org_publico((_store.asn_detail(d, asn) or {}).get("geo_org")) or {}
    cadastro = (_store._load_geo_orgs(d) or {}).get(asn) or {}
    municipio = org.get("municipio") or org.get("city") or cadastro.get("city")
    uf = org.get("uf") or cadastro.get("uf")
    ibge = org.get("codigo_municipio_ibge")
    ponto = None
    if ibge and (c := _store.municipio_centroide(str(ibge))):
        ponto = (c[1], c[0])
    elif municipio and uf and (c := centroide_municipio(municipio, uf)):
        ponto, municipio = (c[0], c[1]), c[2]
    return {
        "asn": asn,
        "name": _store.asn_map(d).get(asn, {}).get("name"),
        "municipio": municipio, "uf": uf, "codigo_municipio_ibge": ibge,
        "lat": ponto[0] if ponto else None, "lon": ponto[1] if ponto else None,
        "posicao": "centroide do município da sede (IBGE)" if ponto else None,
        "source": "Registro.br/CNPJ → Receita (município da sede)" if municipio else None,
    }


@mcp.tool()
def geo_coords(
    asn: Optional[int] = None,
    ixp: Optional[str] = None,
    date: Optional[str] = None,
) -> dict:
    """Coordenadas (lat/lon) de um AS e/ou de um PTT, sem GeoJSON/Hilbert.

    Resposta enxuta para perguntas de localização textual ("onde fica o AS X / o
    PTT Y?"), evitando os blobs de visualização. De AS: município e UF da sede
    (Registro.br/CNPJ → Receita) e o centroide do município (IBGE); o endereço e a
    posição exata da sede não são servidos. De PTT, as localizações dos PIX do IX.br.

    Args:
        asn: Número do AS para localizar (opcional).
        ixp: Código do IXP para localizar (opcional).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    if asn is None and ixp is None:
        raise ValueError("Informe ao menos um de: asn, ixp.")
    d = _resolve(date)
    result: dict = {"snapshot_date": d}

    if asn is not None:
        result["asn"] = _sede_do_asn(d, asn)

    if ixp is not None:
        code = ixp.lower()
        idx = {e["code"]: e for e in _store.ixp_index(d)}
        pix = [
            {
                "name": f["properties"].get("name"),
                "lat": f["geometry"]["coordinates"][1],
                "lon": f["geometry"]["coordinates"][0],
            }
            for f in _store.pix_map(d).get("features", [])
            if f.get("properties", {}).get("ixp_code") == code
        ]
        result["ixp"] = {
            "code": code,
            "name": idx.get(code, {}).get("name"),
            "uf": idx.get(code, {}).get("uf"),
            "pix": pix,
            "source": "config/pix.yaml (localizações dos PIX do IX.br)",
        }

    return result


@mcp.tool()
def list_asns(
    q: Optional[str] = None,
    br_only: bool = False,
    ipv6_only: bool = False,
    sort_by: Optional[str] = None,
    sort_desc: bool = False,
    page: int = 1,
    limit: int = 100,
    date: Optional[str] = None,
) -> dict:
    """Busca rápida de ASN por nome ou número (paginada), p/ depois chamar get_asn.

    Use SÓ para localizar um AS pelo texto. Para QUALQUER filtro, cruzamento,
    ordenação por métrica ou agregação, use `query` (collection="asns") — ela é mais
    expressiva e os campos estão em describe_schema.
    Cada item traz contagens de prefixos RIR vs. global, presença em IXPs, usuários
    APNIC e flags (has_ipv6, has_rpki, has_aspa).

    Args:
        q: Busca por nome (substring, case-insensitive) ou número exato do AS.
        br_only: Apenas ASNs com registro no Registro.br.
        ipv6_only: Apenas ASNs com prefixos IPv6 observados.
        sort_by: Campo de ordenação. Um de: asn, name, apnic_users, apnic_v6_users,
            pct_v6, ixps_direct_count, ixps_origin_v4_count, ixps_origin_v6_count,
            has_rpki, has_aspa, external_ixps_count.
        sort_desc: True para ordem decrescente.
        page: Página (>=1). limit: itens por página (1..1000).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    limit = max(1, min(limit, 1000))
    page = max(1, page)
    index = _store.asn_index(d)

    if br_only:
        index = [a for a in index if a.get("is_br")]
    if ipv6_only:
        index = [a for a in index if a.get("has_ipv6")]
    if q:
        ql = q.lower()
        index = [
            a for a in index
            if ql in str(a.get("asn", "")) or ql in (a.get("name") or "").lower()
        ]

    if sort_by and sort_by in _SORT_FIELDS:
        if sort_by == "name":
            index = sorted(index, key=lambda a: (a.get("name") or "").lower(), reverse=sort_desc)
        else:
            def sort_key(a):
                v = a.get(sort_by)
                if v is None:
                    return (1, 0)
                if isinstance(v, bool):
                    v = 1 if v else 0
                return (0, -v if sort_desc else v)
            index = sorted(index, key=sort_key)

    total = len(index)
    start = (page - 1) * limit
    return {
        "snapshot_date": d,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 0,
        "items": index[start : start + limit],
    }


@mcp.tool()
def get_asn_paths(asn: int, date: Optional[str] = None) -> dict:
    """Cadeias AS_PATH observadas em cada IXP onde o AS é originador (não direto).

    Mostra por quais ASes intermediários os prefixos do AS chegam a cada IXP, com
    metadados dos nós do caminho (path_node_meta). `ixp_paths` é {} se não houver.

    Args:
        asn: Número do AS.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    result = _store.asn_paths(d, asn)
    if result is None:
        raise ValueError(f"AS{asn} não encontrado no snapshot {d}.")
    return result


@mcp.tool()
def get_asn_ixp_peers(asn: int, date: Optional[str] = None) -> dict:
    """Estatísticas de peering deste AS em cada IXP onde faz peering direto (v6/v4).

    Para cada IXP direto: total_prefixes, own/third_prefixes, origin_asns, espaço /24.
    `peers` é {} se o AS não tiver peering direto.

    Args:
        asn: Número do AS.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    result = _store.asn_ixp_peers(d, asn)
    if result is None:
        raise ValueError(f"AS{asn} não encontrado no snapshot {d}.")
    return result


@mcp.tool()
def asn_ix_presence(date: Optional[str] = None) -> dict:
    """[ÚLTIMO RECURSO — despejo do índice inteiro] Participação reversa de TODOS os ASNs.

    Retorna {asn: {"m": [codes IX.br membro], "o": [codes onde origina prefixos BR]}}
    para todos os ASes (dezenas de milhares de entradas — resposta enorme).
    Quase nunca é o que você quer: para um AS, use get_asn (campo ixp_presence); para
    "quem está no PTT X / em ≥N PTTs", use `query` com ixps_sessao_rs/ixps_origin.

    Args:
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    return _store.asn_ix_presence(d)


@mcp.tool()
def list_ixps(
    status: Optional[str] = None,
    uf: Optional[str] = None,
    date: Optional[str] = None,
) -> dict:
    """Lista os IXPs do IX.br com métricas-resumo por família (v6/v4).

    Cada família traz `coleta`: `ok` (o looking glass devolveu rotas), `vazia` (a coleta funcionou e o looking glass respondeu com a
    tabela vazia: zero rotas coletadas, não zero de cobertura; as porcentagens saem null) ou `missing`. Não atribua causa à tabela vazia.

    Args:
        status: Filtro de coleta: ok (rotas nas duas famílias) | partial (uma família vazia ou ausente) | missing.
        uf: Filtro por UF (sigla de 2 letras, ex.: SP).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    index = _store.ixp_index(d)
    if status:
        index = [e for e in index if e.get("status") == status]
    if uf:
        index = [e for e in index if (e.get("uf") or "").upper() == uf.upper()]
    return {"snapshot_date": d, "count": len(index), "ixps": index}


@mcp.tool()
def ixp_members(code: str, date: Optional[str] = None) -> dict:
    """Listas de membros de um IXP por família: asn_direct, asn_stub, br_asns_direct,
    br_asns_origin.

    Complementa get_ixp (que traz só as métricas escalares). Pode ser volumoso para
    IXPs grandes.

    Args:
        code: Código do IXP (ex.: "sp").
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    code = code.lower()
    doc = _store.ixp_detail(d, code)
    if doc is None:
        raise ValueError(f"IXP '{code}' não encontrado no snapshot {d}.")
    result: dict = {"snapshot_date": d, "ixp": code}
    for afi in ("v4", "v6"):
        v = doc.get(afi)
        result[afi] = (
            {k: v[k] for k in _MEMBER_LIST_FIELDS if k in v}
            if isinstance(v, dict) else {}
        )
    return result


@mcp.tool()
def ixp_peers(code: str, afi: str = "v4", date: Optional[str] = None) -> dict:
    """Estatísticas de prefixos por peer direto de um IXP.

    Por peer: total_prefixes, own_prefixes, third_prefixes (repassados), origin_asns,
    own_space_24 / third_space_24.

    Args:
        code: Código do IXP (ex.: "sp").
        afi: Família de endereços: "v4" ou "v6".
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    result = _store.ixp_peers_stats(d, code.lower(), afi)
    if result is None:
        raise ValueError(f"Sem dados de peers para IXP '{code}' AFI '{afi}' em {d}.")
    return {"snapshot_date": d, "ixp": code.lower(), "afi": afi, "peers": result}


@mcp.tool()
def ixp_potential(code: str, date: Optional[str] = None) -> dict:
    """Indicadores de potencial de crescimento de um PTT do IX.br.

    nearby_asn_count (ASes a ≤80 km de um PIX que ainda não participam),
    v4_prefixes_24 / v6_prefixes_48 (prefixos anunciados ∪ geolocalizados a ≤80 km),
    estimated_users_total (usuários estimados sobre a union do potencial).

    Args:
        code: Código do IXP (ex.: "sp").
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    result = _store.ixp_potential(d, code.lower())
    if result is None:
        raise ValueError(f"IXP '{code}' não encontrado no snapshot {d}.")
    return result


@mcp.tool()
def ixp_estimated_users(code: str, date: Optional[str] = None) -> dict:
    """Usuários finais BR estimados visíveis via os prefixos IPv4 originados num IXP.

    Soma, por AS BR originador, usuarios_APNIC × (espaço IPv4 visível no IXP / espaço
    IPv4 total do AS). Retorna estimated_users e contributing_asns.

    Args:
        code: Código do IXP (ex.: "sp").
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    return _store.ixp_estimated_users(d, code.lower())


@mcp.tool()
def all_ixp_estimated_users(date: Optional[str] = None) -> dict:
    """Usuários finais BR estimados (IPv4) para todos os IXes: {code: estimated_users}.

    Mesma metodologia de ixp_estimated_users, aplicada a cada IXP.

    Args:
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    return _store.all_ixp_estimated_users(d)


@mcp.tool()
def asn_names(date: Optional[str] = None) -> dict:
    """[ÚLTIMO RECURSO — despejo do índice inteiro] Mapa {asn: nome} de TODOS os ASes.

    ~100k entradas (resposta enorme). Para um AS, use get_asn; para buscar por nome,
    use list_asns(q=...); para filtrar/cruzar por nome, use `query` (campo name).

    Args:
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    return {"snapshot_date": d, "names": _store.asn_names(d)}


# ---------------------------------------------------------------------------
# PTTs externos (PeeringDB)
# ---------------------------------------------------------------------------

@mcp.tool()
def list_external_ixps(country: Optional[str] = None, date: Optional[str] = None) -> dict:
    """Lista os IXPs externos ao IX.br (PeeringDB), com membros totais e brasileiros.

    Args:
        country: Filtro por código ISO de país (ex.: BR, NL, US).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    index = _store.external_ixp_index(d)
    if index is None:
        raise ValueError(f"Dados de IXPs externos indisponíveis no snapshot {d}.")
    ixps = index.get("ixps", [])
    if country:
        ixps = [e for e in ixps if (e.get("country") or "").upper() == country.upper()]
    return {"snapshot_date": index.get("snapshot_date", d), "count": len(ixps), "ixps": _decix_rs.com_resumo(ixps, _store.decix_rs_doc(d))}


@mcp.tool()
def get_external_ixp(code: str, br_only: bool = False, date: Optional[str] = None) -> dict:
    """Documento de um IXP externo: lista de membros com marcação de ASNs brasileiros.

    Para "decix-sp" e "decix-rj" traz também `route_server` (Alice-LG do DE-CIX): sessões, ASNs diretos (sessão up) e de origem (piso), membros e comparação com o IX.br da cidade.

    Args:
        code: Código do IXP externo (ex.: "amsix", "decix-fra").
        br_only: Se true, retorna apenas membros brasileiros.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    doc = _store.external_ixp_detail(d, code)
    if doc is None:
        raise ValueError(f"IXP externo '{code}' não encontrado no snapshot {d}.")
    doc = dict(doc)
    if br_only:
        doc["members"] = [m for m in doc.get("members", []) if m.get("is_br")]
    # nome de cada membro pelo ASN: a Store corrige os snapshots que gravaram o nome do PTT
    from api.privacidade import sem_contatos            # o documento do IXP externo não deve levar contato

    return sem_contatos(_resumir_rs(_decix_rs.anexar(doc, _store.decix_rs_doc(d), code)))


# listas do route server do DE-CIX que passam de dezenas de KB: no MCP saem como contagem (a API /external-ixps/{code} segue com elas)
_LISTAS_RS = ("asn_origin", "br_asns_origin", "rotas", "membros")


def _resumir_rs(doc: dict) -> dict:
    rs = doc.get("route_server")
    if not isinstance(rs, dict):
        return doc
    rs = dict(rs)
    for k in _LISTAS_RS:
        if isinstance(rs.get(k), (list, dict)):
            rs[f"{k}_total"] = len(rs.pop(k))
    rs["_nota"] = "Listas de origem, rotas e membros do route server resumidas em contagens; completas em GET /api/v1/external-ixps/{code}."
    return {**doc, "route_server": rs}


# ---------------------------------------------------------------------------
# CDNs / CAPs
# ---------------------------------------------------------------------------

@mcp.tool()
def cdn_presence(date: Optional[str] = None) -> dict:
    """Matriz de presença de CDNs e CAPs nos IXPs do IX.br e externos.

    Para cada CDN/CAP: ASNs, categorias, e em quais IXPs (ixbr/externos) está presente.

    Args:
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    data = _store.cdn_presence(d)
    if data is None:
        raise ValueError(f"Dados de presença de CDNs indisponíveis no snapshot {d}.")
    return data


# ---------------------------------------------------------------------------
# Prefixos BR geolocalizados
# ---------------------------------------------------------------------------

@mcp.tool()
def list_prefixes(
    ip_version: Optional[int] = None,
    uf: Optional[str] = None,
    origin_asn: Optional[int] = None,
    page: int = 1,
    limit: int = 100,
    date: Optional[str] = None,
) -> dict:
    """Lista paginada de prefixos BR (Registro.br) com UF e país.

    Para filtros compostos ou agregação use `query` (collection="prefixes"); esta tool só faz filtros simples.
    Campos: prefix, ip_version, origin_asn, uf, country, geo_confidence, geo_source.
    Latitude, longitude e cidade por prefixo não são servidas.

    Args:
        ip_version: Filtra por versão IP (4 ou 6).
        uf: Filtra por UF (2 letras).
        origin_asn: Filtra por ASN originador.
        page: Página (>=1). limit: itens por página (1..1000).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    limit = max(1, min(limit, 1000))
    page = max(1, page)
    gj = _store.geo_map(d, "prefixes")
    if gj is None:
        raise ValueError(f"Geolocalização de prefixos indisponível no snapshot {d}.")
    feats = gj.get("features", [])
    if ip_version is not None:
        feats = [f for f in feats if (f.get("properties") or {}).get("ip_version") == ip_version]
    if uf is not None:
        u = uf.upper()
        feats = [f for f in feats if ((f.get("properties") or {}).get("uf") or "").upper() == u]
    if origin_asn is not None:
        feats = [f for f in feats if (f.get("properties") or {}).get("origin_asn") == origin_asn]
    total = len(feats)
    start = (page - 1) * limit
    from core.geoip import sem_posicao
    items = [sem_posicao(f.get("properties") or {}) for f in feats[start : start + limit]]
    return {
        "snapshot_date": d,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 0,
        "items": items,
    }


@mcp.tool()
def get_prefix(prefix: Optional[str] = None, ip: Optional[str] = None, date: Optional[str] = None) -> dict:
    """Detalhe de um prefixo: detentor no Registro.br, origem observada, RPKI do anúncio, UF e país; o mesmo de `GET /prefixes/{prefix}`.

    Aceita qualquer grafia CIDR e responde na forma canônica. Abre alocações do Registro.br e rotas observadas fora delas.
    `registro_asn` é o detentor (AS a que o Registro.br associa a alocação igual ou que contém o prefixo); `observed_origin_asn` é a
    origem observada (tabela global coletada, uma origem por prefixo, ou route servers do IX.br; ver `observed_origin_fonte`), nula
    se o prefixo não é anunciado como está. Os dois podem diferir por motivos legítimos. `rpki_observado` valida só o par
    anunciado (`nao_avaliado` sem anúncio), com `motivo` e os ROAs de qualquer AS que cobrem o prefixo. `origin_asn` está
    depreciado: é o AS do Registro.br, não a origem observada. Latitude, longitude e cidade do prefixo não são servidas.

    Com `ip` (em vez de `prefix`) acha a alocação do Registro.br mais específica que contém o endereço (longest-prefix match) e
    devolve só `prefix`, `ip_version`, `registro_asn`, `observed_origin_asn`, `origin_asn` e `consulta`: é uma consulta de
    roteamento, sem posição (nem UF). Para o detalhe, chame de novo com `prefix`.

    Args:
        prefix: Prefixo CIDR (ex.: "2804::/32" ou "177.75.0.0/20"). Use este OU ip.
        ip: Endereço IPv6 ou IPv4 sem máscara (ex.: "200.160.2.3").
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    from fastapi import HTTPException
    from api.routes.prefixes import PrefixoAusente, PrefixoInvalido, detalhe_prefixo, resumo_do_ip

    d = _resolve(date)
    if not ip and not prefix:
        raise ValueError("Informe prefix ou ip.")
    try:
        return resumo_do_ip(_store, d, ip) if ip else detalhe_prefixo(_store, d, prefix)
    except (PrefixoInvalido, PrefixoAusente) as exc:
        raise ValueError(str(exc))
    except HTTPException as exc:
        raise ValueError(str(exc.detail))
