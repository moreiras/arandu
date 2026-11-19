# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Outorgas STFC — GET /stfcs, /stfcs/stats e /stfcs/{cnpj}.

Geradas da capacidade declarada em `serve/capabilities/stfc.yaml`; a lógica comum está em `api/capacidades.py`.
Os nomes abaixo continuam importáveis (o perfil e o contrato unificado de outorgas chamam as funções).
"""
from api.capacidades import gerar_rotas

router, _rotas = gerar_rotas("stfc")
list_stfcs = _rotas["list_stfcs"]
stfc_stats = _rotas["stfc_stats"]
get_stfc = _rotas["get_stfc"]
