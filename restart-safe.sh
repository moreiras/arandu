#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
# restart-safe.sh
#
# Reconstrói e recria api, mcp e frontend sem cache, preservando dados.
# Use após qualquer atualização de código para garantir que tudo vai a produção.
#
# Uso:
#   sudo bash restart-safe.sh
#
# O que faz:
#   1. Salva tags atuais como :previous (ponto de rollback)
#   2. Reconstrói imagens api e frontend sem cache (api inclui o servidor MCP)
#   3. Para e recria api, mcp e frontend (sem tocar em volumes de dados)
#   4. Verifica saúde de todos os serviços (api, mcp, frontend)
#   5. Em caso de falha: rollback automático para as imagens anteriores
#
# O que NÃO toca:
#   - ./data/          (snapshots, raw, published — volume bind mount)
#   - volume rpki_cache (o RPKI roda avulso no pipeline, scripts/rpki-avulso.sh)
#   - .env             (configuração do ambiente)
#
# Não há serviço Routinator: ele roda avulso antes do worker (scripts/rpki-avulso.sh).

set -uo pipefail

# ============================================================
# Configuração
# ============================================================

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$REPO_DIR/restart-$(date -u +%Y%m%d-%H%M%S).log"

# Monta a lista de arquivos compose de forma incremental:
#   docker-compose.yml          — sempre (base; cópia local do docker-compose.exemplo.yml)
#   docker-compose.no-nginx.yml — quando WEB_NETWORK_NAME=... está no .env
#                                 (nginx externo já existente; sem container frontend na porta 80)
#   docker-compose.prod.yml     — quando PROD_OVERRIDES=true está no .env
#                                 (limites de memória de produção, políticas de logging, etc.)
#                                 Omitir em desenvolvimento para manter os defaults mais leves.
_COMPOSE_FILES="-f docker-compose.yml"
if grep -qE '^WEB_NETWORK_NAME=.+' "$REPO_DIR/.env" 2>/dev/null; then
    _COMPOSE_FILES="$_COMPOSE_FILES -f docker-compose.no-nginx.yml"
fi
if grep -qE '^PROD_OVERRIDES=true' "$REPO_DIR/.env" 2>/dev/null; then
    _COMPOSE_FILES="$_COMPOSE_FILES -f docker-compose.prod.yml"
fi
COMPOSE_BASE="docker compose $_COMPOSE_FILES"

HEALTH_RETRIES=12       # tentativas de health check após subir
HEALTH_INTERVAL=10      # segundos entre tentativas (total: ~120s)

# Serviços recriados por este script.
SERVICOS="api mcp frontend"

# --update-routinator: aviso em vez de ignorar em silêncio (o Routinator roda avulso).
if [[ "${1:-}" == "--update-routinator" ]]; then
    echo "restart-safe.sh não mexe no Routinator: ele roda avulso no pipeline (scripts/rpki-avulso.sh). Para atualizar a imagem: troque a tag e o digest em docker-compose.yml, a partir do docker-compose.exemplo.yml (ou ROUTINATOR_TAG no .env)" >&2
    exit 2
fi

# ============================================================
# Logging
# ============================================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

_log() {
    local level="$1"; shift
    local ts; ts="$(date -u +%FT%TZ)"
    echo -e "${ts} ${level} $*" | tee -a "$LOG_FILE"
}
log()  { _log "${CYAN}[INFO]${NC} " "$*"; }
ok()   { _log "${GREEN}[ OK ]${NC} " "$*"; }
warn() { _log "${YELLOW}[WARN]${NC} " "$*"; }
err()  { _log "${RED}[ERRO]${NC} " "$*"; }
header() {
    local line="════════════════════════════════════════════"
    echo -e "\n${BOLD}${CYAN}${line}${NC}" | tee -a "$LOG_FILE"
    echo -e "${BOLD}${CYAN}  $*${NC}"      | tee -a "$LOG_FILE"
    echo -e "${BOLD}${CYAN}${line}${NC}\n" | tee -a "$LOG_FILE"
}

