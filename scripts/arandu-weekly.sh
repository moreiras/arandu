#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
# Pipeline pelo executor `arandu` (o que o cron chama).
#
#   0 4 * * *  cd /caminho/do/repo && flock -n /tmp/arandurape-run.lock bash scripts/arandu-weekly.sh >> logs/arandu.log 2>&1
#
# Coleta ou produto feito à mão no mesmo host NÃO pode rodar ao lado dele (memória): use scripts/arandu-exclusivo.sh, que pega este mesmo lock.
#
# 0. RPKI avulso (scripts/rpki-avulso.sh): o Routinator roda antes do worker, sozinho, e morre; a etapa rpki_collector do
#    worker só lê o arquivo. Falha ou timeout não param o pipeline (política opcional da etapa). Só roda quando a etapa vai rodar: ela
#    grava em published/, então com ARANDU_MODO=due fica fora dos dias sem publicação, e numa retomada já concluída não refaz.
# 1. `arandu run --retomar` no worker: executa as etapas de worker na ordem calculada do catálogo e retoma o que já
#    concluiu no dia;
# 2. etapas de host (aquecimento, basemap, disco): scripts/host-steps.sh, só se o pipeline não abortou;
# 3. com ARANDU_COMPARE=on, `arandu run --compare` (paridade com o replay), sem bloquear nada.
#
# Publicação: com ARANDU_MODO=due o cron pode rodar todo dia; a coleta segue a cadência de cada fonte e o snapshot só é publicado
# quando o anterior tem ARANDU_PUBLICACAO_DIAS dias ou mais (padrão 7; 0 ou 1 = um por execução). ARANDU_PUBLICAR=1 força a publicação hoje.
# Fora dessa janela as etapas de host e o compare não rodam (não há snapshot novo para aquecer nem comparar).
#
# Falhas: ao terminar, se algo falhou (código ≠ 0, etapa com falha no relatório data/ops/runs/DATA.json, Routinator avulso,
# etapas de host, compare, interrupção), uma mensagem só vai para scripts/alerta-telegram.sh (ALERTA_CMD troca o comando; "" desliga).
# Execução sem falha não manda nada.
#
# Variáveis: DATE (padrão: hoje, UTC), ARANDU_MODO (retomar|due), ARANDU_PUBLICACAO_DIAS, ARANDU_PUBLICAR, ARANDU_COMPARE, MEM_SAMPLE=off, MEM_SAMPLE_INTERVAL,
# MEM_SAMPLE_API_CONTAINER, HOST_STEPS (comando das etapas de host; para testes), RPKI_AVULSO=off (pula o Routinator avulso),
# RPKI_TIMEOUT_S.
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

if grep -qE '^WEB_NETWORK_NAME=.+' "$REPO_DIR/.env" 2>/dev/null; then
    COMPOSE="docker compose -f docker-compose.yml -f docker-compose.no-nginx.yml"
else
    COMPOSE="docker compose -f docker-compose.yml"
fi
WORKER="$COMPOSE --profile worker run --rm --no-TTY -e ARANDU_COMPOSE worker"
DATE="${DATE:-$(date -u +%F)}"
DADOS="${ARANDU_DADOS_HOST:-$REPO_DIR/data}"   # data/ visto do host (testes trocam)
HOST_STEPS="${HOST_STEPS:-bash $REPO_DIR/scripts/host-steps.sh --date $DATE}"
log() { echo "[$(date -u +%FT%TZ)] $*"; }
FALHAS=()
falha() { FALHAS+=("$*"); log "$*"; }

