# De quem o nginx do frontend aceita o X-Forwarded-For como IP real do cliente.
#
# Só faz sentido confiar no proxy que está na frente: atrás da borda externa (overlay no-nginx), a conexão chega de uma rede do Docker.
# Faixas da LAN NÃO entram: quem chega de um IP confiável escolhe o próprio IP pelo cabeçalho e, se cair no ALLOWED_IPS, vira "allowed"
# (sem login nem orçamento). Ficam só as faixas padrão de redes do Docker.
#
# Para restringir ao IP exato da borda, monte outro arquivo no lugar deste: NGINX_REAL_IP_INC=/caminho/real-ip.inc no .env.
# **Obrigatório quando os clientes chegam ao frontend direto de uma LAN em 172.16/12 ou 192.168/16** (sem borda na frente, por exemplo
# numa LAN em 172.18.x ou 172.19.x): com este padrão, qualquer cliente dessa LAN forja o próprio IP. Nesse caso o
# arquivo local confia só no gateway da rede do compose (o docker-proxy das conexões locais): ver docker/nginx-real-ip.exemplo-sem-borda.inc.
#
# Pré-requisito para IPv6: daemon Docker com "userland-proxy": false (sem isso o docker-proxy troca o IP de origem pelo gateway da bridge).
set_real_ip_from 172.16.0.0/12;    # pools padrão do Docker (172.17–172.31)
set_real_ip_from 192.168.0.0/16;   # pools padrão do Docker depois das 172.x
set_real_ip_from fc00::/7;         # ULA de redes Docker com IPv6
real_ip_header X-Forwarded-For;
real_ip_recursive on;
