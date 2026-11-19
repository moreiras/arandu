# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoints de mapa Hilbert — GET /hilbert/v4, /hilbert/v4/{prefix}, /hilbert/v6.

Serve os dados de densidade do espaço de endereçamento IPv6 e IPv4 no formato
de curva de Hilbert, para visualização no frontend.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.store import Store

router = APIRouter()


@router.get(
    "/hilbert/v4",
    summary="Mapas de densidade Hilbert IPv4 (/16)",
    description="""
Retorna 4 mapas de densidade para visualização no mapa de Hilbert a resolução /16.

Cada mapa é uma lista de **65536 inteiros** (0–256): o valor representa o número de
blocos **/24 equivalentes** presentes em cada bloco **/16**, ordenados pelo índice linear
`a*256 + b` (onde `a.b.0.0/16` é o bloco).

**Camadas:**
- `rir_br` — prefixos **atribuídos** ao Brasil pelo Registro.br
- `global_br` — prefixos de **ASNs brasileiros** na full table global
- `global_all` — **todos** os prefixos da full table global
- `ixp_all` — prefixos observados em **qualquer IXP** do IX.br

Para renderizar: o bloco `a.b.0.0/16` tem índice `i = a*256 + b`. A posição
`(x, y)` na grade 256×256 da curva de Hilbert é `d2xy(256, i)`.
""",
)
def get_hilbert_v4(
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

    data = store.hilbert_v4(date_str)
    if data is None:
        raise HTTPException(404, f"Dados Hilbert não disponíveis para snapshot '{date_str}'")

    return data


@router.get(
    "/hilbert/v6",
    summary="Mapas de presença Hilbert IPv6 (/32)",
    description="""
Retorna índices esparsos de presença /32 para 6 blocos RIR no mapa de Hilbert IPv6.

Cada bloco contém listas de **índices de células /32 ativas** (inteiros), não arrays densos.
O índice `d` de uma célula mapeia para a posição `(x, y)` na grade pela curva de Hilbert:
- Blocos /12 (LACNIC, ARIN, RIPE, APNIC, AFRINIC): grade 1024×1024, `d2xy(1024, d)`
- Bloco legado 2001::/16: grade 256×256, `d2xy(256, d)`

**Blocos retornados:** `legacy` (2001::/16), `lacnic` (2800::/12), `arin` (2600::/12),
`ripe` (2a00::/12), `apnic` (2400::/12), `afrinic` (2c00::/12).

**Camadas por bloco:**
- `ixp_all` — /32s com algum prefixo observado em qualquer IXP do IX.br
- `global_all` — /32s com algum prefixo presente na tabela de roteamento global IPv6
""",
)
def get_hilbert_v6(
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

    data = store.hilbert_v6(date_str)
    if data is None:
        raise HTTPException(404, f"Dados Hilbert v6 não disponíveis para snapshot '{date_str}'")

    return data


@router.get(
    "/hilbert/v4/detail",
    summary="Blocos /24 dentro de um /8 (dashboard global)",
)
def get_hilbert_v4_detail(
    request: Request,
    slash8: int = Query(..., description="Número do bloco /8 (0-255)"),
    layer: str = Query("global_all", description="Camada: global_all | global_br | rir_br | rir_br_visible | ixp_all"),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    result = store.hilbert_v4_detail(date_str, slash8, layer)
    if result is None:
        raise HTTPException(404, f"Dados não disponíveis para /8 '{slash8}' camada '{layer}'")
    return result
