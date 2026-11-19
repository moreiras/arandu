# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoint de diagnóstico aprofundado de estabilidade BGP — GET /bgp/stability/{asn}/deep.

Serve a análise detalhada dos ASes mais ruidosos: AS_PATHs completos dos
eventos de flap, diagnóstico de causa raiz por prefixo.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()


@router.get(
    "/bgp-stability-deep",
    summary="Diagnóstico aprofundado dos ASes BR mais ruidosos",
    description="""
Resultado da etapa 2 da análise de estabilidade BGP: releitura dos arquivos MRT
em cache com AS_PATH completo para os N ASes mais ruidosos identificados na etapa 1.

Para cada AS fornece:
- `verdict`: causa-raiz inferida (`upstream_instability`, `prefix_specific`, `origin_instability`)
- `prefix_sync_score`: 0–1, onde 1 = todos os prefixos flapam em sincronia (sugere causa comum)
- `suspected_upstream_asn` e `upstream_concentration_pct`: upstream mais frequente nos eventos
- `hot_prefixes`: prefixos mais instáveis com upstream dominante por prefixo

Também identifica `suspected_upstreams` cross-AS: upstreams que aparecem como suspeitos
em múltiplos ASes simultaneamente, com eventos e hora de pico.
""",
    tags=["bgp-stability"],
)
def get_bgp_stability_deep(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    from api.store import Store
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    data = store.bgp_stability_deep(date_str)
    if data is None:
        raise HTTPException(
            404,
            "bgp_stability_deep não disponível para este snapshot. "
            "Execute: python -m sources.bgp_stability_deep.collect --date "
            + date_str
            + " && python -m products.bgp_stability.deep --date "
            + date_str,
        )
    return data
