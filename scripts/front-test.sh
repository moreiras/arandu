#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
# Testes do frontend via Docker — Node/npm não existem localmente.
# Usa a MESMA imagem Node do Dockerfile.frontend. Etapas: tsc → vitest → build.
#   bash scripts/front-test.sh           # tsc + vitest + build
#   bash scripts/front-test.sh --quick   # só vitest
#   bash scripts/front-test.sh --gen-tipos   # regenera os tipos do OpenAPI
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
IMG=$(sed -n 's/^FROM \(node:[^ ]*\).*/\1/p' Dockerfile.frontend | head -1)
[[ -n "$IMG" ]] || { echo "ERRO: imagem Node não encontrada no Dockerfile.frontend" >&2; exit 1; }
# Rodada completa: `npm audit --omit=dev` mostra as vulnerabilidades conhecidas do que vai ao navegador (informativo, não reprova;
# o portão com exceções registradas vem com o SBOM).
CMD='npm ci --no-audit --no-fund --silent && { npm audit --omit=dev || true; } && npx tsc --noEmit && npx vitest run && npm run build:only --silent'
# --gen-tipos: regenera frontend/src/types/openapi.gen.ts a partir de openapi.json (python3 scripts/gen_openapi.py antes)
[[ "${1:-}" == "--gen-tipos" ]] && CMD='npm ci --no-audit --no-fund --silent && npx openapi-typescript src/types/openapi.json -o src/types/openapi.gen.ts'
[[ "${1:-}" == "--quick" ]] && CMD='npm ci --no-audit --no-fund --silent && npx vitest run'
# node_modules num volume nomeado: não suja o checkout nem herda binários de outra plataforma
exec docker run --rm -v "$PWD:/repo" -v arandu-fe-node-modules:/repo/frontend/node_modules -w /repo/frontend "$IMG" sh -c "$CMD"
