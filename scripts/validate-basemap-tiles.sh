#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
#
# validate-basemap-tiles.sh — Valida um basemap.pmtiles recém-gerado e,
# se passar, promove essa data a "atual" (data/tiles/current.json).
#
# Não mexe em nada se a validação falhar: a pasta da data fica sem o
# sentinela `_valid`, e o `current.json` continua apontando pra última
# versão boa anterior — rollback automático, sem intervenção manual.
#
# Uso:
#   bash scripts/validate-basemap-tiles.sh --date YYYY-MM-DD
#
# Checagem aqui é estrutural e rápida (roda sem navegador, pra poder ser
# chamada de dentro do pipeline semanal sem depender de Docker/Playwright).
# A verificação visual completa (renderizar os 7 mapas) é feita à parte,
# manualmente ou via CI, antes de um rollout.

set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TILES_DIR="$REPO_DIR/data/tiles"

# Faixa de tamanho esperada para o extrato da América do Sul até zoom 14.
# Fora disso é sinal de build truncado ou de escopo muito diferente do previsto.
MIN_BYTES=$((50 * 1024 * 1024))          #  50 MB
MAX_BYTES=$((20 * 1024 * 1024 * 1024))   #  20 GB

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

FILE="$TILES_DIR/$DATE/basemap.pmtiles"
[[ -f "$FILE" ]] || die "$FILE não existe"

SIZE=$(stat -f%z "$FILE" 2>/dev/null || stat -c%s "$FILE")
log "arquivo: $FILE ($SIZE bytes)"

if (( SIZE < MIN_BYTES )); then
  die "arquivo menor que o mínimo esperado ($MIN_BYTES bytes) — build provavelmente truncado. Versão NÃO promovida."
fi
if (( SIZE > MAX_BYTES )); then
  die "arquivo maior que o máximo esperado ($MAX_BYTES bytes) — confira --area/--maxzoom do build. Versão NÃO promovida."
fi

MAGIC=$(python3 -c "print(open('$FILE','rb').read(7))")
if [[ "$MAGIC" != "b'PMTiles'" ]]; then
  die "cabeçalho inválido (esperado magic 'PMTiles', achou $MAGIC). Versão NÃO promovida."
fi

log "estrutura OK — gravando sentinela _valid"
touch "$TILES_DIR/$DATE/_valid"

# "Atual" = data mais recente entre as que têm _valid — recalculado do zero
# a cada validação (não confia em estado anterior), mesmo padrão do
# latest() dinâmico já usado pelos snapshots de dados (api/store.py).
LATEST_VALID=""
for d in "$TILES_DIR"/*/; do
  d_name=$(basename "$d")
  [[ -f "$d/_valid" ]] || continue
  if [[ -z "$LATEST_VALID" || "$d_name" > "$LATEST_VALID" ]]; then
    LATEST_VALID="$d_name"
  fi
done

[[ -n "$LATEST_VALID" ]] || die "nenhuma versão válida encontrada em $TILES_DIR (inesperado logo após validar uma)"

TMP_JSON="$TILES_DIR/.current.json.tmp"
printf '{"date":"%s"}\n' "$LATEST_VALID" > "$TMP_JSON"
mv -f "$TMP_JSON" "$TILES_DIR/current.json"

# current.pmtiles é o que o frontend de fato lê (ver mapTheme.ts) — symlink
# relativo, trocado atomicamente (ln -sfn) só depois de validado.
ln -sfn "$LATEST_VALID/basemap.pmtiles" "$TILES_DIR/current.pmtiles"

log "current → $LATEST_VALID (current.json + current.pmtiles atualizados)"
if [[ "$LATEST_VALID" != "$DATE" ]]; then
  log "AVISO: versão validada ($DATE) não é a mais recente válida — mantendo $LATEST_VALID como atual."
fi