die() {
    err "$*"
    err "Log: $LOG_FILE"
    exit 1
}

# ============================================================
# Funções auxiliares
# ============================================================

# Retorna o status do healthcheck nativo do Docker para um serviço compose.
# Evita `docker compose exec`, que falha com erros de fifo/OCI quando o processo
# do container ainda não iniciou (janela logo após `docker compose up -d`).
_docker_health() {
    local service="$1"
    local cid
    cid=$($COMPOSE_BASE ps -q "$service" 2>/dev/null | head -1)
    [[ -z "$cid" ]] && return 1
    local status
    status=$(docker inspect --format='{{.State.Health.Status}}' "$cid" 2>/dev/null)
    echo "$(date -u +%FT%TZ) [DEBUG] $service health status: ${status:-unknown}" >> "$LOG_FILE" 2>&1
    [[ "$status" == "healthy" ]]
}

api_healthy()      { _docker_health api;      }
frontend_healthy() { _docker_health frontend; }
mcp_healthy()      { _docker_health mcp;      }

# Aguarda serviços ficarem saudáveis
wait_healthy() {
    local label="$1"
    local check_fn="$2"
    log "Aguardando $label..."
    for i in $(seq 1 $HEALTH_RETRIES); do
        if $check_fn; then
            ok "$label saudável"
            return 0
        fi
        log "  $label não pronto (tentativa $i/$HEALTH_RETRIES)..."
        sleep $HEALTH_INTERVAL
    done
    err "$label não ficou saudável em $((HEALTH_RETRIES * HEALTH_INTERVAL))s"
    return 1
}

# Para e remove só api, mcp e frontend. Nunca `down`: com um contêiner avulso de pé (worker, rpki),
# ele tentaria remover a rede compartilhada.
para_servicos() {
    $COMPOSE_BASE stop $SERVICOS >> "$LOG_FILE" 2>&1
    $COMPOSE_BASE rm -f $SERVICOS >> "$LOG_FILE" 2>&1
}

# Salva tag :latest como :previous para um par de imagem
tag_as_previous() {
    local image="$1"
    if docker image inspect "${image}:latest" &>/dev/null; then
        docker image tag "${image}:latest" "${image}:previous" >> "$LOG_FILE" 2>&1
        log "  ${image}:latest → ${image}:previous"
    else
        log "  ${image}:latest não existe ainda — sem rollback disponível"
    fi
}

# Restaura :previous como :latest e reinicia
rollback() {
    err "╔══════════════════════════════════════════╗"
    err "║          ROLLBACK AUTOMÁTICO             ║"
    err "╚══════════════════════════════════════════╝"
    err "Restaurando imagens anteriores..."

    local rolled_back=false
    for image in arandurape-api arandurape-frontend; do
        if docker image inspect "${image}:previous" &>/dev/null; then
            docker image tag "${image}:previous" "${image}:latest" >> "$LOG_FILE" 2>&1
            err "  ${image}:previous → ${image}:latest (restaurado)"
            rolled_back=true
        else
            err "  ${image}:previous não encontrado — não foi possível restaurar"
        fi
    done

    if $rolled_back; then
        err "Reiniciando containers com imagens anteriores..."
        para_servicos || true
        $COMPOSE_BASE up -d $SERVICOS >> "$LOG_FILE" 2>&1 || true
        sleep 5

        if api_healthy && frontend_healthy; then
            err "Rollback concluído — sistema restaurado com versão anterior"
        else
            err "Rollback falhou também. Verifique manualmente:"
            err "  docker compose logs api"
            err "  docker compose logs frontend"
        fi
    fi

    err "Log completo: $LOG_FILE"
    exit 1
}

