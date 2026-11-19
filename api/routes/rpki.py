# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoints de RPKI — validação de ROAs por ASN e prefixo.

Serve a lista de VRPs (Validated ROA Payloads) do snapshot e a validação
RPKI de prefixos específicos contra os ROAs conhecidos.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.store import Store

router = APIRouter()


def montar_resumo(store: Store, date_str: str) -> dict:
    """Corpo de `GET /rpki/summary` (e da tool `rpki_summary` do MCP): adoção de ROA/ASPA nos ASNs brasileiros."""
    index = store.asn_index(date_str)
    br = [e for e in index if e.get("is_br")]

    total = len(br)
    with_roa = sum(1 for e in br if e.get("has_rpki"))
    with_aspa = sum(1 for e in br if e.get("has_aspa"))
    with_aspa_of_roa = sum(1 for e in br if e.get("has_rpki") and e.get("has_aspa"))

    space_v4_total = sum(e.get("space_v4") or 0 for e in br)
    space_v4_roa = sum(e.get("space_v4") or 0 for e in br if e.get("has_rpki"))
    space_v6_total = sum(e.get("space_v6") or 0 for e in br)
    space_v6_roa = sum(e.get("space_v6") or 0 for e in br if e.get("has_rpki"))

    return {
        "snapshot_date": date_str,
        "br_asns_total": total,
        "br_asns_with_roa": with_roa,
        "br_asns_with_aspa": with_aspa,
        "br_asns_with_aspa_of_roa": with_aspa_of_roa,
        "br_space_v4_total_24": space_v4_total,
        "br_space_v4_roa_24": space_v4_roa,
        "br_space_v6_total_48": space_v6_total,
        "br_space_v6_roa_48": space_v6_roa,
    }


@router.get(
    "/rpki/summary",
    summary="Estatísticas RPKI para ASNs brasileiros",
    description="""
Retorna métricas agregadas de adoção de ROA e ASPA para os ASNs brasileiros
(Registro.br) presentes no snapshot. Calculado a partir do índice de ASNs —
sem custo adicional de I/O.

Os campos `br_space_v4_*` e `br_space_v6_*` representam o espaço anunciado
(em equivalentes /24 e /48) pelos ASNs BR, agrupado por presença de ROA.
Não é o espaço alocado pelo Registro.br, e não indica que cada prefixo tem
ROA válida — apenas que o AS anunciante publicou ao menos uma ROA.
""",
)
def rpki_summary(
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

    return montar_resumo(store, date_str)
