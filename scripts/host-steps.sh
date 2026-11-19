#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
# Etapas de host do pipeline: aquecimento da API, basemap e relatório de disco.
# Dependem de `docker compose` no host e por isso não rodam dentro do worker (onde roda o `arandu`).
#
#   Sozinho, depois de `arandu run`:    bash scripts/host-steps.sh --date AAAA-MM-DD
#   Como biblioteca (source):           run_host_steps          (usa REPO_DIR, COMPOSE, DATE, log e step)
#
# Cada etapa leva o id do catálogo (catalog/steps/host_*.yaml) no log e no registro de tempos.
#
# Nunca bloqueiam o pipeline: toda falha vira aviso.

run_host_steps() {
# Warm-up: pré-carrega os índices do novo snapshot na API sem precisar reiniciá-la.
# Dispara também o pré-aquecimento do byte-cache (latest + top-1000 ASNs por clientes).
# Chama diretamente o container api via rede interna Docker (sem depender do nginx).
log "[host_warmup] Aquecendo caches da API com snapshot $DATE..."
step "host_warmup" $COMPOSE exec -T api python -c "
import os, urllib.request, json, sys
url = 'http://localhost:8000/api/v1/warmup?date=$DATE'
req = urllib.request.Request(url, data=b'', method='POST')
token = os.environ.get('INTERNAL_API_TOKEN', '')
if token:
    req.add_header('X-Internal-Token', token)
try:
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read())
    print(result)
    sys.exit(0 if result.get('status') == 'ok' else 1)
except Exception as e:
    print(f'erro: {e}', file=sys.stderr)
    sys.exit(1)
" && log "[host_warmup] Concluído." || log "[host_warmup] AVISO: warm-up falhou ou API não disponível — próxima requisição aquecerá automaticamente."


# Basemap vetorial auto-hospedado (tiles OSM) — cartografia muda pouco perto
# dos dados do Arandurape, então só reconstrói se a versão atual for velha
# (ou não existir ainda). Nunca bloqueia o pipeline: falha aqui vira só
# aviso, e o basemap anterior (já validado) continua sendo servido.
# O cron não carrega o .env: sem a variável no ambiente, ela é lida de lá (em máquina com 7,9 GiB e disco lento, o Planetiler
# da América do Sul passa de 10 h segurando o lock do pipeline; ali o limite fica alto e o basemap vem de fora).
if [[ -z "${BASEMAP_MAX_AGE_DAYS:-}" && -f "$REPO_DIR/.env" ]]; then
    BASEMAP_MAX_AGE_DAYS=$(sed -n 's/^BASEMAP_MAX_AGE_DAYS=\([0-9][0-9]*\)[[:space:]]*$/\1/p' "$REPO_DIR/.env" | tail -1)
fi
BASEMAP_MAX_AGE_DAYS="${BASEMAP_MAX_AGE_DAYS:-30}"
CURRENT_TILES_JSON="$REPO_DIR/data/tiles/current.json"
NEEDS_BASEMAP_BUILD=1
if [[ -f "$CURRENT_TILES_JSON" ]]; then
    AGE_DAYS=$(python3 -c "
import json, datetime
try:
    current = json.load(open('$CURRENT_TILES_JSON'))['date']
    age = (datetime.date.fromisoformat('$DATE') - datetime.date.fromisoformat(current)).days
    print(age)
except Exception:
    print(-1)
")
    if [[ "$AGE_DAYS" -ge 0 && "$AGE_DAYS" -lt "$BASEMAP_MAX_AGE_DAYS" ]]; then
        NEEDS_BASEMAP_BUILD=0
        log "[host_basemap] versão atual tem $AGE_DAYS dia(s) — dentro do limite de $BASEMAP_MAX_AGE_DAYS, não reconstrói."
    fi
fi
# Reconstruir exige ~2× o espaço de uma versão: com o disco no limite de bloqueio (arandu doctor), mantém a versão atual.
DISK_PCT=$(df -P "$REPO_DIR/data" | awk 'NR==2 {gsub("%","",$5); print $5}')
if [[ "$NEEDS_BASEMAP_BUILD" -eq 1 && "${DISK_PCT:-0}" -ge "${ARANDU_BLOQUEIO_DISCO_PCT:-85}" ]]; then
    log "[host_basemap] AVISO: disco com ${DISK_PCT}% de uso — não reconstrói o basemap (libere espaço: arandu gc --dry-run)."
    NEEDS_BASEMAP_BUILD=0
fi
if [[ "$NEEDS_BASEMAP_BUILD" -eq 1 ]]; then
    log "[host_basemap] Gerando nova versão do basemap vetorial (tiles OSM)..."
    if step "host_basemap_build" bash "$REPO_DIR/scripts/build-basemap-tiles.sh" --date "$DATE"; then
        step "host_basemap_validate" bash "$REPO_DIR/scripts/validate-basemap-tiles.sh" --date "$DATE" || \
            log "[host_basemap] AVISO: validação falhou — mantendo versão anterior do basemap."
    else
        log "[host_basemap] AVISO: build do basemap falhou — mantendo versão anterior."
    fi
fi

# Relatório de disco (du por tipo/data, df e inodes) — somente leitura, nunca bloqueia.
log "[host_disk_report] Relatório de uso de disco..."
step "host_disk_report" bash "$REPO_DIR/scripts/disk-report.sh" --date "$DATE" || \
    log "[host_disk_report] AVISO: relatório de disco falhou"
}

# Execução direta: monta o ambiente (compose, registro de tempos e log).
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    set -uo pipefail
    REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    cd "$REPO_DIR"
    DATE=$(date -u +%F)
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --date) DATE="$2"; shift 2 ;;
            *) echo "uso: $0 [--date AAAA-MM-DD]" >&2; exit 2 ;;
        esac
    done
    if grep -qE '^WEB_NETWORK_NAME=.+' "$REPO_DIR/.env" 2>/dev/null; then
        COMPOSE="docker compose -f docker-compose.yml -f docker-compose.no-nginx.yml"
    else
        COMPOSE="docker compose -f docker-compose.yml"
    fi
    # shellcheck source=scripts/lib-steps.sh
    source "$REPO_DIR/scripts/lib-steps.sh"
    OPS_RUNS_FILE="$REPO_DIR/data/ops/runs/$DATE.host.jsonl"   # separado do relatório do arandu ($DATE.json)
    log() { echo "[$(date -u +%FT%TZ)] $*"; }
    run_host_steps
fi
