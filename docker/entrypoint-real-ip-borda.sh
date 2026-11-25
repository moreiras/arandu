#!/bin/sh
# Gera /tmp/real-ip-borda.inc (incluído por nginx-frontend.conf) com um `set_real_ip_from` por entrada de NGINX_REAL_IP_FROM: lista de IPs ou
# prefixos da borda, separados por espaço ou vírgula, IPv6 e IPv4. Roda na subida do contêiner (/docker-entrypoint.d/ da imagem do nginx).
# Variável vazia ou ausente: arquivo sem diretivas, e o nginx não confia no X-Forwarded-For de ninguém. Valor mal formado: a subida falha.
set -eu
set -f
saida=${REAL_IP_BORDA_SAIDA:-/tmp/real-ip-borda.inc}
lista=$(printf '%s' "${NGINX_REAL_IP_FROM:-}" | tr ',' ' ')
n=0
{
  echo "# gerado na subida do contêiner a partir de NGINX_REAL_IP_FROM; não edite"
  for ip in $lista; do
    case "$ip" in
      *[!0-9A-Fa-f:./]*) echo "real-ip: valor inválido em NGINX_REAL_IP_FROM: '$ip' (use IPs ou prefixos IPv6/IPv4 separados por espaço ou vírgula)" >&2; exit 1 ;;
    esac
    echo "set_real_ip_from $ip;"
    n=$((n + 1))
  done
} > "$saida.tmp"
mv "$saida.tmp" "$saida"
if [ "$n" -eq 0 ]; then
  echo "real-ip: NGINX_REAL_IP_FROM vazio: o X-Forwarded-For é ignorado (vale o endereço da conexão)"
else
  echo "real-ip: confiando no X-Forwarded-For de $n endereço(s) declarado(s) em NGINX_REAL_IP_FROM"
fi
