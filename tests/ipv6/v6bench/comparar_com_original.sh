#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
#
# Mostra o diff desta cópia do v6bench contra o original no commit de origem
# (ORIGEM em MODIFICACOES.md). Serve para revisar as modificações sem depender
# do histórico do git do Arandurapé e para preparar contribuições ao projeto.
#
# Uso: bash tests/ipv6/v6bench/comparar_com_original.sh [DIR_DO_ORIGINAL]
#   sem argumento, clona https://github.com/CEPTRO-br/v6bench num temporário.
set -euo pipefail

ORIGEM_URL="https://github.com/CEPTRO-br/v6bench.git"
ORIGEM_COMMIT="c61474ecdf7dcd8da63cd77cc141955a3d58cf93"
AQUI="$(cd "$(dirname "$0")" && pwd)"

if [[ -n "${1:-}" ]]; then
    ORIG="$1"
else
    TMP="$(mktemp -d)"
    trap 'rm -rf "$TMP"' EXIT
    git clone -q "$ORIGEM_URL" "$TMP/v6bench"
    git -C "$TMP/v6bench" checkout -q "$ORIGEM_COMMIT"
    ORIG="$TMP/v6bench"
fi

# Ficam fora: o .git do original e os arquivos que só existem aqui para
# documentar a cópia (este script e MODIFICACOES.md).
diff -ruN \
    --exclude=.git \
    --exclude=MODIFICACOES.md \
    --exclude=comparar_com_original.sh \
    "$ORIG" "$AQUI" || true