# Reconstrói uma imagem sem cache. Em caso de falha, imprime os erros reais do
# build (ex.: tsc --noEmit, vite, pip) no console — não só um ponteiro pro log.
# Retorna 0 em sucesso, 1 em falha.
build_image() {
    local name="$1" dockerfile="$2"
    local out; out="$(mktemp)"

    log "Construindo ${name} (sem cache)..."
    if docker build --no-cache -f "$dockerfile" -t "${name}:latest" . > "$out" 2>&1; then
        cat "$out" >> "$LOG_FILE"
        rm -f "$out"
        ok "${name}:latest construída"
        return 0
    fi

    cat "$out" >> "$LOG_FILE"
    err "Build de ${name} falhou — abortando sem derrubar o serviço."
    err "As imagens :previous não foram afetadas."
    echo -e "${RED}┌──────── erros do build (${name}) ────────${NC}" | tee -a "$LOG_FILE" >&2
    # Mostra as últimas 50 linhas diretamente: o erro real do Rollup/tsc/pip aparece
    # imediatamente ANTES do stack trace e pode não conter palavras-chave óbvias.
    tail -n 50 "$out" >&2
    echo -e "${RED}└──────────────────────────────────────────${NC}" | tee -a "$LOG_FILE" >&2
    err "Log completo do build: $LOG_FILE"
    rm -f "$out"
    return 1
}

# ============================================================
# Início
# ============================================================

mkdir -p "$REPO_DIR"
touch "$LOG_FILE"

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║     Arandurape — Restart Seguro         ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "  Repositório : $REPO_DIR"
echo "  Log         : $LOG_FILE"
echo "  Serviços    : $SERVICOS"
echo ""

# ============================================================
# 1. PRÉ-REQUISITOS
# ============================================================

header "1 — Pré-requisitos"

[[ "$(id -u)" -ne 0 ]] && die "Execute com sudo ou como root."
ok "Executando como root"

cd "$REPO_DIR" || die "Não foi possível entrar em $REPO_DIR"
[[ -f "docker-compose.yml" ]] || die "docker-compose.yml não encontrado: copie o exemplo (cp docker-compose.exemplo.yml docker-compose.yml) e edite se preciso."
ok "Repositório: $REPO_DIR"

# Trava de deploy: o vigia de saúde (scripts/vigia-saude.sh) não reinicia nada enquanto ela existir. No diretório do projeto, não em /tmp.
TRAVA="$REPO_DIR/.restart-safe.lock"
if [[ -e "$TRAVA" ]] && kill -0 "$(cat "$TRAVA" 2>/dev/null)" 2>/dev/null; then
    die "Outro restart-safe.sh está em andamento (PID $(cat "$TRAVA"))."
fi
echo $$ > "$TRAVA"
trap 'rm -f "$TRAVA"' EXIT

docker info >> "$LOG_FILE" 2>&1 || die "Docker daemon não está acessível."
ok "Docker OK"

# ============================================================
# 2. SALVAR PONTO DE ROLLBACK
# ============================================================

header "2 — Salvando ponto de rollback"

tag_as_previous "arandurape-api"
tag_as_previous "arandurape-frontend"
ok "Imagens anteriores salvas como :previous"

# ============================================================
# 3. BUILD SEM CACHE
# ============================================================

header "3 — Rebuild sem cache"

# O build do frontend roda `tsc --noEmit && vite build` (gate de tipagem estrita):
# erros de tipo abortam o build aqui, antes de qualquer troca de container.
build_image "arandurape-api"      "Dockerfile.api"      || exit 1
build_image "arandurape-frontend" "Dockerfile.frontend" || exit 1

# ============================================================
# 4. PARAR E RECRIAR CONTAINERS
# ============================================================
#
# Só api, mcp e frontend. Sem -v: preserva todos os volumes.

header "4 — Recriando containers"

log "Parando api, mcp e frontend..."
para_servicos
ok "Containers parados"

