#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
#
# Vigia de saúde (instalado pelo scripts/instalar.sh). O Docker fora do Swarm só MARCA um contêiner como `unhealthy`; não o reinicia.
# Este script roda no host a cada minuto (docker/systemd/arandurape-vigia.timer) e reinicia o serviço que ficou `unhealthy` em
# VIGIA_FALHAS rodadas seguidas, com recuo: depois de um reinício, o próximo só depois de VIGIA_RECUO_S, que dobra a cada reinício até
# VIGIA_RECUO_MAX_S e volta ao inicial depois de uma hora saudável. Reiniciar em laço durante um ataque pioraria tudo (cada subida da API
# aquece por até 2 min e perde o cache em memória): o recuo impede isso. Não age durante um deploy (trava do restart-safe.sh) nem antes de
# o contêiner terminar o `start_period` (estado `starting`).
#
# - Host sob pressão: com a pressão de E/S ou de memória do kernel (PSI, `full avg60`) acima de VIGIA_PRESSAO_MAX, o vigia alerta e
#   NÃO reinicia: com o disco saturado, API e MCP ficam unhealthy, e reiniciar faz a API perder o cache e aquecer de novo disputando o
#   mesmo disco.
# - API reiniciada leva o frontend junto: o nginx resolve o nome `api` na subida e, se o IP mudar, o site dá 502 com o frontend "healthy".
#   O frontend não é reiniciado sozinho enquanto a API não está healthy (o healthcheck dele passa pela API).
# - Serviço sem contêiner rodando gera alerta (não sobe nada: pode ser intervenção manual).
# - Alertas por Telegram por padrão (scripts/alerta-telegram.sh, se TELEGRAM_BOT_KEY e TELEGRAM_CHAT_ID estiverem configurados); só falhas.
#
# Uso: bash scripts/vigia-saude.sh [--dry-run]     (no diretório do projeto ou com VIGIA_DIR)
# Variáveis: VIGIA_SERVICOS ("api mcp frontend"), VIGIA_FALHAS (3), VIGIA_RECUO_S (300), VIGIA_RECUO_MAX_S (3600),
#            VIGIA_ESTADO (/var/tmp/arandurape-vigia), VIGIA_PRESSAO_MAX (40, % de `full avg60`), VIGIA_PSI_DIR (/proc/pressure),
#            VIGIA_ALERTA_CMD (padrão: scripts/alerta-telegram.sh; recebe a mensagem no stdin e a chave em ALERTA_CHAVE; "" desliga).
set -uo pipefail
DIR="${VIGIA_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
SERVICOS="${VIGIA_SERVICOS:-api mcp frontend}"
FALHAS="${VIGIA_FALHAS:-3}"
RECUO0="${VIGIA_RECUO_S:-300}"
RECUO_MAX="${VIGIA_RECUO_MAX_S:-3600}"
ESTADO="${VIGIA_ESTADO:-/var/tmp/arandurape-vigia}"
PRESSAO_MAX="${VIGIA_PRESSAO_MAX:-40}"
PSI="${VIGIA_PSI_DIR:-/proc/pressure}"
ALERTA_CMD="${VIGIA_ALERTA_CMD-bash $DIR/scripts/alerta-telegram.sh}"
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
mkdir -p "$ESTADO"
cd "$DIR" || exit 1
agora=$(date +%s)

log() { echo "vigia-saude: $*"; command -v logger >/dev/null && logger -t arandurape-vigia -- "$*"; true; }
alerta() {   # alerta <chave> <mensagem>
  log "$2"
  if [ -n "$ALERTA_CMD" ] && [ "$DRY" -eq 0 ]; then echo "$2" | ALERTA_CHAVE="vigia-$1" sh -c "$ALERTA_CMD" || log "falha no comando de alerta"; fi
}
reinicia() {
  docker compose restart "$1" >/dev/null 2>&1 || { alerta "falha-$1" "falha ao reiniciar $1"; return 1; }
}

