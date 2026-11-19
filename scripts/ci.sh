#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
# CI local = CI do GitHub Actions: o mesmo conjunto, nas versões de produção.
#
#   bash scripts/ci.sh            # usa $PYTHON (padrão: python3 do PATH; com requirements-dev.lock instalado)
#   bash scripts/ci.sh --docker   # roda tudo num container da MESMA imagem-base do Dockerfile.api,
#                                 # instalando requirements-dev.lock do zero, com --require-hashes
#   bash scripts/ci.sh --quick    # sem a suíte lenta (fuzz T4): para o laço de desenvolvimento
#
# Etapas: regras de camada (import-linter) → sintaxe dos scripts → pytest (T0–T5: unit, sources, products, contracts, política de acesso).
# Falha na primeira etapa que falhar. Tempo-alvo do job `python` no CI: < 5 min.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

MODE="local"; QUICK=0
for a in "$@"; do
    case "$a" in
        --docker) MODE="docker" ;;
        --quick) QUICK=1 ;;
        *) echo "uso: $0 [--docker] [--quick]" >&2; exit 2 ;;
    esac
done

if [[ "$MODE" == "docker" ]]; then
    IMAGE=$(sed -n 's/^FROM \(python:[^ ]*\).*/\1/p' Dockerfile.api | head -1)
    [[ -n "$IMAGE" ]] || { echo "ERRO: imagem-base não encontrada no Dockerfile.api" >&2; exit 1; }
    echo "== CI em container: $IMAGE"
    exec docker run --rm -v "$PWD:/app" -w /app -e PYTHONDONTWRITEBYTECODE=1 "$IMAGE" bash -c \
        "pip install --quiet --no-cache-dir --require-hashes -r requirements-dev.lock && bash scripts/ci.sh $([[ $QUICK -eq 1 ]] && echo --quick)"
fi

PY="${PYTHON:-python3}"
T0=$(date +%s)
step() { local n="$1"; shift; echo "== $n"; "$@" || { echo "FALHOU: $n" >&2; exit 1; }; }

step "regras de camada (import-linter)" "$PY" -c "from importlinter.cli import lint_imports_command; lint_imports_command()"
step "sintaxe dos scripts" bash -c 'for f in restart-safe.sh delete-snapshot.sh scripts/*.sh; do bash -n "$f" || exit 1; done'
"$PY" - <<'PY'
import fastapi, pydantic, starlette
print(f"== versões: fastapi {fastapi.__version__} · starlette {starlette.__version__} · pydantic {pydantic.__version__}")
PY
# Vulnerabilidades conhecidas em tudo o que o lock instala (transitivas inclusive). Consulta a rede (PyPI/OSV): sem rede,
# ARANDU_PIP_AUDIT=0. Na integração contínua (CI=true) faltar o pip-audit reprova: a etapa não pode sumir em silêncio.
if [[ "${ARANDU_PIP_AUDIT:-1}" == "0" ]]; then
    echo "== dependências (pip-audit): pulada (ARANDU_PIP_AUDIT=0)"
elif "$PY" -c "import pip_audit" 2>/dev/null; then
    step "dependências (pip-audit)" "$PY" -m pip_audit -r requirements-dev.lock --require-hashes --disable-pip --progress-spinner off
elif [[ "${CI:-}" == "true" ]]; then
    echo "FALHOU: dependências (pip-audit): pip-audit não instalado no CI (está no requirements-dev.lock)" >&2; exit 1
else
    echo "== dependências (pip-audit): pulada (pip-audit não instalado)"
fi
if [[ $QUICK -eq 1 ]]; then
    step "pytest (sem fuzz)" "$PY" -m pytest -q tests -p no:warnings --ignore=tests/products/test_t4_fuzz.py
else
    step "pytest (T0–T5)" "$PY" -m pytest -q tests -p no:warnings
fi
echo "== CI ok em $(( $(date +%s) - T0 )) s"
