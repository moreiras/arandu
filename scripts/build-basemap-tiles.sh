#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
#
# build-basemap-tiles.sh — Gera uma nova versão do basemap vetorial
# (tiles OpenStreetMap/OpenMapTiles em PMTiles) auto-hospedado.
#
# Não sobrescreve versões existentes: cada execução grava em
# data/tiles/<DATA>/. A versão só passa a ser servida em produção depois
# de validada (ver validate-basemap-tiles.sh) e marcada com o arquivo
# sentinela `_valid`.
#
# Uso:
#   bash scripts/build-basemap-tiles.sh [--date YYYY-MM-DD] [--area REGIAO] [--force]
#
#   --date   Data do snapshot de tiles (default: hoje, UTC).
#   --area   Região a extrair via Geofabrik pra dado OSM detalhado (default:
#            south-america). Ver nomes válidos em https://download.geofabrik.de/
#   --force  Reconstrói mesmo se data/tiles/<DATA>/basemap.pmtiles já existir.
#
# Importante: o output cobre o MUNDO INTEIRO (--bounds), não só --area. Os
# mapas usam projeção de globo giratório — o usuário pode rotacionar/dar zoom
# out e ver qualquer parte do planeta, então o tileset precisa ter alguma
# cobertura em todo lugar (senão aparece "sem mapa" fora da região do
# --area). --area continua controlando de onde vem o dado OSM DETALHADO
# (ruas, o que houver); o resto do mundo usa as fontes já globais que o
# Planetiler baixa de qualquer forma (natural_earth, water_polygons) — nomes
# de país/cidade e água/terra em baixo zoom, sem precisar baixar o planeta
# inteiro em OSM.
#
# Requer Docker. Baixa um extrato OSM (~1-2 GB para América do Sul) na
# primeira execução; extratos ficam em cache (data/tiles/_cache/) e são
# reaproveitados/atualizados nas próximas.

set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TILES_DIR="$REPO_DIR/data/tiles"
CACHE_DIR="$TILES_DIR/_cache"

AREA="south-america"
DATE=$(date -u +%F)
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --date) DATE="$2"; shift 2 ;;
    --area) AREA="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    *) echo "Argumento desconhecido: $1" >&2; exit 1 ;;
  esac
done

OUT_DIR="$TILES_DIR/$DATE"
OUT_FILE="$OUT_DIR/basemap.pmtiles"

log() { echo "[$(date -u +%FT%TZ)] $*"; }
die() { log "ERRO: $*"; exit 1; }

command -v docker >/dev/null 2>&1 || die "Docker não encontrado"

if [[ -f "$OUT_FILE" && "$FORCE" -ne 1 ]]; then
  log "Já existe $OUT_FILE — use --force para reconstruir. Nada a fazer."
  exit 0
fi

mkdir -p "$OUT_DIR" "$CACHE_DIR" || die "não foi possível criar diretórios em $TILES_DIR"

log "=== build de basemap iniciado — área=$AREA, data=$DATE ==="

# Planetiler baixa (e faz cache de) o extrato Geofabrik da área e gera o
# PMTiles com o schema OpenMapTiles. --maxzoom 14 cobre bem além do zoom
# máximo hoje usado nos mapas do frontend (12); dá margem para o Localizador
# aproximar até rua/quarteirão sem precisar de um novo build.
docker run --rm \
  -v "$CACHE_DIR":/data \
  -v "$OUT_DIR":/out \
  ghcr.io/onthegomap/planetiler:latest \
  --area="$AREA" --download \
  --bounds=-180,-85,180,85 \
  --maxzoom=14 \
  --output=/out/basemap.pmtiles \
  || die "planetiler falhou"

[[ -s "$OUT_FILE" ]] || die "planetiler não gerou $OUT_FILE"

log "basemap.pmtiles gerado em $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"
log "Próximo passo: bash scripts/validate-basemap-tiles.sh --date $DATE"
