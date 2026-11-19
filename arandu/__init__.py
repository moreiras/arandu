# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""arandu — executor e CLI do pipeline do Arandurapé.

Lê o catálogo (`catalog/`), calcula a ordem das etapas e as executa com política de falha por etapa,
relatório por execução, lock e retomada. O cron o chama por `scripts/arandu-weekly.sh`.
Roda dentro do container worker: `docker compose run --rm worker python -m arandu run --date AAAA-MM-DD`.
"""
