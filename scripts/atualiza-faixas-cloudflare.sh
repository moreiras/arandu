#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
#
# Regera docker/nginx-real-ip-cloudflare.inc a partir das faixas publicadas pela Cloudflare (https://www.cloudflare.com/ips/).
# Uso (com o site atrás da Cloudflare):
#   bash scripts/atualiza-faixas-cloudflare.sh            # regrava o arquivo; confira o diff antes do commit
#   NGINX_REAL_IP_INC=./docker/nginx-real-ip-cloudflare.inc no .env, e recrie o frontend
# O mesmo conjunto de faixas serve para o firewall da origem (aceitar 80/443 só delas). Falha com código 1 se a lista vier vazia.
set -euo pipefail
cd "$(dirname "$0")/.."
SAIDA=docker/nginx-real-ip-cloudflare.inc
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
{
  echo "# IP real do cliente atrás da Cloudflare: só conexões vindas das faixas dela podem dizer o IP do cliente (CF-Connecting-IP)."
  echo "# Gerado por scripts/atualiza-faixas-cloudflare.sh em $(date -u +%Y-%m-%d) a partir de https://www.cloudflare.com/ips-v4 e /ips-v6."
  echo "# Sem isto todo cliente apareceria com um IP da Cloudflare e os limites por IP barrariam todos juntos; com faixas a mais, quem"
  echo "# chegasse delas escolheria o próprio IP. Não edite à mão: regenere."
  n=0
  for u in https://www.cloudflare.com/ips-v4 https://www.cloudflare.com/ips-v6; do
    while IFS= read -r l || [ -n "$l" ]; do
      l=$(echo "$l" | tr -d '[:space:]')
      [ -z "$l" ] && continue
      [[ "$l" =~ ^[0-9a-fA-F.:]+/[0-9]+$ ]] || { echo "linha inesperada em $u: $l" >&2; exit 1; }
      echo "set_real_ip_from $l;"
      n=$((n + 1))
    done < <(curl -fsS --max-time 20 -A "arandurape-faixas-cloudflare" "$u")
  done
  echo "real_ip_header CF-Connecting-IP;"
  [ "$n" -gt 0 ] || { echo "nenhuma faixa obtida" >&2; exit 1; }
} > "$tmp"
mv "$tmp" "$SAIDA"
trap - EXIT
echo "gravado $SAIDA ($(grep -c set_real_ip_from "$SAIDA") faixas)"
