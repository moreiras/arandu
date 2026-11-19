# Exemplo para frontend SEM borda na frente, acessado direto de uma LAN que cai nas faixas do Docker.
# Copie para docker/nginx-real-ip.local.inc (ignorado pelo git), troque o gateway pelo da rede do compose
# (`docker network inspect <projeto>_arandurape -f '{{range .IPAM.Config}}{{.Gateway}}{{end}}'`) e defina no .env:
#   NGINX_REAL_IP_INC=./docker/nginx-real-ip.local.inc
# Sem proxy na frente, o Docker preserva o IP de origem; só a conexão local que passa pelo docker-proxy chega pelo gateway.
set_real_ip_from 192.0.2.1;          # TROQUE pelo gateway da rede do compose (endereço de documentação, RFC 5737)
real_ip_header X-Forwarded-For;
real_ip_recursive on;
