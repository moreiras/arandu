# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estado da coleta de um PTT do IX.br por família de endereços, comum ao pipeline (`ixps/index.json`), à API e ao MCP.

`coleta` de cada família: `ok` (o looking glass devolveu rotas), `vazia` (a coleta funcionou, mas o looking glass respondeu com a tabela
vazia: zero rotas, que não é o mesmo que zero de cobertura) e `missing` (sem bruto da família). O `status` do PTT só é `ok` com as duas
famílias `ok`; `partial` quando uma delas está vazia ou ausente. Numa família `vazia` as porcentagens calculadas sobre as rotas
(cobertura, espaço) saem `null`: zero rotas não mede cobertura. A razão de a tabela vir vazia não se conhece daqui.
"""
from __future__ import annotations

COLETA_OK, COLETA_VAZIA, COLETA_AUSENTE = "ok", "vazia", "missing"
# Medidas que dependem de haver rotas: com a tabela vazia não são zero, são indefinidas.
_PCT_SOBRE_ROTAS = ("br_prefix_coverage_pct", "ixp_vs_fulltable_space_pct", "br_asns_direct_pct", "br_asns_origin_pct")


def coleta_afi(afi) -> str:
    if not isinstance(afi, dict) or afi.get("status") == "missing" or "total_routes" not in afi:
        return COLETA_AUSENTE
    return COLETA_OK if afi.get("total_routes") else COLETA_VAZIA


def status_ptt(v4, v6) -> str:
    """`ok` só com rotas nas duas famílias; `missing` sem nenhuma; `partial` no resto (inclusive família com tabela vazia)."""
    estados = {coleta_afi(v4), coleta_afi(v6)}
    if estados == {COLETA_OK}:
        return "ok"
    if estados == {COLETA_AUSENTE}:
        return "missing"
    return "partial"


def marcar_afi(afi):
    """A família com `coleta` (idempotente); com a tabela vazia, as porcentagens sobre rotas viram `null`."""
    if not isinstance(afi, dict):
        return afi
    c = coleta_afi(afi)
    afi["coleta"] = c
    if c == COLETA_VAZIA:
        for k in _PCT_SOBRE_ROTAS:
            if k in afi:
                afi[k] = None
    return afi


def marcar_ptt(entrada: dict) -> dict:
    """Entrada do índice de PTTs ou documento do PTT com `coleta` por família e `status` coerente (idempotente, altera no lugar)."""
    if not isinstance(entrada, dict):
        return entrada
    tem_familias = any(isinstance(entrada.get(a), dict) for a in ("v4", "v6"))
    for a in ("v4", "v6"):
        marcar_afi(entrada.get(a))
    if tem_familias and "status" in entrada:
        entrada["status"] = status_ptt(entrada.get("v4"), entrada.get("v6"))
    return entrada
