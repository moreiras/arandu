#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
#
# rollback-basemap.sh — Invalida manualmente uma versão do basemap
# (ex.: problema só percebido depois de já estar em produção) e recalcula
# "atual" para a versão válida anterior.
#
# Uso:
#   bash scripts/rollback-basemap.sh --date YYYY-MM-DD
#
# Remove o sentinela `_valid` da data indicada (não apaga os arquivos —
# use delete-snapshot.sh-like cleanup manual se quiser liberar espaço depois)
# e reescreve data/tiles/current.json com a data válida mais recente restante.

set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TILES_DIR="$REPO_DIR/data/tiles"

DATE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --date) DATE="$2"; shift 2 ;;
    *) echo "Argumento desconhecido: $1" >&2; exit 1 ;;
  esac
done

log() { echo "[$(date -u +%FT%TZ)] $*"; }
die() { log "ERRO: $*"; exit 1; }

[[ -n "$DATE" ]] || die "uso: --date YYYY-MM-DD"

SENTINEL="$TILES_DIR/$DATE/_valid"
[[ -f "$SENTINEL" ]] || die "$SENTINEL não existe (essa data já não estava marcada como válida?)"

rm -f "$SENTINEL"
log "removido $SENTINEL — $DATE não é mais considerada válida"

LATEST_VALID=""
for d in "$TILES_DIR"/*/; do
  d_name=$(basename "$d")
  [[ -f "$d/_valid" ]] || continue
  if [[ -z "$LATEST_VALID" || "$d_name" > "$LATEST_VALID" ]]; then
    LATEST_VALID="$d_name"
  fi
done

if [[ -z "$LATEST_VALID" ]]; then
  log "AVISO: nenhuma versão válida restante — removendo current.json/current.pmtiles. O basemap ficará indisponível até um novo build passar na validação."
  rm -f "$TILES_DIR/current.json" "$TILES_DIR/current.pmtiles"
  exit 0
fi

TMP_JSON="$TILES_DIR/.current.json.tmp"
printf '{"date":"%s"}\n' "$LATEST_VALID" > "$TMP_JSON"
mv -f "$TMP_JSON" "$TILES_DIR/current.json"
ln -sfn "$LATEST_VALID/basemap.pmtiles" "$TILES_DIR/current.pmtiles"
log "current → $LATEST_VALID (rollback concluído)"
