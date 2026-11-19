#!/bin/sh
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
#
# Depois dos testes (run_lab.sh -x alvo): leva para os resultados o log de uso
# (para conferir que não grava IP) e os logs da API e do gate.
mkdir -p /shared/results/alvo
cp -R /data/ops/usage /shared/results/alvo/ 2>/dev/null || true
cp /var/log/api.log /var/log/gate.log /shared/results/alvo/ 2>/dev/null || true
