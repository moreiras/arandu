#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
# Roda um comando segurando o MESMO lock do pipeline diário (o do cron: `flock -n /tmp/arandurape-run.lock bash scripts/arandu-weekly.sh`),
# para uma coleta ou um produto feito à mão nunca rodar junto com o pipeline (nem duas coletas manuais juntas). Em máquina pequena isso importa: com
# 7,9 GiB de RAM, o pipeline ao lado de uma coleta pesada trava a máquina. Se o lock estiver ocupado, o pipeline do cron
# simplesmente não roda naquele dia (o `flock -n` dele desiste): é melhor perder uma rodada do que duas rodadas ao mesmo tempo.
#
# Uso:  bash scripts/arandu-exclusivo.sh [--esperar SEGUNDOS] -- comando args...
# Ex.:  bash scripts/arandu-exclusivo.sh -- docker compose --profile worker run --rm worker python -m sources.anatel_rqual.collect --date 2026-11-06
#
# Sem --esperar, desiste na hora (saída 75) se houver outra execução. Com --esperar N, aguarda até N segundos. O lock é solto quando o comando termina.
# Variável: ARANDU_LOCK (padrão /tmp/arandurape-run.lock; precisa ser o mesmo arquivo do cron).
set -uo pipefail
LOCK="${ARANDU_LOCK:-/tmp/arandurape-run.lock}"
ESPERA=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --esperar) ESPERA="${2:-}"; shift 2 ;;
        --) shift; break ;;
        *) break ;;
    esac
done
if [[ $# -eq 0 ]] || ! [[ "$ESPERA" =~ ^[0-9]+$ ]]; then
    echo "uso: $0 [--esperar SEGUNDOS] -- comando args..." >&2
    exit 2
fi
command -v flock >/dev/null || { echo "[arandu-exclusivo] flock não encontrado (util-linux); não dá para garantir a exclusão" >&2; exit 2; }
exec 9>"$LOCK"
if (( ESPERA > 0 )); then
    flock -w "$ESPERA" 9 || { echo "[arandu-exclusivo] outra execução (pipeline ou coleta) segura $LOCK; esperei ${ESPERA}s" >&2; exit 75; }
else
    flock -n 9 || { echo "[arandu-exclusivo] outra execução (pipeline ou coleta) segura $LOCK; tente depois ou use --esperar" >&2; exit 75; }
fi
echo "[arandu-exclusivo] lock obtido: $*" >&2
"$@"
