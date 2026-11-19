#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
# delete-snapshot.sh — Remove todos os dados de um snapshot do Arandurape.
#
# Uso:
#   sudo bash delete-snapshot.sh --date YYYY-MM-DD
#
# Remove:
#   data/raw/<date>/
#   data/normalized/<date>/
#   data/published/<date>/
#   data/build/<date>/           (fragmentos do compose)
#
# Não remove caches, o armazém de versões de fonte (data/sources/) nem a série de data/history/.
#
# Requer ao menos 2 snapshots disponíveis; não apaga o único snapshot. Recusa rodar com o pipeline em andamento
# (mesmo lock do cron e de scripts/arandu-exclusivo.sh: ARANDU_LOCK, padrão /tmp/arandurape-run.lock).
# Para a retenção por política, use `python -m arandu gc`.

set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$REPO_DIR/data"

# ────────────────────────────────────────────────────────────
# Cores
# ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'
CYN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'

die() { echo -e "\n${RED}ERRO: $*${NC}" >&2; exit 1; }

# ────────────────────────────────────────────────────────────
# Argumentos
# ────────────────────────────────────────────────────────────
DATE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --date)   DATE="$2"; shift 2 ;;
        --date=*) DATE="${1#--date=}"; shift ;;
        -h|--help)
            echo "Uso: sudo bash delete-snapshot.sh --date YYYY-MM-DD"
            exit 0
            ;;
        *) die "Argumento desconhecido: $1. Uso: $0 --date YYYY-MM-DD" ;;
    esac
done

[[ -z "$DATE" ]] && die "--date é obrigatório. Uso: $0 --date YYYY-MM-DD"
[[ "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || die "Formato inválido: '$DATE' (esperado: YYYY-MM-DD)"

# ────────────────────────────────────────────────────────────
# Caminhos a remover
# ────────────────────────────────────────────────────────────
DIR_RAW="$DATA_DIR/raw/$DATE"
DIR_NORM="$DATA_DIR/normalized/$DATE"
DIR_PUB="$DATA_DIR/published/$DATE"
DIR_BUILD="$DATA_DIR/build/$DATE"

# ────────────────────────────────────────────────────────────
# Nunca ao lado do pipeline
# ────────────────────────────────────────────────────────────
LOCK="${ARANDU_LOCK:-/tmp/arandurape-run.lock}"
if command -v flock >/dev/null; then
    exec 9>"$LOCK"
    flock -n 9 || die "o pipeline (ou outra execução manual) segura $LOCK; tente depois"
else
    echo -e "${YEL}Aviso: flock não encontrado; confira à mão que o pipeline não está rodando.${NC}" >&2
fi

# ────────────────────────────────────────────────────────────
# Verifica quantos snapshots existem
# ────────────────────────────────────────────────────────────
ALL_SNAPSHOTS=()
while IFS= read -r d; do
    ALL_SNAPSHOTS+=("$(basename "$d")")
done < <(ls -d "$DATA_DIR/published"/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] 2>/dev/null | sort)

if [[ ${#ALL_SNAPSHOTS[@]} -eq 0 ]]; then
    die "Nenhum snapshot encontrado em $DATA_DIR/published/"
fi

if [[ ${#ALL_SNAPSHOTS[@]} -eq 1 ]]; then
    ONLY="${ALL_SNAPSHOTS[0]}"
    echo -e "\n${RED}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  OPERAÇÃO RECUSADA                                       ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════╝${NC}"
    echo -e "\n  Há apenas ${BOLD}um${NC} snapshot disponível: ${BOLD}$ONLY${NC}"
    echo -e "  Remover o único snapshot deixaria o serviço sem dados."
    echo -e "  Execute o pipeline para gerar um novo snapshot antes de remover este.\n"
    exit 2
fi

# ────────────────────────────────────────────────────────────
# Verifica se o snapshot alvo existe
# ────────────────────────────────────────────────────────────
FOUND=false
for s in "${ALL_SNAPSHOTS[@]}"; do
    [[ "$s" == "$DATE" ]] && { FOUND=true; break; }
done
$FOUND || die "Snapshot $DATE não encontrado em $DATA_DIR/published/ (disponíveis: ${ALL_SNAPSHOTS[*]})"

# ────────────────────────────────────────────────────────────
# Calcula tamanho total a ser removido
# ────────────────────────────────────────────────────────────
total_size() {
    local total=0
    for d in "$@"; do
        [[ -d "$d" ]] && total=$((total + $(du -sk "$d" 2>/dev/null | cut -f1)))
    done
    echo "${total} KB"
}

SIZE=$(total_size "$DIR_RAW" "$DIR_NORM" "$DIR_PUB" "$DIR_BUILD")

# ────────────────────────────────────────────────────────────
# Exibe resumo e pede confirmação
# ────────────────────────────────────────────────────────────
echo -e "\n${BOLD}${CYN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYN}║   delete-snapshot.sh                                     ║${NC}"
echo -e "${BOLD}${CYN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Snapshot alvo : ${BOLD}$DATE${NC}"
echo -e "  Tamanho total : ${BOLD}$SIZE${NC}"
echo -e "  Snapshots disponíveis após remoção: ${#ALL_SNAPSHOTS[@]} → $((${#ALL_SNAPSHOTS[@]} - 1))"
echo ""
echo -e "  Diretórios que serão ${RED}removidos permanentemente${NC}:"

for d in "$DIR_RAW" "$DIR_NORM" "$DIR_PUB" "$DIR_BUILD"; do
    if [[ -d "$d" ]]; then
        local_size=$(du -sh "$d" 2>/dev/null | cut -f1)
        echo -e "    ${RED}✗${NC}  $d  (${DIM}${local_size}${NC})"
    else
        echo -e "    ${DIM}~  $d  (não existe)${NC}"
    fi
done

echo ""
echo -e "  ${BOLD}${YEL}Esta operação é irreversível.${NC}"
echo ""
echo -e "  Para confirmar, digite exatamente: ${BOLD}apagar snapshot $DATE${NC}"
echo -n "  > "
read -r CONFIRM

EXPECTED="apagar snapshot $DATE"
if [[ "$CONFIRM" != "$EXPECTED" ]]; then
    echo -e "\n${YEL}Confirmação incorreta. Operação cancelada.${NC}\n"
    exit 1
fi

# ────────────────────────────────────────────────────────────
# Remoção
# ────────────────────────────────────────────────────────────
echo ""
REMOVED=0
ERRORS=0

for d in "$DIR_RAW" "$DIR_NORM" "$DIR_PUB" "$DIR_BUILD"; do
    if [[ -d "$d" ]]; then
        echo -e "  ${DIM}Removendo $d ...${NC}"
        if rm -rf "$d"; then
            echo -e "  ${GRN}✓${NC}  Removido: $d"
            REMOVED=$((REMOVED + 1))
        else
            echo -e "  ${RED}✗${NC}  Falhou ao remover: $d" >&2
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo -e "  ${DIM}~  Não existe (ignorando): $d${NC}"
    fi
done

echo ""
if [[ $ERRORS -eq 0 ]]; then
    echo -e "${BOLD}${GRN}Snapshot $DATE removido com sucesso.${NC}"
    echo -e "${DIM}Snapshots restantes: $(ls -d "$DATA_DIR/published"/[0-9][0-9][0-9][0-9]-* 2>/dev/null | xargs -I{} basename {} | sort | tr '\n' ' ')${NC}"
else
    echo -e "${BOLD}${RED}Remoção concluída com $ERRORS erro(s). Verifique as mensagens acima.${NC}" >&2
    exit 1
fi

echo ""
