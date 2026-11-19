# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Playbook do servidor MCP, enviado ao cliente no `initialize` (campo `instructions`)."""

# Playbook do servidor — enviado ao cliente no `initialize` (campo instructions).
# Diferente do prompt (opt-in), isto quase sempre chega ao modelo: é onde ensinamos a ESCOLHER e ENCADEAR as ferramentas, que é onde as
# LLMs mais tropeçam. O texto é gerado de `mcp_server/guia.py` (tabela tarefa → tool); edite lá.
from mcp_server.guia import instrucoes

_INSTRUCTIONS = instrucoes()
