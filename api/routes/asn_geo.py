# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoint de geolocalização de ASN — GET /asns/{asn}/geo.

Retorna as coordenadas da organização (derivadas do CNPJ/PeeringDB) e os prefixos
IPv6/IPv4 do ASN com suas localizações geográficas (DB-IP City Lite).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.store import Store

router = APIRouter()

_VALID_LAYERS = {"fulltable_v4", "fulltable_v6", "ixp_v4", "ixp_v6"}

_LAYER_DESCRIPTIONS = {
    "fulltable_v4": "Prefixos IPv4 na full table global — próprios (azul) e de clientes (azul claro)",
    "fulltable_v6": "Prefixos IPv6 na full table global — próprios (laranja) e de clientes (amarelo)",
    "ixp_v4": "Prefixos IPv4 por PTT — direto: próprios (azul) + clientes (azul claro); indireto: próprios (azul claro)",
    "ixp_v6": "Prefixos IPv6 por PTT — direto: próprios (laranja) + clientes (amarelo); indireto: próprios (amarelo)",
}


@router.get(
    "/asns/{asn}/geo",
    summary="Mapa geográfico de prefixos de um ASN",
    description="""
Retorna um GeoJSON FeatureCollection com a distribuição geográfica dos prefixos
anunciados por um ASN e seus clientes (downstreams).

**Camadas disponíveis (`layer`):**

| Valor | Descrição |
|---|---|
| `fulltable_v4` | Prefixos IPv4 na tabela global — próprios e de clientes downstream |
| `fulltable_v6` | Prefixos IPv6 na tabela global — próprios e de clientes downstream |
| `ixp_v4` | Prefixos IPv4 por PTT — direto (próprios + clientes) e indireto (só próprios) |
| `ixp_v6` | Prefixos IPv6 por PTT — direto (próprios + clientes) e indireto (só próprios) |

Cada feature tem propriedade `role`: `"own"` (prefixos do próprio AS) ou `"downstream"`
(prefixos de clientes). Nas camadas de PTT, `direct: true/false` indica presença direta
no route server.

Prefixos são agregados por cidade (granularidade /20 para IPv4). Camadas `fulltable_*`
incluem prefixos de qualquer país, geolocalizados pela base DB-IP City Lite; prefixos de clientes usam apenas dados
geolocalizados pré-computados (cobertura BR).

Camadas de PTT retornam adicionalmente `ixp_pix` com localização física dos PTTs.
""",
)
def asn_geo(
    asn: int,
    request: Request,
    layer: str = Query(
        "fulltable_v4",
        description="Camada de dados. Ver tabela acima.",
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

    geojson = store.asn_geo(date_str, asn, layer)
    if geojson is None:
        raise HTTPException(404, f"ASN {asn} não encontrado no snapshot '{date_str}'")

    return {
        **geojson,
        "snapshot_date": date_str,
        "asn": asn,
        "layer": layer,
        "layer_description": _LAYER_DESCRIPTIONS[layer],
    }