# Limpa o cache de disco do nginx antes de subir os novos containers.
# O volume persiste entre restarts; sem limpeza, respostas antigas (schema
# anterior) podem ser servidas por até max-age (1h) mesmo depois de um deploy.
# ATENÇÃO: o Docker Compose prefixa o nome do volume com o nome do projeto
# (ex: arandurape_nginx_cache), por isso usamos `docker compose config` para
# obter o nome real em vez de hardcodar "nginx_cache".
log "Limpando cache de disco do nginx..."
NGINX_VOLUME=$($COMPOSE_BASE config --format json 2>/dev/null \
    | python3 -c "import sys,json; cfg=json.load(sys.stdin); print(cfg.get('volumes',{}).get('nginx_cache',{}).get('name','arandurape_nginx_cache'))" 2>/dev/null \
    || echo "arandurape_nginx_cache")
log "  Volume nginx cache: $NGINX_VOLUME"
if docker run --rm -v "${NGINX_VOLUME}:/cache" alpine \
        find /cache/api -mindepth 1 -delete >> "$LOG_FILE" 2>&1; then
    ok "Cache do nginx limpo ($NGINX_VOLUME)"
else
    warn "Não foi possível limpar cache do nginx (não crítico)"
fi

log "Iniciando novos containers..."
$COMPOSE_BASE up -d $SERVICOS >> "$LOG_FILE" 2>&1 || rollback
ok "Containers iniciados"

# ============================================================
# 5. HEALTH CHECKS
# ============================================================

header "5 — Verificação de saúde"

# API
if ! wait_healthy "API" api_healthy; then
    warn "API não saudável — iniciando rollback"
    $COMPOSE_BASE logs api --tail=30 >> "$LOG_FILE" 2>&1
    rollback
fi

# MCP
if ! wait_healthy "MCP" mcp_healthy; then
    warn "MCP não saudável — iniciando rollback"
    $COMPOSE_BASE logs mcp --tail=30 >> "$LOG_FILE" 2>&1
    rollback
fi

# Frontend
if ! wait_healthy "Frontend" frontend_healthy; then
    warn "Frontend não saudável — iniciando rollback"
    $COMPOSE_BASE logs frontend --tail=30 >> "$LOG_FILE" 2>&1
    rollback
fi