# Pressão do host: maior `full avg60` entre E/S e memória (inteiro; 0 se o kernel não expõe PSI).
pressao=0; pressao_txt=""
for r in io memory; do
  v=$(awk '/^full/{for(i=1;i<=NF;i++) if($i ~ /^avg60=/){sub("avg60=","",$i); printf "%d", $i}}' "$PSI/$r" 2>/dev/null)
  [ -n "$v" ] || continue
  pressao_txt="$pressao_txt $r=${v}%"
  [ "$v" -gt "$pressao" ] && pressao=$v
done

trava="$DIR/.restart-safe.lock"
# /proc em vez de `kill -0`: o deploy roda como root e o vigia, como usuário comum, levaria EPERM e acharia a trava velha.
if [ -e "$trava" ] && [ -d "/proc/$(cat "$trava" 2>/dev/null || echo x)" ]; then
  log "deploy em andamento (restart-safe.sh): nada a fazer"; exit 0
fi

saude_api=""
for s in $SERVICOS; do
  cid=$(docker compose ps -q "$s" 2>/dev/null | head -1)
  if [ -z "$cid" ]; then
    alerta "ausente-$s" "$s sem contêiner rodando (o vigia não sobe serviço parado; veja 'docker compose ps -a $s')"
    continue
  fi
  saude=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}sem_healthcheck{{end}}' "$cid" 2>/dev/null || echo erro)
  [ "$s" = api ] && saude_api="$saude"
  f="$ESTADO/$s"
  falhas=0; recuo="$RECUO0"; proximo=0; saudavel_desde=0
  # shellcheck disable=SC1090
  [ -f "$f" ] && . "$f"
  case "$saude" in
    healthy)
      falhas=0
      [ "$saudavel_desde" -eq 0 ] && saudavel_desde=$agora
      if [ $((agora - saudavel_desde)) -ge 3600 ]; then recuo="$RECUO0"; fi
      ;;
    unhealthy)
      falhas=$((falhas + 1)); saudavel_desde=0
      if [ "$falhas" -ge "$FALHAS" ]; then
        if [ "$pressao" -gt "$PRESSAO_MAX" ]; then
          # Não zera as falhas: quando a pressão baixar e ele seguir unhealthy, reinicia na rodada seguinte.
          alerta "pressao-$s" "$s unhealthy há $falhas rodadas, mas o host está sob pressão (full avg60:$pressao_txt; limite $PRESSAO_MAX%): não reiniciei, reiniciar agora pioraria"
        elif [ "$s" = frontend ] && [ -n "$saude_api" ] && [ "$saude_api" != healthy ]; then
          log "frontend unhealthy, mas a API está $saude_api: o problema é da API, o frontend fica"
        elif [ "$agora" -lt "$proximo" ]; then
          alerta "recuo-$s" "$s unhealthy há $falhas rodadas; reinício adiado por recuo até $(date -d "@$proximo" +%H:%M:%S 2>/dev/null || echo "$proximo")"
        elif [ "$DRY" -eq 1 ]; then
          log "[dry-run] reiniciaria $s (unhealthy há $falhas rodadas)"
        else
          alerta "reinicio-$s" "reiniciando $s: unhealthy há $falhas rodadas (próximo reinício permitido em $recuo s)"
          reinicia "$s"
          # O nginx resolve `api` só na subida: frontend vai junto.
          if [ "$s" = api ] && echo " $SERVICOS " | grep -q " frontend "; then reinicia frontend; fi
          proximo=$((agora + recuo)); recuo=$((recuo * 2)); [ "$recuo" -gt "$RECUO_MAX" ] && recuo="$RECUO_MAX"; falhas=0
        fi
      fi
      ;;
    *) ;;   # starting, sem_healthcheck ou erro de leitura: não age
  esac
  printf 'falhas=%s\nrecuo=%s\nproximo=%s\nsaudavel_desde=%s\n' "$falhas" "$recuo" "$proximo" "$saudavel_desde" > "$f"
done
