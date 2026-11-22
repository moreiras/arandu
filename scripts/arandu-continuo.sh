#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
# Trilha contínua: as coletas em rodízio diário com orçamento (`continua: true` no catálogo; hoje o Alice-LG do IX.br e o RDAP de
# contatos do Registro.br) rodam aqui, fora do `arandu-weekly.sh`, no serviço `worker_continuo` (teto de memória próprio), com lock e
# relatório próprios (data/ops/runs/continuo/AAAA-MM-DD.json). O pipeline não as coleta: restaura do armazém a última versão que esta
# trilha registrou. As duas trilhas podem rodar ao mesmo tempo: nenhuma etapa do pipeline fala com os destinos destas (lg.ix.br,
# rdap.registro.br), e a cortesia é por destino.
#
#   bash scripts/arandu-continuo.sh
#
# Cron do usuário (scripts/instalar.sh), uma vez por dia, num horário em que termine antes do pipeline das 04:00: o snapshot do dia
# leva a coleta da noite. Variáveis: DATE (padrão: hoje, UTC), ALERTA_CMD (padrão: scripts/alerta-telegram.sh; vazio = sem alerta).
# Saída: 0 = ok ou já em andamento (outra instância); 1 = alguma etapa falhou; outro código = o executor não rodou.
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

if grep -qE '^WEB_NETWORK_NAME=.+' "$REPO_DIR/.env" 2>/dev/null; then
    COMPOSE="docker compose -f docker-compose.yml -f docker-compose.no-nginx.yml"
else
    COMPOSE="docker compose -f docker-compose.yml"
fi
WORKER="${WORKER_CONTINUO:-$COMPOSE --profile worker run --rm --no-TTY -e ARANDU_COMPOSE worker_continuo}"
DATE="${DATE:-$(date -u +%F)}"
DADOS="${ARANDU_DADOS_HOST:-$REPO_DIR/data}"
log() { echo "[$(date -u +%FT%TZ)] $*"; }

log "=== trilha contínua iniciada — $DATE ==="
$WORKER python -m arandu continuo --date "$DATE"
RC=$?
if [[ $RC -eq 3 ]]; then
    log "a trilha contínua já está em andamento (lock): nada a fazer"
    exit 0
fi
if [[ $RC -ne 0 ]]; then
    etapas=$(python3 - "$DADOS/ops/runs/continuo/$DATE.json" 2>/dev/null <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, ValueError):
    sys.exit(0)
for e in d.get("etapas", []):
    if e.get("status") == "falha":
        print(f"- {e.get('id')}: {e.get('motivo') or 'falha'}")
PY
)
    msg="trilha contínua $DATE: terminou com código $RC"
    [[ -n "$etapas" ]] && msg+=$'\n'"$etapas"
    msg+=$'\n'"log: logs/arandu-continuo.log"
    cmd="${ALERTA_CMD-bash $REPO_DIR/scripts/alerta-telegram.sh}"
    [[ -n "$cmd" ]] && { printf '%s\n' "$msg" | ALERTA_CHAVE="continuo-$DATE-$RC" sh -c "$cmd" || log "AVISO: alerta não enviado"; }
fi
log "=== trilha contínua concluída — $DATE (código $RC) ==="
exit "$RC"