# Resumo das falhas do relatório do arandu (etapas com status falha, crítica ou não) e envio de uma mensagem só, no fim.
avisar() {
    local rc=$? relatorio="$DADOS/ops/runs/$DATE.json" etapas
    trap - EXIT
    etapas=$(python3 - "$relatorio" 2>/dev/null <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, ValueError):
    sys.exit(0)
for e in d.get("etapas", []):
    if e.get("status") == "falha":
        extra = f", {e['tentativas']} tentativas" if (e.get("tentativas") or 1) > 1 else ""
        print(f"- {e.get('id')} ({e.get('politica', '?')}): {e.get('motivo') or 'falha'}{extra}")
if d.get("abortada_em"):
    print(f"- abortado em {d['abortada_em']}")
PY
)
    [[ $rc -eq 0 && -z "$etapas" && ${#FALHAS[@]} -eq 0 ]] && return 0
    local msg="pipeline $DATE: "
    [[ $rc -eq 0 ]] && msg+="terminou com falhas" || msg+="falhou (código $rc)"
    [[ -n "$etapas" ]] && msg+=$'\n'"$etapas"
    local f; for f in ${FALHAS[@]+"${FALHAS[@]}"}; do msg+=$'\n'"- $f"; done
    msg+=$'\n'"log: logs/arandu.log"
    local cmd="${ALERTA_CMD-bash $REPO_DIR/scripts/alerta-telegram.sh}"
    [[ -n "$cmd" ]] && { printf '%s\n' "$msg" | ALERTA_CHAVE="pipeline-$DATE-$rc" sh -c "$cmd" || log "AVISO: alerta não enviado"; }
    return 0
}
trap avisar EXIT
trap 'falha "interrompido por sinal"; exit 143' TERM INT

log "=== arandu semanal iniciado — snapshot $DATE ==="

# Amostrador de memória: pico da API e do worker em data/ops/mem/.
if [[ "${MEM_SAMPLE:-on}" != "off" ]]; then
    ( python3 "$REPO_DIR/scripts/mem_sample.py" --out "$REPO_DIR/data/ops/mem/$DATE.jsonl" \
        --parent $$ --interval "${MEM_SAMPLE_INTERVAL:-30}" \
        --diag-container "${MEM_SAMPLE_API_CONTAINER:-arandurape-api}" >/dev/null 2>&1 & ) 2>/dev/null || true
fi

# ARANDU_MODO=due: só roda o que a cadência de cada fonte manda (restaura a última versão do armazém nas demais); padrão: retomar
if [[ "${ARANDU_MODO:-retomar}" == "due" ]]; then MODO=(--due --retomar); else MODO=(--retomar); fi
if [[ "${ARANDU_PUBLICAR:-0}" == "1" ]]; then MODO+=(--publicar); fi
rpki_hoje() {
    [[ "${RPKI_AVULSO:-on}" == "off" ]] && { log "[RPKI] RPKI_AVULSO=off: Routinator avulso não roda"; return 1; }
    [[ -f "$DADOS/published/$DATE/rpki/vrp_list.json.gz" ]] && { log "[RPKI] já publicado em $DATE (retomada): Routinator avulso não roda"; return 1; }
    [[ "${ARANDU_MODO:-retomar}" != "due" || "${ARANDU_PUBLICAR:-0}" == "1" ]] && return 0
    local porque
    porque=$(python3 "$REPO_DIR/arandu/publicacao.py" --date "$DATE" --data "$DADOS" 2>&1) && return 0
    # Saída 1 = janela fechada; outro erro (python ausente, etc.) = roda, por segurança.
    [[ $? -eq 1 ]] && { log "[RPKI] Routinator avulso não roda: $porque"; return 1; }
    return 0
}
if rpki_hoje; then
    bash "$REPO_DIR/scripts/rpki-avulso.sh" || falha "[RPKI] Routinator avulso falhou (ver o log); a etapa RPKI do dia deve falhar (opcional)"
fi
$WORKER python -m arandu run --date "$DATE" "${MODO[@]}"
RC=$?
if [[ $RC -ne 0 ]]; then
    log "ERRO: arandu run terminou com código $RC — etapas de host não executadas"
    exit "$RC"
fi

# Sem snapshot publicado nesta data (fora da janela de publicação) não há o que aquecer nem comparar.
if [[ ! -f "$DADOS/published/$DATE/manifest.json" && "${ARANDU_MODO:-retomar}" == "due" ]]; then
    log "[HOST] sem snapshot publicado em $DATE (fora da janela de publicação): etapas de host e compare não rodam"
    log "=== arandu semanal concluído — sem publicação em $DATE ==="
    exit 0
fi

log "[HOST] etapas de host..."
$HOST_STEPS || falha "[HOST] etapas de host terminaram com erro"

if [[ "${ARANDU_COMPARE:-off}" == "on" ]]; then
    log "[ARANDU] Paridade: arandu run --compare..."
    $WORKER python -m arandu run --compare --date "$DATE" || \
        falha "[ARANDU] o compare apontou diferenças novas ou falhou — ver data/ops/compare/$DATE.json"
fi
log "=== arandu semanal concluído — snapshot $DATE ==="
