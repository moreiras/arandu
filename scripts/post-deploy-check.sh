#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
# Verificação pós-implantação: só leitura contra a instância no ar.
# Uso: bash scripts/post-deploy-check.sh [--base URL] [--expect-version X.Y.Z] [--json]
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/post_deploy_check.py" "$@"
