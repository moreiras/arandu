#!/bin/sh
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
#
# Pronto = o nginx responde e a API atrás dele também (run_lab.sh -w alvo).
curl -sf -m 3 -o /dev/null http://127.0.0.1:8080/health
