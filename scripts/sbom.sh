#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
#
# SBOM (CycloneDX) do que o Arandurapé instala e verificação contra as bases de vulnerabilidades conhecidas (Grype). O mesmo
# script roda na integração contínua (job `sbom`) e na máquina de quem desenvolve; só precisa de Docker.
#
#   bash scripts/sbom.sh                     # dependências: Python de produção, frontend (produção e dev), componentes compilados
#   bash scripts/sbom.sh --imagens           # também as imagens já construídas (IMG_API, IMG_FRONTEND; padrão: as do compose)
#   bash scripts/sbom.sh --saida DIR         # onde gravar (padrão: sbom/, fora do git)
#
# Política: sai com código 1 se houver vulnerabilidade alta ou crítica, COM correção publicada, em algo que vai para produção
# (dependências Python de produção, frontend de produção, componentes compilados, imagens). O ferramental de desenvolvimento entra no
# relatório sem reprovar. Exceção (componente afetado no papel, mas não na prática) vai para config/vex.openvex.json com a
# justificativa; nunca desligue a verificação para passar.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

GRYPE="anchore/grype:v0.122.1@sha256:661583704a253c0448ed63998b5ea2cd9d5a76ee71eedc4aed439b8ce3e93a1c"
SYFT="anchore/syft:v1.57.2@sha256:e97e20b6e6d1699c60296b66ab337941724f9bd06ac279d893eda89601fc4b2a"
CYCLONEDX_BOM=9.0.0
VEX=config/vex.openvex.json

IMAGENS=0; SAIDA=sbom
while [[ $# -gt 0 ]]; do
    case "$1" in
        --imagens) IMAGENS=1 ;;
        --saida) SAIDA="${2:?--saida pede um diretório}"; shift ;;
        *) echo "uso: $0 [--imagens] [--saida DIR]" >&2; exit 2 ;;
    esac
    shift
done
mkdir -p "$SAIDA"; SAIDA="$(cd "$SAIDA" && pwd)"
VERSAO="$(cat VERSION)"
PY_IMG=$(sed -n 's/^FROM \(python:[^ ]*\).*/\1/p' Dockerfile.api | head -1)
NODE_IMG=$(sed -n 's/^FROM \(node:[^ ]*\).*/\1/p' Dockerfile.frontend | head -1)
NGINX_VERSION=$(sed -n 's/^ARG NGINX_VERSION=\(.*\)/\1/p' Dockerfile.frontend | head -1)
NGX_BROTLI_COMMIT=$(sed -n 's/^ARG NGX_BROTLI_COMMIT=\(.*\)/\1/p' Dockerfile.frontend | head -1)
[[ -n "$PY_IMG" && -n "$NODE_IMG" && -n "$NGINX_VERSION" && -n "$NGX_BROTLI_COMMIT" ]] \
    || { echo "ERRO: imagem ou versão não encontrada nos Dockerfiles" >&2; exit 1; }
falha() { echo "FALHOU: $*" >&2; exit 1; }

echo "== SBOM Python (requirements.lock, ambiente de produção)"
docker run --rm -v "$PWD:/app:ro" -v "$SAIDA:/out" -w /app -e PIP_DISABLE_PIP_VERSION_CHECK=1 -e PIP_ROOT_USER_ACTION=ignore \
    -e VERSAO="$VERSAO" -e NGINX_VERSION="$NGINX_VERSION" -e NGX_BROTLI_COMMIT="$NGX_BROTLI_COMMIT" "$PY_IMG" sh -c '
  set -e
  pip install --quiet --no-cache-dir cyclonedx-bom=='"$CYCLONEDX_BOM"'
  python -m venv --without-pip /tmp/prod
  pip --python /tmp/prod/bin/python install --quiet --no-cache-dir --require-hashes --no-deps -r requirements.lock
  cyclonedx-py environment --mc-type application --of JSON --output-reproducible -o /out/sbom-python.cdx.json /tmp/prod/bin/python
  # Componentes compilados no build do frontend: nenhum scanner os acha na imagem (o nginx vem do repositório do nginx.org; os
  # módulos brotli, do código-fonte). Entram à mão, com as versões tiradas do Dockerfile.frontend.
  python - <<PY
