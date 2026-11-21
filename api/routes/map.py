# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoints de mapa geográfico — GET /map/asns e GET /map/prefixes.

Retorna GeoJSON com pontos de ASNs geolocalizados e polígonos/pontos de prefixos
BR, para renderização no mapa interativo do frontend.
"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response

from api import query as q
from api.ratelimit import limiter, LIMIT_HEAVY
from api.store import Store

router = APIRouter()


def _filter_geojson(geojson: dict, uf: Optional[str]) -> dict:
    """Retorna novo FeatureCollection com filtro opcional por UF."""
    if not uf:
        return geojson
    uf_upper = uf.upper()
    features = [
        f for f in geojson.get("features", [])
        if (f.get("properties") or {}).get("uf", "").upper() == uf_upper
    ]
    return {**geojson, "features": features}


@router.get(
    "/map/asns",
    summary="Mapa de ASNs geolocalizados",
    description="""
Retorna um GeoJSON FeatureCollection com os ASNs brasileiros que possuem geolocalização
derivada do endereço da organização (via CNPJ → BrasilAPI → Nominatim).

Cada Feature contém as propriedades: `asn`, `name`, `uf`, `city`,
`geo_confidence` (`exact_address`, `cep_centroid`, `city_centroid`), `geo_source`.

Use `?uf=SP` para filtrar por estado.
""",
)
def map_asns(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
    uf: Optional[str] = Query(
        None,
        description="Filtrar por UF (sigla de dois caracteres, ex: SP, RJ, RS).",
        min_length=2,
        max_length=2,
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    geojson = store.geo_map(date_str, "asns")
    if geojson is None:
        raise HTTPException(404, "Dados de geolocalização de ASNs não disponíveis para este snapshot")

    return _filter_geojson(geojson, uf)


@router.get(
    "/map/asns-overview",
    summary="Visão geral dos ASNs brasileiros",
    description="""
Retorna um GeoJSON FeatureCollection combinando:

- **ASNs BR** (alocados pelo Registro.br) com propriedade `visibility`:
  `both` (IPv6+IPv4), `v4_only`, `v6_only` ou `none` (não visível na FT).
- **PIX de PTTs** do IX.br com `role: "pix"`, `ixp_code`, `name`, `ixp_name`.
""",
)
def map_asns_overview(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    geojson = store.asns_overview_map(date_str)
    if geojson is None:
        raise HTTPException(404, "Dados de geolocalização não disponíveis para este snapshot")

    return geojson


@router.get(
    "/map/pix",
    summary="Mapa dos PIX (PTTs) do IX.br",
    description="""
Retorna um GeoJSON FeatureCollection com os PIX (Pontos de Intercâmbio físicos) do IX.br
que possuem localização conhecida (config/pix.yaml).

Cada Feature contém: `role` (`"pix"`), `ixp_code`, `name` (nome do PIX), `ixp_name`.
""",
)
def map_pix(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return store.pix_map(date_str)


_MAP_QUERY_EXAMPLE = {
    "filter": {"and": [
        {"field": "is_br",    "op": "eq", "value": True},
        {"field": "has_rpki", "op": "eq", "value": False},
    ]},
    "near": {"ixp": "mao", "radius_km": 80},
    "layers": ["asns_geo", "pix"],
    "color_by": "rpki",
}


@router.post(
    "/map/query",
    summary="Mapa Explorer — consulta geográfica composável",
    description="""
Retorna um GeoJSON FeatureCollection filtrando ASes e prefixos por uma combinação
de filtros booleanos, proximidade geográfica e seleção de camadas.

## Parâmetros do body

| Campo | Tipo | Descrição |
|---|---|---|
| `filter` | objeto | Filtro booleano sobre a collection `asns` (DSL: `and/or/not` + predicados) |
| `near` | objeto | Raio em km a partir da **sede** de AS: `{"ixp":"mao","radius_km":80}` |
| `near_prefixes` | objeto | Raio em km a partir dos **prefixos geolocalizados** do AS (em vez da sede) |
| `layers` | lista | Camadas a retornar: `asns_geo`, `prefixes_v4`, `prefixes_v6`, `pix`, `scms`, `outorgas_scm`, `prefixos_ix_v4`, `prefixos_ix_v6` |
| `color_by` | string | Atributo de cor para `asns_geo`: `visibility`, `rpki`, `aspa`, `porte`, `pct_v6`, `outorga` |
| `scm_mode` | string | Para `outorgas_scm`: `todas` (default), `com_asn`, `sem_asn` |
| `ix_apply_filter` | bool | Prefixos do PTT só com origem no recorte de ASes (default `false`) |

A camada `scms` retorna as outorgas SCM **sem ASN** (operadores licenciados ausentes do BGP);
a interseção AS∩SCM aparece via `asns_geo` com `color_by="outorga"`. A camada
`outorgas_scm` traz todas as outorgas (com `has_asn`); as com ASN respeitam o
recorte, as sem ASN só aparecem sem filtro por atributos (a proximidade é aplicada
à localização da própria outorga). O campo virtual
`has_scm` (eq true/false) também pode ser usado no `filter` para isolar ASes com/sem outorga.

## Sintaxe de filtro

Mesma DSL de `POST /query/asns`. Exemplos:

```json
{"field": "has_rpki", "op": "eq", "value": false}
{"field": "ixps_direct", "op": "contains", "value": "sp"}
{"field": "pct_v6", "op": "gte", "value": 30}
{"field": "porte", "op": "eq", "value": "MICRO EMPRESA"}
{"and": [...], "or": [...], "not": {...}}
```

## Operadores de grupo

`and`, `or`, `not` com filhos aninhados arbitrariamente. XOR deve ser expandido
pelo cliente em `(A AND NOT B) OR (NOT A AND B)`.

## Propriedades das features

- `asns_geo`: herda todas as propriedades de `maps/asns.geojson` + `layer` + `color_value`
- `prefixes_v4/v6`: herda de `maps/prefixes.geojson` **agregado por ASN e município** (`prefix_count`, sem o prefixo) + `layer`
- `pix`: propriedades padrão dos PIX do IX.br (`role`, `ixp_code`, `name`, `ixp_name`)

## Casos de uso

```json
// ASes a 80 km do PTT de Manaus sem RPKI
{
  "filter": {"field": "has_rpki", "op": "eq", "value": false},
  "near": {"ixp": "mao", "radius_km": 80},
  "layers": ["asns_geo", "pix"]
}

// ASes com prefixos cobrindo região próxima a Palmas
{
  "near_prefixes": {"ixp": "to", "radius_km": 300},
  "layers": ["asns_geo", "prefixes_v4", "pix"]
}

// Prefixos do PTT de SP exceto o AS 6939
{
  "filter": {"not": {"field": "asn", "op": "eq", "value": 6939}},
  "near": {"ixp": "sp", "radius_km": 1},
  "layers": ["prefixes_v4"]
}
```
""",
    tags=["geo"],
)
@limiter.limit(LIMIT_HEAVY)
def map_query(
    request: Request,
    body: dict = Body(default_factory=dict, examples=[_MAP_QUERY_EXAMPLE]),
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    try:
        return store.map_query(date_str, body)
    except q.QueryError as exc:
        raise HTTPException(400, str(exc))


@router.get(
    "/map/scms",
    summary="Mapa de outorgas SCM geolocalizadas",
    description="""
Retorna um GeoJSON FeatureCollection com as outorgas de SCM (Serviço de Comunicação
Multimídia) coletadas da Anatel que possuem geolocalização.

Cada Feature contém: `cnpj`, `razao_social`, `nome_fantasia`, `municipio`, `uf`,
`situacao`, `asns` (lista de ASNs com mesmo CNPJ), `has_asn`, `geo_confidence`.

Use `?uf=SP` para filtrar por estado. Disponível somente se as etapas anatel_scm e scm_geo foram executadas.
""",
)
def map_scms(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
    uf: Optional[str] = Query(
        None,
        description="Filtrar por UF (sigla de dois caracteres, ex: SP, RJ, RS).",
        min_length=2,
        max_length=2,
    ),
    com_asn: bool = Query(
        False,
        description="Se true, retorna apenas pontos com ASN identificado pelo CNPJ.",
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    path = store._pub(date_str) / "maps" / "scms.geojson"
    if not path.exists():
        raise HTTPException(404, "Mapa de SCMs não disponível para este snapshot. Rode anatel_scm e scm_geo primeiro.")

    try:
        import json as _json
        geojson = _json.loads(path.read_bytes())
    except Exception:
        raise HTTPException(500, "Erro ao carregar mapa de SCMs")

    features = geojson.get("features", [])
    if uf:
        uf_upper = uf.upper()
        features = [f for f in features if (f.get("properties") or {}).get("uf", "").upper() == uf_upper]
    if com_asn:
        features = [f for f in features if (f.get("properties") or {}).get("has_asn")]

    return {**geojson, "features": features}


@router.get(
    "/map/smps",
    summary="Mapa de outorgas SMP geolocalizadas",
    description="""
Retorna um GeoJSON FeatureCollection com as outorgas de SMP (Serviço Móvel Pessoal)
coletadas da Anatel que possuem geolocalização. Mesmo formato de /map/scms, universo
bem menor (~30 CNPJs).

Use `?uf=SP` para filtrar por estado. Disponível somente se as etapas anatel_smp e smp_geo foram executadas.
""",
)
def map_smps(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
    uf: Optional[str] = Query(
        None,
        description="Filtrar por UF (sigla de dois caracteres, ex: SP, RJ, RS).",
        min_length=2,
        max_length=2,
    ),
    com_asn: bool = Query(
        False,
        description="Se true, retorna apenas pontos com ASN identificado pelo CNPJ.",
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    path = store._pub(date_str) / "maps" / "smps.geojson"
    if not path.exists():
        raise HTTPException(404, "Mapa de SMPs não disponível para este snapshot. Rode anatel_smp e smp_geo primeiro.")

    try:
        import json as _json
        geojson = _json.loads(path.read_bytes())
    except Exception:
        raise HTTPException(500, "Erro ao carregar mapa de SMPs")

    features = geojson.get("features", [])
    if uf:
        uf_upper = uf.upper()
        features = [f for f in features if (f.get("properties") or {}).get("uf", "").upper() == uf_upper]
    if com_asn:
        features = [f for f in features if (f.get("properties") or {}).get("has_asn")]

    return {**geojson, "features": features}


@router.get(
    "/map/stfcs",
    summary="Mapa de outorgas STFC geolocalizadas",
    description="""
Retorna um GeoJSON FeatureCollection com as outorgas de STFC (Serviço Telefônico Fixo Comutado)
coletadas da Anatel que possuem geolocalização. Mesmo formato de /map/scms, universo maior (~1.700 CNPJs).

Use `?uf=SP` para filtrar por estado.
""",
)
def map_stfcs(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
    uf: Optional[str] = Query(
        None,
        description="Filtrar por UF (sigla de dois caracteres, ex: SP, RJ, RS).",
        min_length=2,
        max_length=2,
    ),
    com_asn: bool = Query(
        False,
        description="Se true, retorna apenas pontos com ASN identificado pelo CNPJ.",
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    path = store._pub(date_str) / "maps" / "stfcs.geojson"
    if not path.exists():
        raise HTTPException(404, "Mapa de STFCs não disponível para este snapshot.")

    try:
        import json as _json
        geojson = _json.loads(path.read_bytes())
    except Exception:
        raise HTTPException(500, "Erro ao carregar mapa de STFCs")

    features = geojson.get("features", [])
    if uf:
        uf_upper = uf.upper()
        features = [f for f in features if (f.get("properties") or {}).get("uf", "").upper() == uf_upper]
    if com_asn:
        features = [f for f in features if (f.get("properties") or {}).get("has_asn")]

    return {**geojson, "features": features}

@router.get(
    "/map/seacs",
    summary="Mapa de outorgas SEAC geolocalizadas",
    description="""
Retorna um GeoJSON FeatureCollection com as outorgas de SEAC (Serviço de Acesso Condicionado)
coletadas da Anatel que possuem geolocalização. Mesmo formato de /map/scms, universo próprio (~1.400 CNPJs).

Use `?uf=SP` para filtrar por estado.
""",
)
def map_seacs(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
    uf: Optional[str] = Query(
        None,
        description="Filtrar por UF (sigla de dois caracteres, ex: SP, RJ, RS).",
        min_length=2,
        max_length=2,
    ),
    com_asn: bool = Query(
        False,
        description="Se true, retorna apenas pontos com ASN identificado pelo CNPJ.",
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    path = store._pub(date_str) / "maps" / "seacs.geojson"
    if not path.exists():
        raise HTTPException(404, "Mapa de SEACs não disponível para este snapshot.")

    try:
        import json as _json
        geojson = _json.loads(path.read_bytes())
    except Exception:
        raise HTTPException(500, "Erro ao carregar mapa de SEACs")

    features = geojson.get("features", [])
    if uf:
        uf_upper = uf.upper()
        features = [f for f in features if (f.get("properties") or {}).get("uf", "").upper() == uf_upper]
    if com_asn:
        features = [f for f in features if (f.get("properties") or {}).get("has_asn")]

    return {**geojson, "features": features}


@router.get(
    "/map/prefixes",
    summary="Mapa de prefixos por ASN e município",
    description="""
Retorna um GeoJSON FeatureCollection com os prefixos BR declarados no Registro.br **agregados por ASN originador,
versão IP e município** (base DB-IP City Lite). A API não serve a posição de cada prefixo: o ponto de cada
Feature é o centroide do município e nenhuma Feature identifica um prefixo.

Propriedades: `origin_asn`, `ip_version`, `city` (município), `uf`, `country`, `prefix_count` (quantos prefixos do ASN
estão naquele município), `geo_confidence` (`city_centroid`), `geo_source`.

Use `?uf=SP` para filtrar por estado. Prefixos sem geolocalização (`geo_confidence=unknown`)
são excluídos do resultado.
""",
)
def map_prefixes(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
    uf: Optional[str] = Query(
        None,
        description="Filtrar por UF (sigla de dois caracteres, ex: SP, RJ, RS).",
        min_length=2,
        max_length=2,
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    geojson = store.geo_map_prefixos_agregado(date_str)
    if geojson is None:
        raise HTTPException(404, "Dados de geolocalização de prefixos não disponíveis para este snapshot")

    return _filter_geojson(geojson, uf)


_V_QUERY = Query(
    None,
    description="Hash do conteúdo da camada (de `/map/layers`). Com ele a URL não depende da data e a resposta é imutável.",
    pattern=r"^[0-9a-f]{16}$",
)


def _data_da_camada(request: Request, store: Store, layer: str, date: Optional[str], v: Optional[str]) -> str:
    """Resolve o snapshot de uma camada estática. Com `v`, a camada é endereçada pelo conteúdo (imutável no cliente)."""
    if v:
        date_str = store.data_da_camada(layer, v)
        if date_str is None:
            raise HTTPException(404, "Versão da camada não encontrada")
        request.state.cache_imutavel = True
        return date_str
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return date_str


_CAMADAS_ESTATICAS = {
    "submarine_cables": "/api/v1/map/submarine-cables",
    "submarine_landing_points": "/api/v1/map/submarine-landing-points",
    "itu_transmission": "/api/v1/map/terrestrial-links",
    "power_transmission_lines": "/api/v1/map/power-transmission-lines",
    "ibge_rodovias": "/api/v1/map/rodovias",
}


@router.get(
    "/map/layers",
    summary="Camadas estáticas versionadas por conteúdo",
    description=(
        "Para cada camada de infraestrutura física (cabos, pontos de aterrissagem, enlaces ITU, linhas de transmissão, "
        "rodovias), o hash do conteúdo e a URL com `?v=`. A URL não depende da data: enquanto o conteúdo não muda entre "
        "snapshots, o navegador reaproveita o que já baixou."
    ),
)
def map_layers(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    camadas = {}
    for layer, url in _CAMADAS_ESTATICAS.items():
        h = store.camada_hash(date_str, layer)
        if h:
            camadas[layer] = {"hash": h, "url": f"{url}?v={h}"}
    return {"snapshot_date": date_str, "camadas": camadas}


@router.get(
    "/map/terrestrial-links",
    summary="Enlaces terrestres (ITU BBmaps)",
    description="""
Retorna um GeoJSON FeatureCollection com enlaces de transmissão terrestre
(fibra e micro-ondas) coletados da ITU Transmission Networks Geocatalogue
(bbmaps.itu.int), mundo todo.

Cada Feature é um `LineString` com as propriedades `type_inf` (ex.:
`"Fibre Operational"`) e `status` (`Operational`, `Planned`, `Proposed`,
`Under Construction`). Usado como camada de fundo nos mapas e como camada
interativa em `/mapa`.
""",
)
def map_terrestrial_links(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
    v: Optional[str] = _V_QUERY,
) -> dict:
    store: Store = request.app.state.store
    date_str = _data_da_camada(request, store, "itu_transmission", date, v)

    geojson = store.geo_map(date_str, "itu_transmission")
    if geojson is None:
        raise HTTPException(404, "Dados de enlaces terrestres não disponíveis para este snapshot")

    return geojson


@router.get(
    "/map/submarine-cables",
    summary="Cabos submarinos (TeleGeography)",
    description="""
Retorna um GeoJSON FeatureCollection com os cabos submarinos internacionais
coletados do TeleGeography Submarine Cable Map (submarinecablemap.com),
sob licença CC BY-SA 4.0 — atribuição obrigatória sempre que exibido.

Cada Feature é um `MultiLineString` com `id`, `name`, `color`, `length`,
`owners`, `rfs_year`, `is_planned`, `url`.
""",
)
def map_submarine_cables(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
    v: Optional[str] = _V_QUERY,
) -> dict:
    store: Store = request.app.state.store
    date_str = _data_da_camada(request, store, "submarine_cables", date, v)

    geojson = store.geo_map(date_str, "submarine_cables")
    if geojson is None:
        raise HTTPException(404, "Dados de cabos submarinos não disponíveis para este snapshot")

    return geojson


@router.get(
    "/map/submarine-landing-points",
    summary="Pontos de aterrissagem de cabos submarinos (TeleGeography)",
    description="""
Retorna um GeoJSON FeatureCollection com os pontos de aterrissagem de cabos
submarinos (TeleGeography, CC BY-SA 4.0). Cada Feature é um `Point` com `id`,
`name`, `is_tbd`.
""",
)
def map_submarine_landing_points(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
    v: Optional[str] = _V_QUERY,
) -> dict:
    store: Store = request.app.state.store
    date_str = _data_da_camada(request, store, "submarine_landing_points", date, v)

    geojson = store.geo_map(date_str, "submarine_landing_points")
    if geojson is None:
        raise HTTPException(404, "Dados de pontos de aterrissagem não disponíveis para este snapshot")

    return geojson


@router.get(
    "/map/power-transmission-lines",
    summary="Linhas de transmissão de alta tensão (SIGEL/ANEEL)",
    description="""
Retorna um GeoJSON FeatureCollection com as linhas de transmissão de alta
tensão da rede básica nacional (operada pelo ONS), coletadas do SIGEL/ANEEL
(sigel.aneel.gov.br).

Cada Feature é um `LineString`/`MultiLineString` com `name` (texto original
do SIGEL), e, quando extraíveis desse texto, `tensao_kv`, `extensao_km`,
`subestacao_origem`, `subestacao_destino`, `uf`.

Linhas de alta tensão frequentemente carregam cabos OPGW (fibra óptica no
cabo para-raios) usados para telecom, mas o SIGEL **não informa** quais
linhas de fato têm OPGW — essa é informação operacional das transmissoras,
não um dado aberto. Esta camada representa só a malha de alta tensão, sem
nunca afirmar presença de OPGW.
""",
)
def map_power_transmission_lines(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
    v: Optional[str] = _V_QUERY,
) -> dict:
    store: Store = request.app.state.store
    date_str = _data_da_camada(request, store, "power_transmission_lines", date, v)

    geojson = store.geo_map(date_str, "power_transmission_lines")
    if geojson is None:
        raise HTTPException(404, "Dados de linhas de transmissão não disponíveis para este snapshot")

    return geojson


@router.get(
    "/map/rodovias",
    summary="Malha rodoviária nacional (IBGE BC250)",
    description="""
Retorna um GeoJSON FeatureCollection com trechos de rodovia da Base
Cartográfica Contínua do IBGE (BC250, camada `rod_trecho_rodoviario_l`,
124 mil feições nacionalmente).

Dado o volume, esta rota filtra **no servidor** — diferente das outras
camadas de infraestrutura física, que sempre devolvem o arquivo publicado
inteiro. Combine `jurisdicao`/`pavimentada`/`sigla` para reduzir o resultado
antes de baixar.

Faixas de domínio de rodovias frequentemente carregam cabos OPGW ou dutos de
fibra óptica, mas o IBGE **não informa** quais trechos têm fibra — essa é
informação operacional de concessionárias/operadoras, não um dado aberto.
Esta camada representa só a malha viária em si, sem nunca afirmar presença
de fibra.
""",
)
def map_rodovias(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
    jurisdicao: Optional[str] = Query(
        None,
        description="Uma ou mais jurisdições, separadas por vírgula "
                    "(Federal, Estadual/Distrital, Municipal, Propriedade particular, Desconhecida).",
    ),
    pavimentada: Optional[bool] = Query(
        None,
        description="true = só pavimentadas, false = só não pavimentadas. Omitido: todas, incluindo indefinidas.",
    ),
    sigla: Optional[str] = Query(
        None,
        description="Substring (case-insensitive) sobre a sigla da rodovia, ex.: BR-101.",
    ),
    v: Optional[str] = _V_QUERY,
) -> dict:
    store: Store = request.app.state.store
    date_str = _data_da_camada(request, store, "ibge_rodovias", date, v)

    jurisdicoes = None
    if jurisdicao:
        jurisdicoes = {j.strip() for j in jurisdicao.split(",") if j.strip()}
    sigla_lower = sigla.strip().lower() if sigla else None

    if jurisdicoes is None and pavimentada is None and not sigla_lower:
        # Sem filtro o resultado é o arquivo inteiro (~135 MB): repassa os bytes, sem parsear (parsear custava ~2 GB de memória).
        arquivo = store.geo_map_arquivo(date_str, "ibge_rodovias")
        if arquivo is None:
            raise HTTPException(404, "Dados de malha rodoviária não disponíveis para este snapshot")
        return FileResponse(arquivo, media_type="application/json")

    def aceita(f: dict) -> bool:
        props = f.get("properties") or {}
        if jurisdicoes is not None and props.get("jurisdicao") not in jurisdicoes:
            return False
        if pavimentada is not None and props.get("pavimentada") != pavimentada:
            return False
        if sigla_lower and sigla_lower not in (props.get("sigla") or "").lower():
            return False
        return True

    # Filtra feição a feição direto do arquivo (ver `Store.geo_map_filtrado`): parsear a malha inteira custava ~2 GB.
    geojson = store.geo_map_filtrado(date_str, "ibge_rodovias", aceita)
    if geojson is None:
        raise HTTPException(404, "Dados de malha rodoviária não disponíveis para este snapshot")
    # Serializa direto para bytes: devolver o dict passaria pelo jsonable_encoder, que copia as ~100 mil feições antes do json.dumps
    # (o dobro do pico de memória por pedido, multiplicado pelos pedidos simultâneos).
    corpo = json.dumps(geojson, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return Response(content=corpo, media_type="application/json")
