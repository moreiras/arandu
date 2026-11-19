#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
#
# Alerta por Telegram: manda a mensagem lida da entrada padrão ao chat configurado. Só falhas passam por aqui (vigia de saúde,
# pipeline, verificação externa); quem chama decide o que é falha.
#
#   echo "mensagem" | bash scripts/alerta-telegram.sh [--chave K]
#
# Configuração: TELEGRAM_BOT_KEY e TELEGRAM_CHAT_ID no ambiente ou no .env da raiz do projeto (só essas duas linhas são lidas; o .env
# não é carregado inteiro). Sem elas o alerta vai só para o syslog e o script sai 0: alerta nunca derruba quem o chama.
# --chave (ou ALERTA_CHAVE): a mesma chave dentro de ALERTA_INTERVALO_S (padrão 1800) não reenvia, para um incidente longo não inundar o
# chat. Sem chave, a própria mensagem é a chave.
# ALERTA_ENV: outro arquivo no lugar do .env (os testes apontam para um inexistente). ALERTA_ORIGEM: rótulo da máquina no início da mensagem (padrão: hostname). ALERTA_ESTADO: diretório das marcas (/var/tmp/arandurape-alerta).
#
# O token nunca vai para a linha de comando (o curl o recebe pela entrada padrão, em -K -): a lista de processos do host é legível por
# todos. A mensagem passa pelos servidores do Telegram: não ponha nela IP de cliente, conta, e-mail nem dado pessoal.
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHAVE="${ALERTA_CHAVE:-}"
[[ "${1:-}" == "--chave" ]] && CHAVE="${2:-}"

msg="$(cat)"
[[ -z "$msg" ]] && exit 0

ENV_ARQ="${ALERTA_ENV:-$DIR/.env}"
do_env() {   # valor de uma chave no .env, sem aspas; o .env não é executado
    [[ -f "$ENV_ARQ" ]] || return 0
    grep -E "^$1=" "$ENV_ARQ" | tail -1 | cut -d= -f2- | sed -E 's/^["'\'']//; s/["'\'']\s*$//'
}
KEY="${TELEGRAM_BOT_KEY:-$(do_env TELEGRAM_BOT_KEY)}"
CHAT="${TELEGRAM_CHAT_ID:-$(do_env TELEGRAM_CHAT_ID)}"
ORIGEM="${ALERTA_ORIGEM:-$(hostname -s 2>/dev/null || hostname)}"
ESTADO="${ALERTA_ESTADO:-/var/tmp/arandurape-alerta}"
INTERVALO="${ALERTA_INTERVALO_S:-1800}"

syslog() { command -v logger >/dev/null && logger -t arandurape-alerta -- "$*"; true; }

mkdir -p "$ESTADO" 2>/dev/null
marca="$ESTADO/$(printf '%s' "${CHAVE:-$msg}" | cksum | cut -d' ' -f1)"
agora=$(date +%s)
if [[ -f "$marca" ]] && (( agora - $(cat "$marca" 2>/dev/null || echo 0) < INTERVALO )); then
    syslog "alerta repetido suprimido: ${msg:0:200}"
    exit 0
fi

texto="⚠ [$ORIGEM] $msg"
texto="${texto:0:4000}"   # limite do Telegram: 4096 caracteres
syslog "$texto"
if [[ -z "$KEY" || -z "$CHAT" ]]; then
    exit 0
fi
if printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$KEY" \
    | curl -sS -o /dev/null -m 15 --fail -K - --data-urlencode "chat_id=$CHAT" --data-urlencode "text=$texto" 2>/dev/null; then
    echo "$agora" > "$marca" 2>/dev/null
else
    syslog "falha ao enviar o alerta ao Telegram"
fi
exit 0
