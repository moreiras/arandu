#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
#
# Prepara data/ para a API rodar sem root e com data/ só leitura.
#
#   sudo bash scripts/preparar-dados-api-sem-root.sh [--uid 1001] [--dry-run]     # Docker com root
#   bash scripts/preparar-dados-api-sem-root.sh [--uid 1001] [--dry-run]          # Docker rootless, como o usuário do serviço
#
# A API só grava em data/auth, data/ops/usage, data/ops/uso_conta e data/cache/br11. Este script cria o que faltar e entrega esses
# diretórios ao usuário da imagem (appuser, UID 1001, grupo 0), com 0770 nos diretórios e 0660 nos arquivos, e não
# `chmod a+rw data/auth/*` (qualquer usuário do host leria e-mails e IPs). Não toca published/, raw/ nem normalized/.
# Com Docker rootless o UID 1001 do contêiner é outro UID no host (subuid): um `chown 1001` no host entregaria os dados a quem tem o
# UID 1001 do host. Por isso, no rootless, o chown roda dentro de um contêiner descartável da imagem da API (PREPARAR_IMAGEM,
# padrão arandurape-api:latest: construa antes), sem rede, e sem sudo.
#
# Depois, no .env: API_USER=1001:0 e API_DATA_MODE=ro, e restart-safe.sh. Para voltar: apague as duas linhas do .env e reinicie;
# a API como root (cap_drop ALL, sem DAC_OVERRIDE) continua gravando pelos bits de grupo (grupo 0, 0660/0770).
set -euo pipefail

UID_API=1001
DRY=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --uid) UID_API="${2:?}"; shift 2 ;;
        --dry-run) DRY=true; shift ;;
        -h|--help) sed -n 8,21p "$0"; exit 0 ;;
        *) echo "argumento desconhecido: $1" >&2; exit 2 ;;
    esac
done
[[ "$UID_API" =~ ^[0-9]+$ ]] || { echo "--uid precisa ser numérico" >&2; exit 2; }
SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib-docker.sh
source "$SCRIPTS/lib-docker.sh"
DATA="$(cd "$SCRIPTS/.." && pwd)/data"
[[ -d "$DATA/published" ]] || { echo "não achei $DATA/published" >&2; exit 1; }

faz() { echo "+ $*"; $DRY || "$@"; }

# O mesmo procedimento nos dois modos; no rootless roda como root do contêiner, que é o usuário do serviço no host.
read -r -d '' PASSOS <<'SH' || true
set -eu
u="$1"; data="$2"
for d in auth ops/usage ops/uso_conta cache/br11; do
    alvo="$data/$d"
    mkdir -p "$alvo"
    chown -R "$u:0" "$alvo"
    find "$alvo" -type d -exec chmod 0770 {} +
    find "$alvo" -type f -exec chmod 0660 {} +
done
# os pais precisam ser atravessáveis pelo usuário da API (sem dar escrita)
chmod o+x "$data" "$data/ops" "$data/cache"
SH

if docker_rootless; then
    [[ "$(id -u)" -ne 0 ]] || { echo "Docker rootless: rode como o usuário do serviço, sem sudo (o root não enxerga o daemon dele)" >&2; exit 1; }
    IMAGEM="${PREPARAR_IMAGEM:-arandurape-api:latest}"
    $DRY || docker image inspect "$IMAGEM" >/dev/null 2>&1 \
        || { echo "falta a imagem $IMAGEM: rode antes 'docker compose build api'" >&2; exit 1; }
    mkdir -p "$DATA/ops" "$DATA/cache"
    faz docker run --rm --network none --user 0:0 --entrypoint sh -v "$DATA:/data" "$IMAGEM" -c "$PASSOS" sh "$UID_API" /data
else
    [[ "$(id -u)" -eq 0 ]] || { echo "rode com sudo" >&2; exit 1; }
    if $DRY; then
        echo "+ (como root) chown -R $UID_API:0 e chmod 0770/0660 em $DATA/{auth,ops/usage,ops/uso_conta,cache/br11}; chmod o+x nos pais"
    else
        bash -c "$PASSOS" sh "$UID_API" "$DATA"
    fi
fi
echo "pronto: defina API_USER=$UID_API:0 e API_DATA_MODE=ro no .env e rode restart-safe.sh"
