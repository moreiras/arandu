# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Repositórios de artefatos publicados: cada um lê e guarda em cache um tipo de arquivo de `published/{data}/`.

O `Store` continua sendo a fachada com os mesmos métodos públicos e aponta para estes repositórios.
"""
