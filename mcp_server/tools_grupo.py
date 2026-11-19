# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tool `grupo_perfil` do MCP: o grupo econômico com mercado, regulatório e técnico.

Mesma fonte da rota `GET /grupos/{id}` (com `include`), pelo mesmo caminho: o handler da rota roda com um `request` mínimo que só carrega a `store`.
O grupo é inferido do quadro societário; nunca devolve nome de sócio nem CPF.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

from fastapi import HTTPException

from api.routes.grupos import get_grupo
from mcp_server.contexto import _resolve, _store, mcp

BLOCOS = ("mercado", "regulatorio", "tecnico", "relacoes")


@mcp.tool()
def grupo_perfil(grupo_id: str, blocos: Optional[list[str]] = None, date: Optional[str] = None) -> dict:
    """Perfil de um grupo econômico (grupo_id = `grp_…` ou `ind_…`, de `operadora_grupo` ou da busca): composição (CNPJs, serviços, ASNs), acessos e UFs, e os blocos pedidos.

    `blocos` (opcional): `mercado` = posição entre as empresas, série de 24 meses, UFs com HHI e empresas presentes nos mesmos municípios; `regulatorio` = outorgas, multas (por raiz de
    CNPJ), prestadoras do RQUAL e reclamações (Anatel e Consumidor.gov.br), listas em ordem alfabética; `tecnico` = ASes, IPv6, RPKI, trânsito e PTTs; `relacoes` = com que evidência as empresas estão ligadas (tipo da ligação e contagem de sócios, sem nome de pessoa física).
    O grupo é INFERIDO do quadro societário (pode juntar empresas independentes). Multa constituída não é condenação definitiva; não ordene empresas por multa ou reclamação.

    Args:
        grupo_id: Identificador do grupo (`grp_…`, vários CNPJs; `ind_…`, empresa sem grupo).
        blocos: Subconjunto de mercado, regulatorio, tecnico, relacoes. Omita para só a composição.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    invalidos = [b for b in (blocos or []) if b not in BLOCOS]
    if invalidos:
        raise ValueError(f"bloco inválido: {invalidos}; válidos: {list(BLOCOS)}")
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(store=_store)))
    try:
        return get_grupo(grupo_id, request, _resolve(date), ",".join(blocos or []) or None)
    except HTTPException as e:
        raise ValueError(e.detail)
