#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
# Espelha o data/ desta instância em outra (um ambiente de teste que serve os mesmos dados sem coletar), por rsync sobre SSH, quando
# há snapshot publicado novo. O destino é sobrescrito: é um espelho, não uma cópia de segurança.
#
#   bash scripts/espelhar-dados.sh [--forcar] [--simular]
#
# Vai tudo menos raw/: a API ainda lê normalized/ e os raw/<data>/<ptt>/ixbr_members.json em tempo de execução (os PTTs em que o ASN é
# membro), então esses vão também; o resto do bruto (GBs) não. Os SQLite de data/auth/ estão em WAL e abertos pela API: vão por
# `sqlite3 .backup` (cópia consistente) e, no destino, os -wal/-shm antigos são apagados antes, senão o SQLite aplicaria o WAL do banco
# velho sobre o novo. O sal do log de uso (ops/usage/.salt-*) não vai: só o contêiner o lê e cada instância usa o seu. Os manifestos dos snapshots vão por último: a API só enxerga a data que tem manifest.json, então o destino nunca
# vê um snapshot pela metade.
#
# Sem snapshot novo desde a última cópia (ESPELHO_ESTADO), não faz nada: dá para agendar todo dia logo depois do pipeline, dentro do
# lock dele (flock), e a cópia sai no dia em que a data nova é publicada. --forcar copia mesmo assim (a primeira carga).
#
# .env: ESPELHO_DESTINO   destino do rsync, `usuario@host:` (com a chave restrita a `rrsync DIR_DATA` no destino, o caminho é relativo a ele)
#       ESPELHO_CHAVE     chave SSH (padrão ~/.ssh/id_ed25519_espelho)
#       ESPELHO_BWLIMIT   teto de banda em KiB/s (padrão 20000): o enlace é o mesmo que serve o site
# Saída: 0 = copiado ou nada a copiar; 1 = falha (o estado não avança e a próxima execução tenta de novo); 2 = uso.
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

FORCAR=0
SIMULAR=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --forcar) FORCAR=1; shift ;;
        --simular) SIMULAR=1; shift ;;
        -h|--help) sed -n '7,24p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *) echo "argumento desconhecido: $1" >&2; exit 2 ;;
    esac
done

_env() { [[ -f .env ]] && grep -E "^$1=" .env | tail -1 | cut -d= -f2- | sed -E 's/^"(.*)"$/\1/' ; }
DESTINO="${ESPELHO_DESTINO:-$(_env ESPELHO_DESTINO)}"
CHAVE="${ESPELHO_CHAVE:-$(_env ESPELHO_CHAVE)}"
CHAVE="${CHAVE:-$HOME/.ssh/id_ed25519_espelho}"
BWLIMIT="${ESPELHO_BWLIMIT:-$(_env ESPELHO_BWLIMIT)}"
BWLIMIT="${BWLIMIT:-20000}"
DADOS="${DATA_DIR_HOST:-$REPO_DIR/data}"
ESTADO="${ESPELHO_ESTADO:-$DADOS/ops/espelho_ultimo.txt}"

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [espelho] $*"; }
[[ -n "$DESTINO" ]] || { log "ESPELHO_DESTINO vazio: nada a fazer"; exit 2; }

ULTIMA=$(ls -1 "$DADOS/published" 2>/dev/null | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | while read -r d; do
    [[ -f "$DADOS/published/$d/manifest.json" ]] && echo "$d"; done | tail -1)
# Sem snapshot publicado a origem está vazia ou montada errado: com --delete isso apagaria o destino.
[[ -n "$ULTIMA" ]] || { log "nenhum snapshot publicado em $DADOS/published: abortado"; exit 1; }
if [[ $FORCAR -eq 0 && -f "$ESTADO" && "$(cat "$ESTADO")" == "$ULTIMA" ]]; then
    log "nada novo (último espelhado: $ULTIMA)"
    exit 0
fi

SSH="ssh -i $CHAVE -o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=accept-new"
[[ "$DESTINO" == *:* ]] || SSH=""                     # destino local (testes): sem SSH
if [[ "$DESTINO" == *: ]]; then DEST_AUTH="${DESTINO}auth/"; else DEST_AUTH="${DESTINO%/}/auth/"; fi   # `host:` é a raiz do rrsync
RSYNC=(rsync -rlpt --bwlimit="$BWLIMIT" --partial --stats)
[[ -n "$SSH" ]] && RSYNC+=(-e "$SSH")
[[ $SIMULAR -eq 1 ]] && RSYNC+=(--dry-run)

PREPARO=$(mktemp -d "${TMPDIR:-/tmp}/espelho.XXXXXX")
trap 'rm -rf "$PREPARO"' EXIT
mkdir -p "$PREPARO/auth"

# 1) data/auth/ num diretório de preparo: SQLite por backup consistente; o resto como está; -wal/-shm nunca.
for f in "$DADOS"/auth/*; do
    [[ -f "$f" ]] || continue
    nome=$(basename "$f")
    case "$nome" in
        *-wal|*-shm|*-journal) continue ;;
        *.db) python3 - "$f" "$PREPARO/auth/$nome" <<'PY' || { log "backup de $nome falhou"; exit 1; }
import sqlite3, sys
origem = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True, timeout=30)
destino = sqlite3.connect(sys.argv[2])
origem.backup(destino)
destino.execute("PRAGMA journal_mode=DELETE")       # um arquivo só, sem -wal ao lado
destino.close(); origem.close()
PY
              ;;
        *) cp -p "$f" "$PREPARO/auth/$nome" ;;
    esac
done
chmod -R u+rwX,g+rwX,o-rwx "$PREPARO/auth"       # contas e chaves: nada para outros usuários do host de destino

log "espelhando até $ULTIMA para $DESTINO (teto ${BWLIMIT} KiB/s)"
# 2) tudo menos raw/ (salvo ixbr_members.json), auth/ (vem do preparo) e os manifestos (vão por último). --delete: espelho; o que é
#    excluído aqui não é apagado no destino. --max-delete limita o estrago de uma origem errada.
"${RSYNC[@]}" --delete --max-delete=5000 --prune-empty-dirs \
    --exclude='/auth/' --exclude='/published/*/manifest.json' \
    --include='/raw/' --include='/raw/*/' --include='/raw/*/*/' --include='/raw/*/*/ixbr_members.json' --exclude='/raw/**' \
    --exclude='*.tmp' --exclude='.salt-*' \
    "$DADOS/" "$DESTINO" || { log "rsync dos dados falhou"; exit 1; }
# 3) auth/: --delete-before tira os -wal/-shm do banco antigo antes de o novo entrar.
"${RSYNC[@]}" --delete-before "$PREPARO/auth/" "$DEST_AUTH" || { log "rsync de auth/ falhou"; exit 1; }
# 4) os manifestos: daqui em diante o destino enxerga as datas novas.
"${RSYNC[@]}" --include='/published/' --include='/published/*/' --include='/published/*/manifest.json' --exclude='*' \
    "$DADOS/" "$DESTINO" || { log "rsync dos manifestos falhou"; exit 1; }

if [[ $SIMULAR -eq 0 ]]; then
    echo "$ULTIMA" > "$ESTADO.tmp" && mv "$ESTADO.tmp" "$ESTADO"
fi
log "concluído ($ULTIMA)"
