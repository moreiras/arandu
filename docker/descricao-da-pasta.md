# docker/ — nginx do frontend, exemplos de borda e vigia

> Licença: AGPL-3.0-or-later — Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit

Arquivos usados na construção das imagens e na operação do host. `Dockerfile.api`, `Dockerfile.frontend` e os
`docker-compose*.yml` ficam na raiz.

## nginx do contêiner `frontend` (copiados pelo `Dockerfile.frontend`)

| Arquivo | Papel |
|---|---|
| `nginx-frontend.conf` | Servidor do frontend: SPA, proxy da API e do MCP, gate de acesso (`auth_request`), cache em disco das respostas da API, compressão brotli/gzip, limites por endpoint e metatags para robôs. |
| `nginx-api-proxy.inc` | Proxy e cache das respostas da API, comum ao caminho normal (atrás do `auth_request`) e ao fallback fail-open quando o gate está fora. |
| `nginx-security-headers.conf` | Cabeçalhos de segurança (CSP, HSTS, X-Frame-Options…), incluídos no `server` e em cada `location` que usa `add_header`. |
| `nginx-real-ip.inc` | Cabeçalho de onde o nginx tira o IP real (`X-Forwarded-For`); em quem confiar vem de `NGINX_REAL_IP_FROM` (nenhum IP por padrão). |
| `entrypoint-real-ip-borda.sh` | Roda na subida do contêiner do frontend e gera `/tmp/real-ip-borda.inc` (um `set_real_ip_from` por IP de `NGINX_REAL_IP_FROM`). |
| `nginx-real-ip-cloudflare.inc` | Variante para quando a borda é a Cloudflare (só as faixas dela informam o IP do cliente); regerada por `scripts/atualiza-faixas-cloudflare.sh`. |
| `nginx-real-ip.exemplo-sem-borda.inc` | Exemplo para frontend sem borda, acessado direto de uma LAN que cai nas faixas do Docker; copie para `nginx-real-ip.local.inc` (ignorado pelo git). |

## Exemplos e arquivos sem uso no compose atual

| Arquivo | Papel |
|---|---|
| `nginx-arandu.conf` | Exemplo de nginx de borda no host para o modo com proxy externo (`docker-compose.no-nginx.yml`): HTTPS, ACME, limite volumétrico por IP e proxy para o contêiner `arandurape-frontend`. Ajuste `server_name` e certificados. |
| `nginx.conf` | Proxy mínimo antigo (API e frontend); nenhuma imagem nem compose o usa. |
| `Dockerfile.frontend.dev` | Imagem do servidor de desenvolvimento do Vite; nenhum compose a usa (o README mostra o `docker run` equivalente). |

## Vigia de saúde (`systemd/`)

| Arquivo | Papel |
|---|---|
| `systemd/arandurape-vigia.service` | Roda `scripts/vigia-saude.sh`, que reinicia com recuo o serviço que o Docker marcou como `unhealthy`. |
| `systemd/arandurape-vigia.timer` | Dispara o vigia a cada minuto, 2 min depois do boot. Instalados por `scripts/instalar.sh`. |
| `systemd/user/arandurape-vigia.{service,timer}` | Os mesmos, para Docker rootless: vão para o systemd do usuário do serviço, com o `DOCKER_HOST` do socket dele. |

## Compose (na raiz)

| Arquivo | Uso |
|---|---|
| `docker-compose.exemplo.yml` | Exemplo versionado, copiado para `docker-compose.yml` (fora do git) e editado por instalação. Serviços `api`, `mcp` e `frontend`; avulsos `worker` (perfil `worker`, pipeline) e `rpki` (perfil `rpki`, Routinator antes do worker). |
| `docker-compose.no-nginx.yml` | Overlay para proxy reverso já existente no host: não publica a porta 80 e liga o frontend à rede do proxy (`WEB_NETWORK_NAME`). |
| `docker-compose.prod.yml` | Overlay para produção com infraestrutura externa. |
