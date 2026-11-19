#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
# Cronometragem de etapas do pipeline. Para ser `source`ado.
#
#   OPS_RUNS_FILE=data/ops/runs/AAAA-MM-DD.jsonl
#   step `lg_ixbr` $WORKER python -m sources.lg_ixbr.collect --date "$DATE" || die "`lg_ixbr` falhou"
#
# `step ROTULO COMANDO...` executa o comando, devolve o MESMO código de saída (não
# altera a ordem nem a política de falha do chamador) e anexa uma linha JSON:
#   {"step","module","start","end","duration_s","exit","status"}
# Falha ao gravar o registro nunca interrompe o pipeline.

# Rótulo/módulo só com caracteres seguros para JSON (sem aspas nem barra invertida).
_steps_json_safe() { printf '%s' "$1" | tr -c 'A-Za-z0-9_./:+-' '_'; }

step_record() {
    local label module start_iso end_iso duration rc status
    label="$(_steps_json_safe "$1")"; module="$(_steps_json_safe "$2")"
    start_iso="$3"; end_iso="$4"; duration="$5"; rc="$6"
    if [[ "$rc" -eq 0 ]]; then status="ok"; else status="falha"; fi
    [[ -n "${OPS_RUNS_FILE:-}" ]] || return 0
    mkdir -p "$(dirname "$OPS_RUNS_FILE")" 2>/dev/null || return 0
    printf '{"step":"%s","module":"%s","start":"%s","end":"%s","duration_s":%d,"exit":%d,"status":"%s"}\n' \
        "$label" "$module" "$start_iso" "$end_iso" "$duration" "$rc" "$status" \
        >> "$OPS_RUNS_FILE" 2>/dev/null || true
}

step() {
    local label="$1"; shift
    local module="" prev="" arg
    for arg in "$@"; do
        if [[ "$prev" == "-m" ]]; then module="$arg"; break; fi
        prev="$arg"
    done
    local t0 t1 iso0 iso1 rc
    t0=$(date -u +%s); iso0=$(date -u +%FT%TZ)
    "$@"
    rc=$?
    t1=$(date -u +%s); iso1=$(date -u +%FT%TZ)
    step_record "$label" "$module" "$iso0" "$iso1" "$((t1 - t0))" "$rc"
    return "$rc"
}
