# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoint de geolocalização de membros de IXP — GET /ixps/{code}/geo.

Retorna a lista de membros de um PTT com as coordenadas geográficas de cada
organização, para visualização no mapa de membros.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.store import Store

router = APIRouter()

_VALID_LAYERS = {
    "asns_members",
    "asns_direct",
    "asns_origin",
    "prefixes_v4",
    "prefixes_v6",
}

_LAYER_DESCRIPTIONS = {
    "asns_members": "ASNs membros do IXP (lista do IX.br)",
    "asns_direct":  "ASNs com prefixos anunciados diretamente no IXP (lidos do LG)",
    "asns_origin":  "ASNs brasileiros de origem dos prefixos no IXP (lidos do LG)",
    "prefixes_v4":  "Prefixos IPv4 anunciados no IXP (agregados por cidade, blocos /20)",
    "prefixes_v6":  "Prefixos IPv6 anunciados no IXP (agregados por cidade)",
}


@router.get(
    "/ixps/{code}/geo",
    summary="Mapa geográfico de um IXP",
    description="""
Retorna um GeoJSON FeatureCollection com a distribuição geográfica dos ASNs ou
prefixos de um IXP.

**Camadas disponíveis (`layer`):**

| Valor | Descrição |
|---|---|
| `asns_members` | ASNs membros do IXP (lista do IX.br; BR via CNPJ, internacionais via PeeringDB) |
| `asns_direct` | ASNs com prefixos anunciados diretamente no IXP (lidos do LG) |
| `asns_origin` | ASNs brasileiros de origem dos prefixos no IXP |
| `prefixes_v4` | Prefixos IPv4 anunciados (agregados por cidade, granularidade /20) |
| `prefixes_v6` | Prefixos IPv6 anunciados (agregados por cidade) |

**Camadas de ASNs** — cada Feature representa um ASN com campos:
`asn`, `name`, `uf`, `city`, `country`, `geo_confidence`, `geo_source`.
Requer execução prévia de `cnpj_geo` (cnpj_geo) para ASNs BR e peeringdb_intl_geo para internacionais.

**Camadas de prefixos** — cada Feature representa uma cidade com campos:
`city`, `uf`, `country`, `block_count` (número de blocos /20 ou prefixos v6), `block_unit`.
Requer a geolocalização de prefixos (`prefix_geo`) e a base DB-IP City Lite local.
IPv4: prefixos maiores que /20 são expandidos em sub-blocos /20 para maior precisão geográfica.
""",
)
def ixp_geo(
    code: str,
    request: Request,
    layer: str = Query(
        "asns_members",
        description="Camada de dados a retornar. Ver tabela acima para valores válidos.",
    ),
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
) -> dict:
    if layer not in _VALID_LAYERS:
        raise HTTPException(
            400,
            f"layer inválido: '{layer}'. Valores aceitos: {', '.join(sorted(_VALID_LAYERS))}",
        )

    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    geojson = store.ixp_geo(date_str, code, layer)
    if geojson is None:
        raise HTTPException(404, f"IXP '{code}' não encontrado no snapshot '{date_str}'")

    return {
        **geojson,
        "snapshot_date": date_str,
        "ixp_code": code,
        "layer": layer,
        "layer_description": _LAYER_DESCRIPTIONS[layer],
    }