import json, os
v, c = os.environ["NGINX_VERSION"], os.environ["NGX_BROTLI_COMMIT"]
doc = {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
       "metadata": {"component": {"type": "application", "name": "arandurape-frontend", "version": os.environ["VERSAO"]}},
       "components": [
           {"type": "application", "name": "nginx", "version": v, "purl": f"pkg:generic/nginx@{v}",
            "cpe": f"cpe:2.3:a:f5:nginx:{v}:*:*:*:*:*:*:*",
            "description": "binário do repositório de pacotes do nginx.org (Dockerfile.frontend)"},
           {"type": "library", "name": "ngx_brotli", "version": c, "purl": f"pkg:github/google/ngx_brotli@{c}",
            "description": "módulos dinâmicos compilados no build, com o submódulo brotli"}]}
json.dump(doc, open("/out/sbom-compilados.cdx.json", "w"), indent=1, ensure_ascii=False)
PY
' || falha "SBOM Python"

echo "== SBOM frontend (package-lock.json)"
# O npm sbom exige `version` no package.json; a fonte única é VERSION, então a versão só entra numa cópia.
docker run --rm -v "$PWD/frontend:/fe:ro" -v "$SAIDA:/out" -e VERSAO="$VERSAO" "$NODE_IMG" sh -c '
  set -e
  mkdir /tmp/fe && cp /fe/package.json /fe/package-lock.json /tmp/fe/ && cd /tmp/fe
  npm pkg set version="$VERSAO"
  npm sbom --package-lock-only --omit dev --sbom-format cyclonedx > /out/sbom-frontend.cdx.json
  npm sbom --package-lock-only --sbom-format cyclonedx > /out/sbom-frontend-dev.cdx.json
' || falha "SBOM frontend"

PRODUCAO=(sbom-python sbom-compilados sbom-frontend)
if [[ $IMAGENS -eq 1 ]]; then
    for par in "api=${IMG_API:-arandurape-api:latest}" "frontend=${IMG_FRONTEND:-arandurape-frontend:latest}"; do
        nome="${par%%=*}"; img="${par#*=}"
        echo "== SBOM da imagem $img"
        docker image inspect "$img" >/dev/null 2>&1 || falha "imagem $img não encontrada (construa antes: docker compose build)"
        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$SAIDA:/out" "$SYFT" -q "docker:$img" \
            -o "cyclonedx-json=/out/sbom-imagem-$nome.cdx.json" || falha "SBOM da imagem $img"
        PRODUCAO+=("sbom-imagem-$nome")
    done
fi

# Base do Grype num volume, para não baixá-la a cada rodada local (na CI o volume nasce vazio).
GRYPE_RUN=(docker run --rm -v "$SAIDA:/sbom" -v "$PWD/$VEX:/vex.json:ro" -v arandurape-grype-db:/.cache -e GRYPE_DB_AUTO_UPDATE=true "$GRYPE")
reprovou=0
verificar() {   # nome, política (producao|dev)
    local nome="$1" politica="$2" args=(--only-fixed --vex /vex.json -o table -o "json=/sbom/vulns-$1.json")
    echo "== Grype: $nome ($politica)"
    [[ "$politica" == "producao" ]] && args+=(--fail-on high)
    "${GRYPE_RUN[@]}" "sbom:/sbom/$nome.cdx.json" "${args[@]}"
    case $? in   # 0 = ok; 2 = achou acima do limite (--fail-on); outro = o Grype não rodou
        0) ;;
        2) echo "REPROVADO: $nome tem vulnerabilidade alta ou crítica com correção" >&2; reprovou=1 ;;
        *) echo "ERRO: o Grype não conseguiu verificar $nome" >&2; reprovou=1 ;;
    esac
}
for n in "${PRODUCAO[@]}"; do verificar "$n" producao; done
verificar sbom-frontend-dev dev

echo "== SBOMs e relatórios em $SAIDA"
exit $reprovou
