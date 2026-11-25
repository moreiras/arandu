# Cabeçalho de onde o nginx do frontend tira o IP real do cliente, e SÓ ele: este arquivo não declara em quem confiar.
#
# O X-Forwarded-For só vale vindo de um proxy seu. Quem confiar é declarado em NGINX_REAL_IP_FROM no .env (IPs ou prefixos da borda,
# separados por espaço ou vírgula, IPv6 e IPv4); o contêiner gera /tmp/real-ip-borda.inc com um `set_real_ip_from` por entrada
# (docker/entrypoint-real-ip-borda.sh) e o nginx-frontend.conf o inclui. Sem a variável nenhum `set_real_ip_from` é emitido: o nginx
# ignora o X-Forwarded-For de todos e vale o $remote_addr. Faixas inteiras do Docker (172.16/12, 192.168/16, fc00::/7) NÃO são mais
# confiadas por padrão: com Docker rootless ou userland-proxy a conexão do cliente chega pelo gateway da bridge, dentro dessas faixas, e
# quem chega de um IP confiável escolhe o próprio IP pelo cabeçalho (e, se cair no ALLOWED_IPS, vira "allowed": sem login nem orçamento).
#
# Alternativas, por NGINX_REAL_IP_INC (arquivo montado no lugar deste): nginx-real-ip-cloudflare.inc (borda Cloudflare, outro cabeçalho)
# e nginx-real-ip.exemplo-sem-borda.inc. Um arquivo alternativo pode trazer os próprios `set_real_ip_from`; os de NGINX_REAL_IP_FROM
# valem em conjunto com eles.
#
# Pré-requisito para IPv6 atrás de uma borda em Docker: daemon com "userland-proxy": false (sem isso o docker-proxy troca o IP de origem
# pelo gateway da bridge).
real_ip_header X-Forwarded-For;
real_ip_recursive on;
