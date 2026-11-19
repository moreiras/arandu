# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoints de CDNs e CAPs — GET /cdns.

Serve a presença de CDNs (Content Delivery Networks) e CAPs (Content Anchor
Points) nos PTTs do IX.br, com a lista de IXPs em que cada CDN está presente.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.store import Store

router = APIRouter()


_ALCANCE_CACHE: dict = {}


@router.get(
    "/cdns/alcance",
    summary="Alcance de cada CDN por peering: fração dos usuários BR em ASes membros dos PTTs onde ela está",
    description="""
Por CDN: a fração dos usuários estimados pela APNIC, nos ASes do Brasil, que estão em ASes **membros de algum PTT do IX.br onde a CDN tem peering direto observado**, no país e por UF da sede
do AS. Estimativa: usuários se repetem entre ASes da mesma operadora, membro registrado não quer dizer que o tráfego da CDN passe ali, e não mede tráfego nem qualidade.
""",
)
def cdns_alcance(request: Request, date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD).")) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    pres = store.cdn_presence(date_str)
    if pres is None:
        raise HTTPException(404, "Dados de presença de CDNs não disponíveis para este snapshot")
    if date_str not in _ALCANCE_CACHE:
        from api.services.interconexao import alcance_cdns
        idx = {a["asn"]: a for a in store.asn_index(date_str) if a.get("is_br") and a.get("apnic_users")}
        uf_de = {int(a): v.get("uf") for a, v in ((store.seguranca_doc(date_str) or {}).get("asns") or {}).items() if v.get("uf")}
        membros = {int(a): v.get("m", []) for a, v in store.asn_ix_presence(date_str).get("asns", {}).items()}
        _ALCANCE_CACHE[date_str] = alcance_cdns(pres["cdns"], membros, {a: x["apnic_users"] for a, x in idx.items()}, uf_de)
        while len(_ALCANCE_CACHE) > 2:
            _ALCANCE_CACHE.pop(next(iter(_ALCANCE_CACHE)))
    return {"snapshot_date": date_str, **_ALCANCE_CACHE[date_str]}


@router.get(
    "/cdns/presence",
    summary="Matriz de presença de CDNs nos IXPs",
    description="Retorna matriz de presença de CDNs/provedores nos IXPs do IX.br e externos.",
)
def get_cdn_presence(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    data = store.cdn_presence(date_str)
    if data is None:
        raise HTTPException(404, "Dados de presença de CDNs não disponíveis para este snapshot")

    return data
