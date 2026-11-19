# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
#
# Alvo do laboratório IPv6 (T7): a imagem real da API (Dockerfile.api, passada em
# API_IMAGE) mais o nginx com os MESMOS arquivos de configuração do frontend
# (docker/nginx-*.conf/.inc) e o dataset sintético. Num contêiner só porque o
# Kathará trata cada dispositivo como um nó de rede; o nginx é o do Debian (com
# brotli) e não o alpine da imagem do frontend: o que se testa aqui é a
# configuração (listen [::], real_ip, auth_request, X-Real-IP), não o binário.
ARG API_IMAGE=arandurape-v6lab-api:local

# Estágio 1: dataset sintético (o publicador usa o pipeline dos testes e o
# MonkeyPatch do pytest, que fica só neste estágio).
FROM ${API_IMAGE} AS sintetico
RUN pip install --no-cache-dir pytest==9.1.1
COPY tests/ tests/
RUN python -m tests.synth.publish --out /data

FROM ${API_IMAGE}
USER root
RUN apt-get update -qq \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
      nginx libnginx-mod-http-brotli-filter libnginx-mod-http-brotli-static iproute2 curl \
 && rm -rf /var/lib/apt/lists/* /etc/nginx/sites-enabled/default \
 # O nginx.conf do Debian liga gzip no http{}; o da imagem oficial (a do frontend)
 # não, e o nginx-frontend.conf liga de novo: "gzip" duplicado impede a subida.
 && sed -i 's/^\(\s*\)gzip on;/\1# gzip on;/' /etc/nginx/nginx.conf \
 && mkdir -p /var/cache/nginx /usr/share/nginx/html \
 && echo ok > /usr/share/nginx/html/index.html
COPY docker/nginx-frontend.conf        /etc/nginx/conf.d/default.conf
COPY docker/nginx-security-headers.conf /etc/nginx/conf.d/security-headers.conf
COPY docker/nginx-api-proxy.inc         /etc/nginx/conf.d/api-proxy.inc
# No laboratório o nginx é a borda (instalação integrada): não confia em
# X-Forwarded-For de ninguém, como o exemplo "sem borda" do repositório.
COPY docker/nginx-real-ip.exemplo-sem-borda.inc /etc/nginx/conf.d/real-ip.inc
COPY --from=sintetico /data /data
# Kathará mantém o CMD da imagem como processo principal do dispositivo; como nas
# imagens kathara/*, um shell ocioso. Gate, API e nginx sobem pelo alvo.startup.
CMD ["/bin/bash"]
