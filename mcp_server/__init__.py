# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Servidor MCP do Arandurape — expõe o snapshot mais recente a LLMs.

Casca fina sobre `api.store.Store`: nenhuma regra de negócio é reimplementada;
todas as respostas vêm da mesma fonte pré-computada que alimenta a API e a UI.
"""
