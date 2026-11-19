#!/usr/bin/env bash
# E2E da política de acesso com Playwright (docker). Requer: docker; API real rodando
# em :8000 com ACCESS_POLICY_MODE=enforce ANON_SESSION_LIMIT_MINUTES=1
# ANON_HEARTBEAT_INTERVAL_SECONDS=2 ALLOWED_IPS=203.0.113.128/25 e DATA_DIR com snapshots
# **APP_BASE_URL=http://localhost** (com https o cookie anon_sid sai `Secure` e o Playwright
# `ctx.request`, que roda em http, não o envia: falsa falha em "API avançada = 403").
# Sobe o nginx do frontend em :18080.
# Opcional: `uvicorn api.gate_app:app --port 8001` com as mesmas variáveis (gate em
# processo próprio, como em produção); sem ele o nginx cai em fail-open e a API decide.
# O run.js esgota de propósito o orçamento anônimo, que fica em {DATA_DIR}/auth/anon_sessions.db: apague esse arquivo (e reinicie a API)
# antes de repetir a execução, senão o passo do chip de orçamento falha por estado antigo, não por bug.
# Uso: bash tests/e2e/run.sh [run.js|smoke.js|menu.js|inventario.js|operadoras.js|estaticos.js|explorar.js] [--update]    (menu.js = menu por tema; inventario.js = conteúdo das páginas; operadoras.js = paridade /scms /smps /stfcs /seacs; estaticos.js = sitemap/robots/llms/catálogo; explorar.js = coleções do explorador; console.js = erros de console por página — o nginx local não tem basemap, então IGNORAR_TILES=1 por padrão)
#      bash tests/e2e/run.sh [run.js|smoke.js] [--update]    (padrão: run.js — política de acesso;
#      smoke.js = fumaça das 8 páginas e orçamento de requisições/bytes, baseline em tests/contracts/page_budget.json)
set -u
cd "$(dirname "$0")/../.."
SCRIPT="${1:-run.js}"; shift 2>/dev/null || true
docker build -q -f Dockerfile.frontend -t arandu-fe-e2e . >/dev/null || exit 1
docker rm -f ng-e2e >/dev/null 2>&1
docker run -d --name ng-e2e --add-host api:host-gateway --add-host mcp:127.0.0.1 -p 18080:8080 arandu-fe-e2e >/dev/null
trap 'docker rm -f ng-e2e >/dev/null 2>&1' EXIT
sleep 2
docker run --rm --add-host host.docker.internal:host-gateway -v "$PWD/tests/e2e:/e2e" -v "$PWD/tests/contracts:/contracts" -v "$PWD/frontend/src/components/layout/menu.ts:/menu.ts:ro" -w /e2e \
  -e BASE_URL=http://host.docker.internal:18080 -e IGNORAR_TILES="${IGNORAR_TILES:-1}" \
  mcr.microsoft.com/playwright:v1.49.0-jammy \
  bash -c "npm init -y >/dev/null 2>&1 && npm i --silent playwright@1.49.0 >/dev/null 2>&1 && node $SCRIPT $*"
