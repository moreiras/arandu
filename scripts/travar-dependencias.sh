#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
#
# Regrava os locks das dependências Python com hash de cada arquivo:
#   requirements.lock      — produção (Dockerfile.api instala com --require-hashes)
#   requirements-dev.lock  — produção + testes (CI e desenvolvimento), com as MESMAS versões de produção
#
#   bash scripts/travar-dependencias.sh            # regrava a partir de requirements.txt e requirements-dev.txt
#   bash scripts/travar-dependencias.sh --upgrade  # também sobe as transitivas para a versão mais nova compatível
#
# requirements*.txt seguem sendo o que se edita (dependências diretas, versão fixa); o lock acrescenta as transitivas e os hashes,
# para que dois builds da mesma versão instalem exatamente os mesmos arquivos. Resolve na imagem-base do Dockerfile.api (Python e
# plataforma de produção). tests/unit/test_lock_dependencias.py reprova se um lock ficar para trás do requirements*.txt.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
IMAGE=$(sed -n 's/^FROM \(python:[^ ]*\).*/\1/p' Dockerfile.api | head -1)
[[ -n "$IMAGE" ]] || { echo "ERRO: imagem-base não encontrada no Dockerfile.api" >&2; exit 1; }
UPGRADE=""
case "${1:-}" in
    "") ;;
    --upgrade) UPGRADE="--upgrade" ;;
    *) echo "uso: $0 [--upgrade]" >&2; exit 2 ;;
esac
PIP_TOOLS=7.7.0
docker run --rm -v "$PWD:/app" -w /app -e PIP_DISABLE_PIP_VERSION_CHECK=1 -e PIP_ROOT_USER_ACTION=ignore "$IMAGE" sh -c "
  set -e
  pip install --quiet --no-cache-dir pip-tools==$PIP_TOOLS
  opts='--quiet --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url --resolver=backtracking $UPGRADE'
  CUSTOM_COMPILE_COMMAND='bash scripts/travar-dependencias.sh' pip-compile \$opts -o requirements.lock requirements.txt
  CUSTOM_COMPILE_COMMAND='bash scripts/travar-dependencias.sh' pip-compile \$opts -c requirements.lock -o requirements-dev.lock requirements.txt requirements-dev.txt
"
echo "locks regravados: requirements.lock, requirements-dev.lock (confira o diff)"
