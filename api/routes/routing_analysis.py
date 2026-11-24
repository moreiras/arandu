# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoint de análise de roteamento BGP — GET /bgp/routing-analysis.

Serve o resultado da análise da tabela BGP global com foco nos ASNs e
prefixos brasileiros: cobertura de espaço alocado, prefixos too-specific,
composição de AS_PATHs e comunidades BGP relevantes.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, HTTPException, Query, Request

from api.store import Store
from core import moas

router = APIRouter()

_CONFIG_ROOT = Path(__file__).parent.parent.parent


@lru_cache(maxsize=1)
def _communities_lookup() -> tuple[dict[str, tuple[str, str]], list[tuple]]:
    path = _CONFIG_ROOT / "config" / "bgp_communities.yaml"
    if not path.exists():
        return {}, []
    with open(path) as f:
        data = yaml.safe_load(f)
    exact: dict[str, tuple[str, str]] = {}
    patterns: list[tuple] = []
    for entry in data.get("communities", []):
        comm = entry.get("community", "")
        desc = entry.get("description", "")
        operator = entry.get("operator", "")
        if not comm:
            continue
        if "X" in comm:
            patterns.append((re.compile("^" + comm.replace("X", r"\d+") + "$"), desc, operator))
        else:
            exact.setdefault(comm, (desc, operator))
    return exact, patterns


def _lookup_community(comm: str) -> tuple[str | None, str | None]:
    exact, patterns = _communities_lookup()
    if comm in exact:
        return exact[comm]
    for pat, desc, operator in patterns:
        if pat.match(comm):
            return desc, operator
    return None, None


def _enrich_top_communities(data: dict) -> None:
    as_path = data.get("as_path_stats") or {}
    for afi in ("v4", "v6"):
        for entry in (as_path.get("community_stats") or {}).get(afi, {}).get("top_communities", []):
            desc, operator = _lookup_community(entry["community"])
            if desc:
                entry["description"] = desc
            if operator:
                entry["operator"] = operator


@router.get(
    "/routing-analysis",
    summary="Análise BGP global — prefixos brasileiros",
    description="""
Retorna análise completa da tabela de roteamento global com foco em ASNs e
prefixos brasileiros (P_BR). Inclui composição de P_BR, histograma de
prefix length, more specifics, potencial de agregação, cobertura Registro.br,
prefixos potencialmente filtráveis. `moas` vem nulo, com o motivo em `moas_indisponivel`: a tabela usada guarda uma origem por
prefixo e não detecta origem múltipla.

Quando `has_path_data` é `true`, o campo `as_path_stats` é preenchido com
estatísticas de AS_PATH, prepending, upstream aparente, higiene e communities.
""",
)
def get_routing_analysis(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    data = store.routing_analysis(date_str)
    if data is None:
        raise HTTPException(
            404,
            "routing_analysis não disponível para este snapshot. "
            "Execute: python -m products.routing_analysis.build --date " + date_str,
        )
    _enrich_top_communities(data)
    return moas.retirar_da_analise(data)              # snapshots anteriores traziam `moas: []`, lido como "nenhum MOAS"
