#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
#
# Verificação de ponta a ponta: testa pela URL pública (Cloudflare → nginx de borda → frontend → API/MCP) os três alvos, cada um
# com o seu critério, e alerta por Telegram quando um falha VIGIA_EXTERNO_FALHAS vezes seguidas. Só alerta, nunca reinicia: a falha pode
# ser da Cloudflare, da rede ou do host inteiro. Por isso roda em OUTRA máquina; no próprio servidor ele não avisaria se o host caísse.
#
#   frontend  GET  /       200 e o HTML da aplicação (<div id="root">): o nginx do frontend serve a página, não só o proxy
#   api       GET  /health 200 e "status":"ok" no JSON
#   mcp       POST /mcp    `initialize` do JSON-RPC, 200 e "serverInfo" na resposta; a sessão aberta é fechada em seguida (DELETE).
#                          Sem chave de MCP: atende como anônimo, não chama tool, não gasta cota nem toca em dado.
#
#   bash scripts/vigia-externo.sh [URL_BASE]       (padrão: VIGIA_EXTERNO_SITE ou SITE_URL do ambiente ou do .env)
#   */5 * * * *  cd /caminho/do/clone && bash scripts/vigia-externo.sh https://arandurape.example >> logs/vigia-externo.log 2>&1
#
# A máquina precisa de um clone (ou deste script e do alerta-telegram.sh) e de TELEGRAM_BOT_KEY e TELEGRAM_CHAT_ID no ambiente ou no .env.
# Variáveis: VIGIA_EXTERNO_ALVOS ("frontend api mcp"), VIGIA_EXTERNO_MCP_URL (padrão URL_BASE/mcp), VIGIA_EXTERNO_FALHAS (2),
# VIGIA_EXTERNO_TIMEOUT_S (20), VIGIA_EXTERNO_ESTADO (/var/tmp/arandurape-vigia-externo), ALERTA_ORIGEM ("externo"),
# VIGIA_ALERTA_CMD (padrão scripts/alerta-telegram.sh; "" desliga).
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALVOS="${VIGIA_EXTERNO_ALVOS:-frontend api mcp}"
FALHAS_MAX="${VIGIA_EXTERNO_FALHAS:-2}"
TIMEOUT="${VIGIA_EXTERNO_TIMEOUT_S:-20}"
ESTADO="${VIGIA_EXTERNO_ESTADO:-/var/tmp/arandurape-vigia-externo}"
ALERTA_CMD="${VIGIA_ALERTA_CMD-bash $DIR/scripts/alerta-telegram.sh}"
export ALERTA_ORIGEM="${ALERTA_ORIGEM:-externo}"

BASE="${1:-${VIGIA_EXTERNO_SITE:-${SITE_URL:-$(grep -E '^SITE_URL=' "$DIR/.env" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d "\"'")}}}"
BASE="${BASE%/}"
[[ -n "$BASE" ]] || { echo "vigia-externo: sem URL base (argumento, VIGIA_EXTERNO_SITE ou SITE_URL)" >&2; exit 2; }
MCP_URL="${VIGIA_EXTERNO_MCP_URL:-$BASE/mcp}"
mkdir -p "$ESTADO"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Cada teste deixa em $url o que testou e em $motivo o porquê da falha; devolve 0 se o alvo está bem.
http() {   # http <saída do corpo> <args do curl...>: código HTTP (000 = sem resposta)
    local corpo="$1"; shift
    curl -sS -o "$corpo" -D "$tmp/cab" -m "$TIMEOUT" -w '%{http_code}' "$@" 2>/dev/null || true
}
sem_resposta() { [[ "$1" == "000" || -z "$1" ]] && motivo="sem resposta em ${TIMEOUT}s" || motivo="HTTP $1"; }

testa_frontend() {
    url="$BASE/"
    local c; c=$(http "$tmp/corpo" "$url")
    [[ "$c" == 200 ]] || { sem_resposta "$c"; return 1; }
    grep -q '<div id="root">' "$tmp/corpo" || { motivo="200, mas sem o HTML da aplicação"; return 1; }
}

testa_api() {
    url="$BASE/health"
    local c; c=$(http "$tmp/corpo" "$url")
    [[ "$c" == 200 ]] || { sem_resposta "$c"; return 1; }
    grep -q '"status" *: *"ok"' "$tmp/corpo" || { motivo="200, mas sem \"status\":\"ok\" ($(head -c 120 "$tmp/corpo"))"; return 1; }
}

testa_mcp() {
    url="$MCP_URL"
    local c sid
    c=$(http "$tmp/corpo" -X POST "$url" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"arandurape-vigia-externo","version":"1"}}}')
    sid=$(grep -i '^mcp-session-id:' "$tmp/cab" 2>/dev/null | head -1 | cut -d: -f2- | tr -d ' \r')
    # Fecha a sessão para não acumular sessões abertas no servidor a cada verificação.
    [[ -n "$sid" ]] && curl -sS -o /dev/null -m 10 -X DELETE "$url" -H "Mcp-Session-Id: $sid" 2>/dev/null
    [[ "$c" == 200 ]] || { sem_resposta "$c"; return 1; }
    grep -q '"serverInfo"' "$tmp/corpo" || { motivo="200, mas o initialize não trouxe serverInfo"; return 1; }
}

for alvo in $ALVOS; do
    case "$alvo" in frontend|api|mcp) ;; *) echo "vigia-externo: alvo desconhecido: $alvo" >&2; continue ;; esac
    url=""; motivo=""
    f="$ESTADO/$(printf '%s' "$alvo $BASE" | cksum | cut -d' ' -f1)"
    falhas=$(cat "$f" 2>/dev/null || echo 0)
    if "testa_$alvo"; then
        echo 0 > "$f"
        continue
    fi
    falhas=$((falhas + 1))
    echo "$falhas" > "$f"
    echo "vigia-externo: $alvo ($url): $motivo (falha $falhas seguida)"
    if [[ "$falhas" -ge "$FALHAS_MAX" && -n "$ALERTA_CMD" ]]; then
        echo "$alvo fora pela URL pública ($url): $motivo, $falhas verificações seguidas" | ALERTA_CHAVE="externo-$alvo-$BASE" sh -c "$ALERTA_CMD"
    fi
done
exit 0
