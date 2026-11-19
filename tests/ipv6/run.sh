#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
#
# T7 IPv6: laboratório do v6bench (Kathará + TAYGA, sem root, sem módulo de kernel)
# com o Arandurapé (API + gate + nginx sobre o dataset sintético) como alvo.
# Não usa a Internet na execução nem servidores reais; só Docker e Kathará.
#
# Uso:
#   KATHARA="$HOME/.venvs/kathara/bin/python -m kathara" bash tests/ipv6/run.sh
#   bash tests/ipv6/run.sh --sem-build      # reaproveita as imagens já construídas
# Variáveis: KATHARA (padrão: "kathara" do PATH), RESULTADOS (diretório de saída;
# padrão: um temporário, impresso no fim). Requisitos e leitura: tests/ipv6/README.md.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$RAIZ"
V6="tests/ipv6/v6bench/v6bench"
BUILD=1
[[ "${1:-}" == "--sem-build" ]] && BUILD=0

if [[ -z "${KATHARA:-}" ]]; then
    if command -v kathara >/dev/null 2>&1; then
        KATHARA=kathara
    else
        echo "erro: Kathará não encontrado; instale (pip install -r tests/ipv6/requirements.txt num venv) e passe KATHARA=\"<venv>/bin/python -m kathara\"" >&2
        exit 2
    fi
fi
export KATHARA

if [[ $BUILD -eq 1 ]]; then
    echo "Construindo as imagens do laboratório"
    docker build -q -t v6bench/translator:local "$V6/images/translator" >/dev/null
    docker build -q -t v6bench/client:local "$V6/images/client" >/dev/null
    docker build -q -f Dockerfile.api -t arandurape-v6lab-api:local . >/dev/null
    docker build -q -f tests/ipv6/alvo/Dockerfile --build-arg API_IMAGE=arandurape-v6lab-api:local \
        -t arandurape-v6lab-alvo:local . >/dev/null
fi

RESULTADOS="${RESULTADOS:-$(mktemp -d "${TMPDIR:-/tmp}/t7-ipv6.XXXXXX")/resultados}"

lab=0
sh "$V6/run_lab.sh" -d arandurape.test -4 192.168.0.80 -6 2001:db8:1::80 \
    -t tests/ipv6/alvo/lab -p tests/ipv6/scanapi.yaml -c tests/ipv6/checks \
    -e tests/ipv6/lab.env -w alvo -x alvo -r "$RESULTADOS" || lab=$?

verif=0
python3 tests/ipv6/verificar.py "$RESULTADOS" tests/ipv6/esperado.json || verif=$?

echo "Resultados: $RESULTADOS"
if [[ $lab -ne 0 || $verif -ne 0 ]]; then
    exit 1
fi
