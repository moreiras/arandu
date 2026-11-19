# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Outorgas SeAC — GET /seacs, /seacs/stats e /seacs/{cnpj}.

Geradas da capacidade declarada em `serve/capabilities/seac.yaml`; a lógica comum está em `api/capacidades.py`.
Os nomes abaixo continuam importáveis (o perfil e o contrato unificado de outorgas chamam as funções).
"""
from api.capacidades import gerar_rotas

router, _rotas = gerar_rotas("seac")
list_seacs = _rotas["list_seacs"]
seac_stats = _rotas["seac_stats"]
get_seac = _rotas["get_seac"]
