# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Camada de histórico: séries por entidade e log de eventos derivados dos snapshots publicados.

É uma camada derivada e reconstruível (`data/history/`, fora de `published/`, que segue imutável)."""
