# Proxy + cache em disco das respostas da API — compartilhado entre `location /api/`
# (caminho normal, atrás do auth_request) e `@api_open` (fallback fail-open quando o
# /auth/gate está indisponível). Incluído em docker/nginx-frontend.conf.
#
# `proxy_pass` sem URI de propósito: não é permitido com URI em location nomeada, e
# sem URI o caminho original (/api/...) é repassado intacto — o mesmo resultado
# de `proxy_pass http://api:8000/api/;` dentro de `location /api/`.
proxy_pass         http://api:8000;
proxy_http_version 1.1;
proxy_set_header   Host $host;
proxy_set_header   X-Real-IP $remote_addr;
proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;

# Timeouts explícitos (default nginx = 60 s, insuficiente para /map/query).
proxy_read_timeout      120s;
proxy_send_timeout      120s;

# Buffers para respostas grandes (índice de ASNs ~3 MB, GeoJSON do mapa).
# Sem configuração explícita o nginx usa 8×4k = 32 kB e derrama em disco.
proxy_buffer_size       16k;
proxy_buffers           8 32k;
proxy_busy_buffers_size 64k;

# Compressão: ver o map $api_ae em nginx-frontend.conf. Cliente com brotli → API entrega sem compressão e o
# nginx comprime ($api_ae vazio); os demais repassam o Accept-Encoding e usam o gzip da API.
proxy_set_header   Accept-Encoding $api_ae;
proxy_cache_key    $scheme$proxy_host$request_uri|$api_ae;
# A variante já está na chave ($api_ae, normalizada). Sem isto o `Vary: Accept-Encoding` da API faria o nginx guardar uma cópia por valor literal
# do cabeçalho do cliente ("gzip, br" ≠ "br"): a camada pré-comprimida em brotli-11 (api/precompressao.py) seria baixada da API de novo para cada uma.
proxy_ignore_headers Vary;

# Cache: o TTL vem do Cache-Control da própria API (latest=7d immutable,
# datas antigas=5min, sem-date=60s). proxy_cache_valid é só fallback.
proxy_cache            api_cache;
proxy_cache_valid      200 1m;
proxy_cache_valid      404 30s;
# Colapsa misses concorrentes (evita N gerações simultâneas do índice de 38 MB).
proxy_cache_lock       on;
# Após 30 s aguardando o lock, o nginx emite sua própria requisição em vez de
# deixar acumular todos os waiters de uma vez (thundering herd no cold start).
proxy_cache_lock_timeout 30s;
# Resiliência: serve resposta antiga se a API cair ou estiver atualizando.
proxy_cache_use_stale  error timeout updating http_500 http_502 http_503 http_504;
proxy_cache_background_update on;
include /etc/nginx/conf.d/security-headers.conf;
add_header X-Cache-Status $upstream_cache_status always;