# Verifica snapshot disponível. O prewarm do lifespan ocupa a API por ~40 s logo após o
# "healthy"; um /health único com timeout curto estourava e era lido como "sem snapshot"
# (pulava o aquecimento da etapa 5b). Por isso: várias tentativas, timeout folgado e o
# erro real no log.
SNAP=""
SNAP_TRIES=6
for ((i = 1; i <= SNAP_TRIES; i++)); do
    SNAP=$($COMPOSE_BASE exec -T api python3 -c "
import urllib.request, json
r = urllib.request.urlopen('http://localhost:8000/health', timeout=15)
d = json.load(r)
print(d.get('latest_snapshot', ''))
" 2>>"$LOG_FILE" || echo "")
    [[ -n "$SNAP" ]] && break
    log "  /health sem snapshot (tentativa $i/$SNAP_TRIES) — API possivelmente ocupada com o prewarm"
    sleep 10
done

if [[ -n "$SNAP" ]]; then
    ok "API servindo snapshot: $SNAP"
else
    warn "Não foi possível obter o snapshot em /health após $SNAP_TRIES tentativas (ver $LOG_FILE)"
fi

# ============================================================
# 5b. PRÉ-AQUECIMENTO DE CACHE
# ============================================================
#
# Best-effort: nunca aborta nem dispara rollback. Aquece duas camadas:
#   1. Cache em memória da API: dicts parseados + byte-cache do latest + pré-aquecimento
#      dos top-1000 ASNs por clientes (o POST /warmup dispara prewarm_latest e
#      prewarm_top_asns). O lifespan já faz isso no startup; este POST é reforço síncrono.
#   2. proxy_cache do nginx (disco), batendo nos endpoints quentes via o próprio
#      container frontend com Accept-Encoding: gzip — como um browser faria.

header "5b — Pré-aquecimento de cache"

# Uso de memória da API (% do limite do cgroup, sem o cache de arquivos reclamável). Serve de freio do
# aquecimento: com 7 GiB a API morre por OOM (exit 137) no meio dos /potential.
cgroup_mem_pct() {
    $COMPOSE_BASE exec -T api python3 -c "
import re
def r(p):
    try:
        return open(p).read().strip()
    except OSError:
        return None
cur = r('/sys/fs/cgroup/memory.current') or r('/sys/fs/cgroup/memory/memory.usage_in_bytes')
mx = r('/sys/fs/cgroup/memory.max') or r('/sys/fs/cgroup/memory/memory.limit_in_bytes')
m = re.search(r'^inactive_file (\d+)', r('/sys/fs/cgroup/memory.stat') or '', re.M)
inact = int(m.group(1)) if m else 0
print(int((int(cur) - inact) * 100 / int(mx)) if cur and mx and mx.isdigit() else 0)
" 2>/dev/null || echo 0
}
WARM_MEM_MAX_PCT="${WARM_MEM_MAX_PCT:-80}"      # acima disto o aquecimento para (não derruba o deploy)
WARM_PAUSE="${WARM_PAUSE:-1}"                    # pausa entre chamadas /potential (segundos)
WARM_START_DELAY="${WARM_START_DELAY:-20}"       # deixa o prewarm do lifespan terminar antes dos /potential

if [[ -n "$SNAP" ]]; then
    # O lifespan da API já aquece (índices, VRPs e prewarm do latest e dos top ASNs). O `POST /warmup` dispara
    # tudo de novo, em paralelo, e dobrava o pico de memória; fica opcional (RESTART_SAFE_POST_WARMUP=1).
    if [[ "${RESTART_SAFE_POST_WARMUP:-0}" == "1" ]]; then
        if $COMPOSE_BASE exec -T api python3 -c "
import os, urllib.request
req = urllib.request.Request('http://localhost:8000/api/v1/warmup?date=$SNAP', method='POST')
token = os.environ.get('INTERNAL_API_TOKEN', '')
if token:
    req.add_header('X-Internal-Token', token)
urllib.request.urlopen(req, timeout=180)
" >> "$LOG_FILE" 2>&1; then
            ok "Cache em memória da API aquecido (POST /warmup, snapshot $SNAP)"
        else
            warn "Falha ao aquecer cache em memória da API (não crítico)"
        fi
    else
        ok "Cache em memória da API: aquecido pelo lifespan (POST /warmup dispensado)"
    fi

    WARM_PATHS="ixps external-ixps cdns/presence asns asns/names hilbert/v4 hilbert/v6 map/asns map/prefixes"
    WARM_TOTAL=0
    WARM_OK=0
    for p in $WARM_PATHS; do
        WARM_TOTAL=$((WARM_TOTAL + 1))
        if $COMPOSE_BASE exec -T frontend \
            wget -q -O /dev/null --header="Accept-Encoding: gzip" \
            "http://localhost:8080/api/v1/$p?date=$SNAP" >> "$LOG_FILE" 2>&1; then
            WARM_OK=$((WARM_OK + 1))
        fi
    done
    ok "proxy_cache do nginx pré-aquecido: $WARM_OK/$WARM_TOTAL endpoints (snapshot $SNAP)"

    # Aquece /potential de cada IXP (calculado por código, não coberto pelos 9 genéricos)
    IXP_CODES=$($COMPOSE_BASE exec -T api python3 -c "
import urllib.request, json
try:
    r = urllib.request.urlopen('http://localhost:8000/api/v1/ixps?date=$SNAP', timeout=30)
    data = json.loads(r.read())
    print(' '.join(e['code'] for e in data.get('ixps', [])))
except Exception:
    pass
" 2>>"$LOG_FILE")
    POT_TOTAL=0
    POT_OK=0
    POT_STOP=""
    [[ -n "$IXP_CODES" ]] && sleep "$WARM_START_DELAY"
    for c in $IXP_CODES; do
        POT_TOTAL=$((POT_TOTAL + 1))
        MEM_PCT=$(cgroup_mem_pct)
        if [[ "$MEM_PCT" =~ ^[0-9]+$ ]] && (( MEM_PCT >= WARM_MEM_MAX_PCT )); then
            POT_STOP="memória da API em ${MEM_PCT}% do limite (teto do aquecimento: ${WARM_MEM_MAX_PCT}%) antes de /ixps/$c"
            break
        fi
        if $COMPOSE_BASE exec -T frontend \
            wget -q -O /dev/null --header="Accept-Encoding: gzip" \
            "http://localhost:8080/api/v1/ixps/$c/potential?date=$SNAP" >> "$LOG_FILE" 2>&1; then
            POT_OK=$((POT_OK + 1))
        fi
        sleep "$WARM_PAUSE"
    done
    if [[ $POT_TOTAL -gt 0 ]]; then
        ok "Potencial dos IXPs pré-aquecido: $POT_OK/$POT_TOTAL (snapshot $SNAP)"
    fi
    if [[ -n "$POT_STOP" ]]; then
        warn "Aquecimento do potencial interrompido por segurança: $POT_STOP. O restante é calculado sob demanda."
    fi
else
    warn "Snapshot não obtido na etapa 5 — pré-aquecimento de cache pulado (rode o aquecimento manual)"
fi

# ============================================================
# 5c. VERIFICAÇÃO PÓS-IMPLANTAÇÃO (somente leitura)
# ============================================================
# Confere /health e a versão, rotas-chave, privacidade, MCP e páginas de fumaça pela URL pública
# (scripts/post-deploy-check.sh). Informativo: nunca aborta nem dispara rollback —
# o rollback automático continua dependendo só da verificação de saúde (etapa 5).

header "5c — Verificação pós-implantação"
if command -v python3 >/dev/null 2>&1 && [[ -f "$REPO_DIR/scripts/post-deploy-check.sh" ]]; then
    # Sem POST_DEPLOY_BASE, o script usa o SITE_URL do .env.
    PDC_ARGS=()
    [[ -n "${POST_DEPLOY_BASE:-}" ]] && PDC_ARGS=(--base "$POST_DEPLOY_BASE")
    if bash "$REPO_DIR/scripts/post-deploy-check.sh" ${PDC_ARGS[@]+"${PDC_ARGS[@]}"} 2>&1 | tee -a "$LOG_FILE"; then
        ok "Verificação pós-implantação sem falhas"
    else
        warn "Verificação pós-implantação com falhas (ver acima) — o deploy segue; investigar"
    fi
else
    warn "post-deploy-check indisponível (python3 ou script ausente) — etapa pulada"
fi

# ============================================================
# 6. LIMPEZA DE IMAGENS ANTIGAS
# ============================================================

header "6 — Limpeza"

# Remove imagens dangling (camadas sem tag após o rebuild)
DANGLING=$(docker images -f "dangling=true" -q)
if [[ -n "$DANGLING" ]]; then
    echo "$DANGLING" | xargs docker rmi >> "$LOG_FILE" 2>&1 || true
    ok "Imagens dangling removidas"
else
    ok "Sem imagens dangling para remover"
fi

# ============================================================
# RESUMO
# ============================================================

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  ✓  Restart concluído com sucesso        ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "  API       : nova imagem ativa"
echo "  MCP       : nova imagem ativa (mesma imagem da api)"
echo "  Frontend  : nova imagem ativa"
[[ -n "$SNAP" ]] && echo "  Snapshot  : $SNAP"
echo ""
echo "  Rollback disponível:"
echo "    docker image tag arandurape-api:previous arandurape-api:latest"
echo "    docker image tag arandurape-frontend:previous arandurape-frontend:latest"
echo "    $COMPOSE_BASE up -d --force-recreate api mcp frontend"
echo ""
echo "  Log: $LOG_FILE"
echo ""
