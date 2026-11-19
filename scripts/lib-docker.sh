#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
# Modo do Docker (com root ou rootless) para os scripts de implantação. Para ser `source`ado.
#
#   docker_rootless        0 se o daemon que este usuário alcança roda sem root (rootless)
#   docker_host_atual      endereço do daemon deste usuário (DOCKER_HOST ou o do contexto ativo), para o cron e o systemd
#
# No rootless o daemon pertence ao usuário do serviço: sudo não o enxerga (o root procura /var/run/docker.sock), o UID de dentro do
# contêiner corresponde a outro UID no host (subuid) e o cron e o systemd não herdam o DOCKER_HOST da sessão.
# ARANDU_DOCKER_ROOTLESS=1|0 força a resposta (testes, ou um host onde `docker info` é lento).

docker_rootless() {
    case "${ARANDU_DOCKER_ROOTLESS:-}" in
        1) return 0 ;;
        0) return 1 ;;
    esac
    docker info --format '{{range .SecurityOptions}}{{.}} {{end}}' 2>/dev/null | grep -q 'name=rootless'
}

docker_host_atual() {
    if [[ -n "${DOCKER_HOST:-}" ]]; then
        echo "$DOCKER_HOST"
    else
        docker context inspect --format '{{.Endpoints.docker.Host}}' 2>/dev/null
    fi
}
