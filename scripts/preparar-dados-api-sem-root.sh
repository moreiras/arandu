#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
#
# Prepara data/ para a API rodar sem root e com data/ só leitura.
#
#   sudo bash scripts/preparar-dados-api-sem-root.sh [--uid 1001] [--dry-run]
#
# A API só grava em data/auth, data/ops/usage, data/ops/uso_conta e data/cache/br11. Este script cria o que faltar e entrega esses
# diretórios ao usuário da imagem (appuser, UID 1001, grupo 0), com 0770 nos diretórios e 0660 nos arquivos, e não
# `chmod a+rw data/auth/*` (qualquer usuário do host leria e-mails e IPs). Não toca published/, raw/ nem normalized/.
#
# Depois, no .env: API_USER=1001:0 e API_DATA_MODE=ro, e `sudo bash restart-safe.sh`. Para voltar: apague as duas linhas do .env e reinicie;
# a API como root (cap_drop ALL, sem DAC_OVERRIDE) continua gravando pelos bits de grupo (grupo 0, 0660/0770).
set -euo pipefail

UID_API=1001
DRY=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --uid) UID_API="${2:?}"; shift 2 ;;
        --dry-run) DRY=true; shift ;;
        -h|--help) sed -n 8,18p "$0"; exit 0 ;;
        *) echo "argumento desconhecido: $1" >&2; exit 2 ;;
    esac
done
[[ "$(id -u)" -eq 0 ]] || { echo "rode com sudo" >&2; exit 1; }
DATA="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/data"
[[ -d "$DATA/published" ]] || { echo "não achei $DATA/published" >&2; exit 1; }

faz() { echo "+ $*"; $DRY || "$@"; }
for d in auth ops/usage ops/uso_conta cache/br11; do
    alvo="$DATA/$d"
    [[ -d "$alvo" ]] || faz mkdir -p "$alvo"
    faz chown -R "$UID_API:0" "$alvo"
    faz find "$alvo" -type d -exec chmod 0770 {} +
    faz find "$alvo" -type f -exec chmod 0660 {} +
done
# os pais precisam ser atravessáveis pelo usuário da API (sem dar escrita)
for d in "$DATA" "$DATA/ops" "$DATA/cache"; do
    faz chmod o+x "$d"
done
echo "pronto: defina API_USER=$UID_API:0 e API_DATA_MODE=ro no .env e rode restart-safe.sh"
