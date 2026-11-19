#!/usr/bin/env bash
# Regressão do controle de acesso no nginx do frontend (auth_request antes do cache).
# Requer: docker, .venv-mcp (ou PYTHON=...). Sobe API stub em :$API_PORT (padrão 8000) e nginx em :18080.
# O gate roda em processo próprio (api/gate_app.py, :8001). Casos: MISS→HIT; esgotado recebe 403 MESMO com HIT; allowlist passa; /api/v1/docs
# isento; fail-open com a API fora (serve cache).
set -u
cd "$(dirname "$0")/../.."
PY=${PYTHON:-.venv-mcp/bin/python}
TMP=$(mktemp -d)
# A imagem do frontend (com os módulos brotli): o nginx oficial não os tem e a config usa `brotli on`.
# O build reaproveita as camadas em cache; para só testar o nginx use IMG=<tag já construída>.
IMG=${IMG:-arandurape-frontend-teste}
docker image inspect "$IMG" >/dev/null 2>&1 || docker build -q -f Dockerfile.frontend -t "$IMG" . >/dev/null || { echo "build da imagem falhou"; exit 1; }
fail=0
ok()   { echo "  ok   - $1"; }
nok()  { echo "  FAIL - $1 (obtido: $2)"; fail=1; }
# Portas do stub e do gate: o nginx as vê como api:8000/api:8001; se já estiverem ocupadas (API local de dev),
# use API_PORT/GATE_PORT: cópias da config com as portas trocadas são montadas no container.
API_PORT=${API_PORT:-8000}; GATE_PORT=${GATE_PORT:-8001}
API_PID=""; GATE_PID=""
# Mata só os processos que ESTE script criou (nunca por nome: pode haver outra API local rodando).
cleanup() { docker rm -f ng-gate >/dev/null 2>&1; [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null; [ -n "$GATE_PID" ] && kill "$GATE_PID" 2>/dev/null; rm -rf "$TMP"; }
trap cleanup EXIT

DATA_DIR=$TMP/data STUB_DATA_DIR=$TMP/data ALLOWED_IPS=203.0.113.128/25 ACCESS_POLICY_MODE=enforce \
  $PY -m uvicorn stub_api:app --app-dir tests/nginx --host 0.0.0.0 --port "$API_PORT" >"$TMP/api.log" 2>&1 &
API_PID=$!
# Gate em processo próprio (porta 8001), como no container da API em produção.
DATA_DIR=$TMP/data JWT_SECRET=$(printf 'x%.0s' {1..32}) GOOGLE_CLIENT_ID=a GOOGLE_CLIENT_SECRET=b \
  ALLOWED_IPS=203.0.113.128/25 ACCESS_POLICY_MODE=enforce APP_BASE_URL=https://teste.local \
  $PY -m uvicorn api.gate_app:app --host 0.0.0.0 --port "$GATE_PORT" --log-level warning >"$TMP/gate.log" 2>&1 &
GATE_PID=$!
mkdir -p "$TMP/conf"
for f in nginx-frontend.conf nginx-api-proxy.inc; do
  sed -e "s/api:8000/api:$API_PORT/g" -e "s/api:8001/api:$GATE_PORT/g" "docker/$f" > "$TMP/conf/$f"
done
docker run -d --name ng-gate --add-host api:host-gateway --add-host mcp:127.0.0.1 -p 18080:8080 \
  -v "$TMP/conf/nginx-frontend.conf:/etc/nginx/conf.d/default.conf:ro" \
  -v "$PWD/docker/nginx-security-headers.conf:/etc/nginx/conf.d/security-headers.conf:ro" \
  -v "$PWD/docker/nginx-real-ip.inc:/etc/nginx/conf.d/real-ip.inc:ro" \
  -v "$TMP/conf/nginx-api-proxy.inc:/etc/nginx/conf.d/api-proxy.inc:ro" "$IMG" >/dev/null
for _ in $(seq 1 30); do curl -sf localhost:$API_PORT/api/v1/ping >/dev/null && break; sleep 0.5; done

req() { # ip [sid] [path] -> "status cache"
  local a=(-s -o /dev/null -D - -H "X-Forwarded-For: $1"); [ -n "${2:-}" ] && a+=(-H "Cookie: anon_sid=$2")
  curl "${a[@]}" "localhost:18080${3:-/api/v1/ping}" | tr -d '\r' | awk 'NR==1{s=$2} tolower($1)=="x-cache-status:"{c=$2} END{print s, c}'
}
expect() { [ "$2" = "$3" ] && ok "$1" || nok "$1" "$3"; }

expect "anon novo: 1ª chamada MISS"        "200 MISS" "$(req 8.8.8.8)"
expect "anon novo: 2ª chamada HIT"         "200 HIT"  "$(req 8.8.8.8)"
SID=$(curl -s -D - -o /dev/null -H "X-Forwarded-For: 8.8.8.8" localhost:18080/auth/me | grep -i set-cookie | sed -E 's/.*anon_sid=([^;]*);.*/\1/')
$PY - "$TMP/data/auth/anon_sessions.db" "$SID" <<'PYE'
import sqlite3, sys
d = sqlite3.connect(sys.argv[1]); d.execute("update anon_sessions set active_seconds=999999 where session_id=?", (sys.argv[2],)); d.commit()
PYE
expect "esgotado: avançada 403 mesmo com HIT" "403 "      "$(req 8.8.8.8 "$SID")"
expect "esgotado + IP na allowlist: 200"       "200 HIT"   "$(req 203.0.113.129 "$SID")"
expect "esgotado: docs isento"                 "200 "      "$(req 8.8.8.8 "$SID" /api/v1/openapi.json | awk '{print $1" "}')"
expect "outro anon sem cookie: 200 HIT"        "200 HIT"   "$(req 9.9.9.9)"
req 8.8.8.8 "" /api/v1/ixps >/dev/null   # aquece o cache da entrada
expect "esgotado: ENTRADA segue aberta (HIT)"  "200 HIT"   "$(req 8.8.8.8 "$SID" /api/v1/ixps)"
expect "login: lista pág. 2 = 401"             "401 "      "$(req 9.9.9.9 "" '/api/v1/asns?page=2')"
expect "login: lista pág. 2 = 401 de novo (sem cache)" "401 " "$(req 9.9.9.9 "" '/api/v1/asns?page=2')"
expect "lista pág. 1 aberta"                   "200 MISS"  "$(req 9.9.9.9 "" '/api/v1/asns?page=1&limit=8')"
expect "login: allowlist pág. 2 = 200"         "200 MISS"  "$(req 203.0.113.129 "" '/api/v1/asns?page=2')"
[ "$(curl -s -H 'X-Forwarded-For: 9.9.9.9' 'localhost:18080/api/v1/asns?page=2' | grep -c login_required)" = 1 ] && ok "corpo 401 traz login_required" || nok "corpo 401" "-"
# Compressão: br só para quem pede; gzip da API para os demais; variantes não se misturam no cache.
enc() { curl -s -o /dev/null -D - -H "X-Forwarded-For: 7.7.7.7" ${1:+-H "Accept-Encoding: $1"} localhost:18080/api/v1/ixps/estimated-users \
  | tr -d '\r' | awk 'tolower($1)=="content-encoding:"{e=$2} END{if(e=="")e="identity"; print e}'; }
expect "br pedido → brotli"                    "br"        "$(enc 'gzip, deflate, br')"
expect "gzip pedido → gzip (variante própria)" "gzip"      "$(enc 'gzip')"
expect "br de novo (HIT) segue brotli"         "br"        "$(enc 'br')"
expect "sem Accept-Encoding → identidade"      "identity"  "$(enc '')"
[ "$(curl -s -H 'X-Forwarded-For: 7.7.7.7' -H 'Accept-Encoding: br' localhost:18080/api/v1/ixps/estimated-users | wc -c)" -gt 0 ] && ok "corpo brotli não vazio" || nok "corpo brotli" "-"
# Camada estática por hash: quem aceita br leva a API a entregar brotli-11 pré-comprimido; o nginx só repassa `br`.
V=0123456789abcdef
camada() { curl -s -o /dev/null -D - -H "X-Forwarded-For: 203.0.113.129" -H "Accept-Encoding: $1" "localhost:18080/api/v1/map/eco$2" | tr -d '\r'; }
cab() { echo "$1" | awk -v k="$2" 'tolower($1)==tolower(k":"){print $2}'; }
R1=$(camada 'gzip, br' "?v=$V")
expect "camada ?v= + br: a API recebe só br"   "br"        "$(cab "$R1" x-upstream-ae)"
expect "camada ?v= + br: nginx responde brotli" "br"       "$(cab "$R1" content-encoding)"
expect "1ª resposta (ainda sem br11) não vai ao cache" "MISS" "$(cab "$R1" x-cache-status)"
sleep 3   # a compressão nível 11 roda em segundo plano na API
R2=$(camada 'gzip, br' "?v=$V")
expect "2ª: brotli-11 do disco, imutável"      "br"        "$(cab "$R2" content-encoding)"
[ "$(cab "$R2" cache-control | grep -c immutable)" = 1 ] || [ "$(echo "$R2" | grep -ic "cache-control:.*immutable")" = 1 ] && ok "2ª: Cache-Control imutável" || nok "2ª: Cache-Control imutável" "$(echo "$R2" | grep -i cache-control)"
R3=$(camada 'br' "?v=$V")
expect "3ª: entra no cache do nginx (HIT)"     "HIT"       "$(cab "$R3" x-cache-status)"
expect "camada ?v= + só gzip: gzip da API"     "gzip"      "$(cab "$(camada 'gzip' "?v=$V")" x-upstream-ae)"
expect "sem ?v=: a API não recebe br"          ""          "$(cab "$(camada 'gzip, br' "")" x-upstream-ae)"
# Metatags das entidades: agente de prévia/rastreador recebe o HTML da API (/meta/); o navegador comum recebe a SPA.
corpo() { curl -s -H "X-Forwarded-For: 7.7.7.7" -A "$1" "localhost:18080$2"; }
expect "entidade + Googlebot: HTML de metatags da API" "1" "$(corpo 'Mozilla/5.0 (compatible; Googlebot/2.1)' /asn/64500 | grep -c 'META asn 64500')"
expect "entidade + ClaudeBot: HTML de metatags da API" "1" "$(corpo 'ClaudeBot/1.0' /ixp/sp | grep -c 'META ixp sp')"
expect "entidade + navegador comum: SPA (sem metatags da API)" "0" "$(corpo 'Mozilla/5.0 (X11; Linux x86_64) Firefox/130.0' /asn/64500 | grep -c 'META asn')"
expect "entidade + navegador comum: devolve o index.html" "1" "$(corpo 'Mozilla/5.0 Firefox/130.0' /asn/64500 | grep -c 'id="root"')"
expect "entidade inexistente + bot: cai na SPA"        "1" "$(corpo 'Googlebot/2.1' /uf/inexistente | grep -c 'id="root"')"
expect "página que não é entidade + bot: SPA"          "1" "$(corpo 'Googlebot/2.1' /fontes | grep -c 'id="root"')"
kill "$API_PID"; sleep 1
expect "API fora: fail-open serve do cache"    "200 HIT"   "$(req 9.9.9.9)"
[ $fail -eq 0 ] && echo "TODOS OK" || { echo "HÁ FALHAS"; exit 1; }
