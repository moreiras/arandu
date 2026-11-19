# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoints de IXPs externos — GET /external-ixps e GET /external-ixps/{code}.

IXPs externos são os IXPs fora do IX.br (ex: Equinix IX, DE-CIX, AMS-IX)
coletados via PeeringDB. Usados para analisar presença global de redes BR.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.services import decix_rs
from api.store import Store

router = APIRouter()


@router.get(
    "/external-ixps",
    summary="Listar IXPs externos",
    description="""
Retorna a lista de IXPs externos ao IX.br com contagens de membros totais e brasileiros.

Dados provenientes exclusivamente do PeeringDB (membros autodeclarados).
""",
)
def list_external_ixps(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    country: Optional[str] = Query(None, description="Filtro por código de país ISO (ex: BR, NL, US)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    index = store.external_ixp_index(date_str)
    if index is None:
        raise HTTPException(404, "Dados de IXPs externos não disponíveis para este snapshot")

    ixps = index.get("ixps", [])
    if country:
        ixps = [e for e in ixps if e.get("country", "").upper() == country.upper()]

    return {
        "snapshot_date": index.get("snapshot_date", date_str),
        "count": len(ixps),
        "ixps": decix_rs.com_resumo(ixps, store.decix_rs_doc(date_str)),
    }


@router.get(
    "/external-ixps/{code}",
    summary="Documento completo de um IXP externo",
    description="""
Retorna lista completa de membros de um IXP externo com indicação de ASNs brasileiros.

Dados provenientes exclusivamente do PeeringDB (membros autodeclarados).

**Requer autenticação** — lista de membros é dado PeeringDB redistribuído; acesso restrito a
usuários autenticados conforme AUP do PeeringDB.
""",
)
def get_external_ixp(
    code: str,
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    br_only: bool = Query(False, description="Se true, retorna apenas membros brasileiros."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    doc = store.external_ixp_detail(date_str, code)
    if doc is None:
        raise HTTPException(404, f"IXP externo '{code}' não encontrado no snapshot '{date_str}'")

    if br_only:
        doc = dict(doc)
        doc["members"] = [m for m in doc.get("members", []) if m.get("is_br")]

    # DE-CIX: `route_server` só existe para decix-sp e decix-rj quando a coleta rodou; ver api/services/decix_rs.py (a descrição da rota não muda: contrato OpenAPI intacto)
    return decix_rs.anexar(doc, store.decix_rs_doc(date_str), code)
