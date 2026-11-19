# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tool `asn_interconexao` do MCP: o que os dados públicos mostram sobre a interconexão de um AS.

Mesma fonte da rota `GET /asns/{asn}/interconexao` (o handler da rota roda com um `request` mínimo que só carrega a `store`).
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

from fastapi import HTTPException

from api.routes.asns import asn_interconexao as _rota
from mcp_server.contexto import _resolve, _store, mcp


@mcp.tool()
def asn_interconexao(asn: int, date: Optional[str] = None) -> dict:
    """Interconexão mensurável de um AS: PTTs do IX.br onde ele origina prefixos SEM ser par direto (do mais perto da sede ao mais longe, com quem entrega os caminhos), sessões ausentes ou só de uma família nos route servers e rotas rejeitadas.

    Só o que os dados públicos mostram na data da coleta. NUNCA diga que o AS "não troca tráfego" com alguém: peering bilateral não é visível nesses dados, e cada item é um fato, não uma recomendação.

    Args:
        asn: Número do AS.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(store=_store)))
    try:
        return _rota(int(asn), request, _resolve(date))
    except HTTPException as e:
        raise ValueError(e.detail)
