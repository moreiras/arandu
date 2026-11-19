#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
# RPKI em modo avulso: atualiza o cache RPKI, valida e grava os VRPs e ASPAs em data/cache/rpki/vrps.json; o contêiner
# morre em seguida. Quem chama: scripts/arandu-weekly.sh (antes do worker, dentro do lock do pipeline).
# sources.rpki_collector lê o arquivo.
#
#   bash scripts/rpki-avulso.sh [--timeout S]
#
# --timeout (padrão RPKI_TIMEOUT_S ou 2700 s): o pipeline não espera mais que isso; estourado, o contêiner é removido, o arquivo
# anterior fica onde está e a etapa RPKI do dia falha (política opcional; o coletor recusa arquivo velho, RPKI_MAX_IDADE_H).
# Sem data/cache/rpki/vrps.json (instalação nova ou volume perdido) o cache está frio e a execução é longa (no ambiente de teste, 2 h 58 min
# com o disco disputado; em SSD bem menos): o padrão passa a RPKI_TIMEOUT_FRIO_S (14400 s). O que já foi baixado fica no volume
# rpki_cache, então uma execução interrompida não se perde toda.
#
# RPKI_DESTINO troca o diretório de saída (testes; o coletor lê RPKI_JSON).
# Saída: 0 = arquivo novo gravado; 1 = falha ou timeout (arquivo anterior preservado).
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

TIMEOUT_S=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --timeout) TIMEOUT_S="$2"; shift 2 ;;
        -h|--help) sed -n '7,20p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *) echo "argumento desconhecido: $1" >&2; exit 2 ;;
    esac
done

# Mesma escolha de arquivos compose do arandu-weekly.sh.
if grep -qE '^WEB_NETWORK_NAME=.+' "$REPO_DIR/.env" 2>/dev/null; then
    COMPOSE="docker compose -f docker-compose.yml -f docker-compose.no-nginx.yml"
else
    COMPOSE="docker compose -f docker-compose.yml"
fi
NOME="arandurape-rpki"
DESTINO="${RPKI_DESTINO:-$REPO_DIR/data/cache/rpki}"
log() { echo "[$(date -u +%FT%TZ)] [RPKI] $*"; }

mkdir -p "$DESTINO" || { log "ERRO: não consegui criar $DESTINO"; exit 1; }
if [[ -z "$TIMEOUT_S" ]]; then
    if [[ -f "$DESTINO/vrps.json" ]]; then TIMEOUT_S="${RPKI_TIMEOUT_S:-2700}"; else TIMEOUT_S="${RPKI_TIMEOUT_FRIO_S:-14400}"; log "sem vrps.json anterior: cache frio"; fi
fi
TMP="$DESTINO/vrps.json.tmp"
# Nome fixo: duas execuções ao mesmo tempo disputariam o cache. Uma de pé = recusa; uma parada = sobra de interrupção, remove.
if [[ -n "$(docker ps -q --filter "name=^/${NOME}$")" ]]; then
    log "ERRO: já há um Routinator avulso rodando ($NOME)"
    exit 1
fi
docker rm -f "$NOME" >/dev/null 2>&1 || true

log "Routinator avulso (timeout ${TIMEOUT_S}s)..."
t0=$SECONDS
# A saída vai por stdout para um arquivo do host: o contêiner roda como o usuário do Routinator e não grava em data/.
timeout --signal=TERM "$TIMEOUT_S" $COMPOSE --profile rpki run --rm --no-TTY --name "$NOME" rpki > "$TMP"
RC=$?
# Com timeout, o `compose run` morre mas o contêiner não: remove.
docker rm -f "$NOME" >/dev/null 2>&1 || true
DUR=$(( SECONDS - t0 ))

if [[ $RC -ne 0 ]]; then
    rm -f "$TMP"
    [[ $RC -eq 124 ]] && log "ERRO: timeout em ${DUR}s (o cache baixado até aqui fica no volume)" || log "ERRO: Routinator saiu com código $RC em ${DUR}s"
    exit 1
fi
if ! python3 - "$TMP" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
roas = d.get("roas") or []
if not roas:
    sys.exit("sem roas")
print(f"{len(roas)} ROAs, {len(d.get('aspas') or [])} ASPAs")
EOF
then
    rm -f "$TMP"
    log "ERRO: saída do Routinator inválida ou vazia (${DUR}s)"
    exit 1
fi
mv -f "$TMP" "$DESTINO/vrps.json"
log "ok em ${DUR}s: $DESTINO/vrps.json"
