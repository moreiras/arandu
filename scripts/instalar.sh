#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
#
# Prepara um servidor para rodar o serviço: .env com segredos gerados, data/ com permissões da API sem root, fontes do basemap,
# imagens e serviços no ar, cron diário do pipeline e da manutenção das contas, vigia de saúde. NÃO coleta dados: o pipeline é o do
# cron (`scripts/arandu-weekly.sh`, executor `arandu`); `--coletar` dispara a primeira execução já.
# Para quem migra dados de outro servidor: copie data/ antes e rode este script depois (ele não apaga nem sobrescreve dados).
#
#   bash scripts/instalar.sh [--simular] [--coletar] [--sem-cron] [--sem-vigia]
#
# Rode como o usuário do serviço (no grupo docker), na raiz do clone. Pede sudo só para as permissões de data/ e para o systemd.
# Idempotente: pode rodar de novo depois de ajustar o .env. Na primeira vez cria o .env e para (código 3) para você preencher.
# --simular  mostra o que faria, sem mudar nada (as conferências rodam).
# Variáveis: INSTALAR_DISCO_MIN_GB (padrão 80), INSTALAR_ESPERA_S (espera pela saúde, padrão 360), INSTALAR_HORA_PIPELINE (padrão 12, UTC).
# Fora do alcance deste script: proxy de borda (Cloudflare), origem escondida atrás dele, firewall e backup (ver o resumo no fim).
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR" || exit 1
ENV="$REPO_DIR/.env"
SIMULAR=false; COLETAR=false; CRON=true; VIGIA=true
for a in "$@"; do
    case "$a" in
        --simular) SIMULAR=true ;;
        --coletar) COLETAR=true ;;
        --sem-cron) CRON=false ;;
        --sem-vigia) VIGIA=false ;;
        -h|--help) sed -n 8,19p "$0"; exit 0 ;;
        *) echo "argumento desconhecido: $a" >&2; exit 2 ;;
    esac
done
# ~57 GiB de data/ num ambiente com 10 snapshots e o basemap da América do Sul (2026-11-17); folga para a coleta e o build dos tiles.
DISCO_MIN_GB="${INSTALAR_DISCO_MIN_GB:-80}"
ESPERA_S="${INSTALAR_ESPERA_S:-360}"
HORA="${INSTALAR_HORA_PIPELINE:-12}"

ok()    { echo "  [ok]    $*"; }
aviso() { echo "  [aviso] $*"; AVISOS=$((AVISOS + 1)); }
die()   { echo "  [erro]  $*" >&2; exit 1; }
etapa() { echo; echo "== $* =="; }
faz()   { echo "  + $*"; $SIMULAR || "$@"; }
AVISOS=0

# Valor de uma chave do .env (última ocorrência, sem aspas).
env_valor() { [[ -f "$ENV" ]] && grep -E "^$1=" "$ENV" | tail -1 | cut -d= -f2- | sed -E 's/^"(.*)"$/\1/; s/^'"'"'(.*)'"'"'$/\1/'; }
# Define KEY=VALOR no .env (troca a linha existente ou acrescenta). Com "se_vazio", só quando a chave falta ou está vazia.
env_define() {
    python3 - "$ENV" "$1" "$2" "${3:-sempre}" <<'PY'
import re, sys
caminho, chave, valor, modo = sys.argv[1:5]
linhas = open(caminho, encoding="utf-8").read().splitlines()
idx = [i for i, l in enumerate(linhas) if re.match(rf"^{re.escape(chave)}=", l)]
if idx:
    atual = linhas[idx[-1]].split("=", 1)[1].strip().strip("\"'")
    if modo == "se_vazio" and atual:
        sys.exit(0)
    linhas[idx[-1]] = f"{chave}={valor}"
else:
    linhas.append(f"{chave}={valor}")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas) + "\n")
PY
}
segredo() { python3 -c 'import secrets; print(secrets.token_urlsafe(48))'; }

compose_arquivos() {    # a mesma montagem do restart-safe.sh
    local f="-f docker-compose.yml"
    grep -qE '^WEB_NETWORK_NAME=.+' "$ENV" 2>/dev/null && f="$f -f docker-compose.no-nginx.yml"
    grep -qE '^PROD_OVERRIDES=true' "$ENV" 2>/dev/null && f="$f -f docker-compose.prod.yml"
    echo "$f"
}

# ── 1. Pré-requisitos ─────────────────────────────────────────────────────
etapa "1/7 Pré-requisitos"
[[ "$(id -u)" -ne 0 ]] || die "não rode como root: use o usuário do serviço (no grupo docker); o script pede sudo onde precisa"
[[ -f docker-compose.exemplo.yml && -f .env.example ]] || die "rode na raiz do clone"
if [[ ! -f docker-compose.yml ]]; then    # cópia local, fora do git: é ela que se edita por instalação
    if $SIMULAR; then echo "  + copiaria docker-compose.exemplo.yml para docker-compose.yml"
    else cp docker-compose.exemplo.yml docker-compose.yml && ok "docker-compose.yml criado a partir do docker-compose.exemplo.yml (edite se preciso)"; fi
elif ! cmp -s docker-compose.exemplo.yml docker-compose.yml; then
    echo "  aviso: docker-compose.yml difere do docker-compose.exemplo.yml; confira com: diff docker-compose.exemplo.yml docker-compose.yml"
fi
for c in docker python3 curl flock crontab; do command -v "$c" >/dev/null || die "falta o comando $c"; done
docker info >/dev/null 2>&1 || die "este usuário não fala com o Docker (daemon parado ou usuário fora do grupo docker)"
docker compose version >/dev/null 2>&1 || die "falta o Docker Compose v2 (plugin 'docker compose')"
ok "Docker $(docker version --format '{{.Server.Version}}' 2>/dev/null), Compose $(docker compose version --short 2>/dev/null)"
livre=$(( $(df -Pk "$REPO_DIR" | awk 'NR==2 {print $4}') / 1024 / 1024 ))
if [[ -d data/published && -n "$(ls -A data/published 2>/dev/null)" ]]; then
    ok "data/ já tem snapshots; ${livre} GiB livres"
elif (( livre < DISCO_MIN_GB )); then
    die "${livre} GiB livres; o mínimo para começar do zero é ${DISCO_MIN_GB} GiB (INSTALAR_DISCO_MIN_GB)"
else
    ok "${livre} GiB livres"
fi
# Sem userland-proxy=false o docker-proxy troca o IP de origem IPv6 pelo gateway da bridge (docker/nginx-real-ip.inc).
if ! grep -qE '"userland-proxy"[[:space:]]*:[[:space:]]*false' /etc/docker/daemon.json 2>/dev/null; then
    aviso "/etc/docker/daemon.json sem \"userland-proxy\": false: cliente IPv6 que chegue direto ao contêiner aparece com o IP da bridge (atrás de túnel ou de proxy no host não importa)"
fi

# ── 2. .env ───────────────────────────────────────────────────────────────
etapa "2/7 Configuração (.env)"
if [[ ! -f "$ENV" ]]; then
    if $SIMULAR; then
        echo "  + criaria .env a partir de .env.example, com segredos gerados, e pararia para você preencher"; exit 0
    fi
    install -m 600 .env.example "$ENV"
    for k in JWT_SECRET INTERNAL_API_TOKEN MCP_KEY_PEPPER; do env_define "$k" "$(segredo)"; done
    env_define MCP_KEY_ATIVA 1
    env_define ACCESS_POLICY_MODE enforce
    env_define API_USER 1001:0
    env_define API_DATA_MODE ro
    env_define APP_BASE_URL ""
    cat <<EOF
  .env criado (0600) com JWT_SECRET, INTERNAL_API_TOKEN e MCP_KEY_PEPPER gerados, chave de MCP ligada, política de acesso em
  enforce e API sem root. Preencha antes de rodar de novo:
    APP_BASE_URL                  endereço público (https://...), obrigatório
    SITE_*                        nome e endereço do site (seção no fim do .env.example)
    GOOGLE_/LINKEDIN_/PEERINGDB_  credenciais OAuth (ao menos um provedor; sem login ninguém vê contatos)
    ALLOWED_IPS                   só as redes que dispensam login; nunca faixa larga
    NOMINATIM_USER_AGENT          com um contato real
    NGINX_REAL_IP_INC             atrás da Cloudflare: ./docker/nginx-real-ip-cloudflare.inc
    API_MEM_LIMIT, API_MEMSWAP_LIMIT (iguais), WORKER_MEM_LIMIT, ARANDU_RETENCAO conforme o host
EOF
    exit 3
fi
[[ "$(stat -c %a "$ENV" 2>/dev/null || stat -f %Lp "$ENV")" == "600" ]] || aviso ".env não está com permissão 0600 (chmod 600 .env)"
[[ -n "$(env_valor JWT_SECRET)" ]] || die "JWT_SECRET vazio no .env (a API não sobe sem ele)"
[[ -n "$(env_valor APP_BASE_URL)" ]] || die "APP_BASE_URL vazio no .env"
if [[ -z "$(env_valor GOOGLE_CLIENT_ID)$(env_valor LINKEDIN_CLIENT_ID)$(env_valor PEERINGDB_CLIENT_ID)" ]]; then
    aviso "nenhum provedor OAuth configurado: ninguém consegue entrar e os contatos ficam inacessíveis"
fi
[[ -n "$(env_valor SITE_URL)" ]] || aviso "SITE_URL vazio: o site usa o nome e o endereço padrão do software"
[[ "$(env_valor NOMINATIM_USER_AGENT)" != *example.com* ]] || aviso "NOMINATIM_USER_AGENT ainda com o contato de exemplo"
[[ "$(env_valor ACCESS_POLICY_MODE)" == "enforce" ]] || aviso "ACCESS_POLICY_MODE=$(env_valor ACCESS_POLICY_MODE): fora de enforce a política de acesso não barra nada"
[[ "$(env_valor MCP_KEY_ATIVA)" == "1" ]] || aviso "MCP_KEY_ATIVA desligada: todos os clientes do MCP dividem o orçamento anônimo"
[[ "$(env_valor CONTATOS_ALLOWLIST)" != "1" ]] || aviso "CONTATOS_ALLOWLIST=1: IP da allowlist vê contatos sem conta e sem cota"
grep -qE '^PROD_OVERRIDES=true' "$ENV" && aviso "PROD_OVERRIDES=true liga docker-compose.prod.yml, com tetos antigos (worker com 1 GiB, API 9 GiB) que passam por cima dos *_MEM_LIMIT do .env"
if [[ -n "$(env_valor API_MEM_LIMIT)" && "$(env_valor API_MEMSWAP_LIMIT)" != "$(env_valor API_MEM_LIMIT)" ]]; then
    aviso "API_MEMSWAP_LIMIT diferente de API_MEM_LIMIT: estourar o teto leva o host ao swap em vez de reiniciar a API"
fi
inc="$(env_valor NGINX_REAL_IP_INC)"
if [[ -z "$inc" ]]; then
    aviso "NGINX_REAL_IP_INC vazio: atrás da Cloudflare todo cliente aparece com IP dela e todos dividem o mesmo orçamento"
else
    [[ -f "$inc" ]] || die "NGINX_REAL_IP_INC aponta para $inc, que não existe"
    ok "IP real: $inc"
fi
# Faixas privadas não importam (atrás do IP real nunca aparecem como cliente); larga é IPv4 mais curto que /16 ou IPv6 que /32.
allowed_avisos=$(python3 - "$(env_valor ALLOWED_IPS)" <<'PY'
import ipaddress, sys
for e in filter(None, (x.strip() for x in sys.argv[1].split(","))):
    try:
        n = ipaddress.ip_network(e, strict=False)
    except ValueError:
        print(f"ALLOWED_IPS: entrada inválida {e!r} (a API a ignora)"); continue
    if n.prefixlen == 0:
        print("ZERO")
    elif not n.is_private and n.prefixlen < (16 if n.version == 4 else 32):
        print(f"ALLOWED_IPS com faixa larga {e}: quem está nela dispensa login e orçamento anônimo")
PY
)
while IFS= read -r l; do
    [[ -z "$l" ]] && continue
    [[ "$l" == ZERO ]] && die "ALLOWED_IPS libera a Internet inteira"
    aviso "$l"
done <<< "$allowed_avisos"
COMPOSE="docker compose $(compose_arquivos)"
ok "compose: $COMPOSE"

# ── 3. data/ ──────────────────────────────────────────────────────────────
etapa "3/7 Dados (data/)"
faz mkdir -p data/published data/raw data/normalized data/sources data/auth data/ops logs
if [[ -n "$(env_valor API_USER)" ]]; then
    echo "  (sudo) permissões da API sem root em data/auth, data/ops/usage, data/ops/uso_conta, data/cache/br11"
    faz sudo bash scripts/preparar-dados-api-sem-root.sh
else
    aviso "API_USER vazio: a API roda como root no contêiner (veja scripts/preparar-dados-api-sem-root.sh)"
fi
faz bash scripts/fetch-basemap-fonts.sh data
[[ -f data/tiles/current.json ]] || echo "  (sem basemap: o pipeline gera os tiles na primeira execução, o que leva horas; os mapas ficam sem fundo até lá)"

# ── 4. Imagens e serviços ─────────────────────────────────────────────────
etapa "4/7 Imagens e serviços"
faz $COMPOSE build api frontend
faz $COMPOSE up -d
if ! $SIMULAR; then
    # Não há serviço Routinator: o RPKI roda avulso no pipeline; a primeira execução, com o cache frio, é longa.
    fim=$(( SECONDS + ESPERA_S ))
    while :; do
        pendentes=""
        for s in api mcp frontend; do
            cid=$($COMPOSE ps -q "$s" 2>/dev/null | head -1)
            st=$([[ -n "$cid" ]] && docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null)
            [[ "$st" == "healthy" ]] || pendentes="$pendentes $s(${st:-ausente})"
        done
        [[ -z "$pendentes" ]] && { ok "api, mcp e frontend saudáveis"; break; }
        (( SECONDS < fim )) || { $COMPOSE logs --tail=30 api; die "sem saúde em ${ESPERA_S}s:$pendentes"; }
        sleep 10
    done
fi

# ── 5. cron ───────────────────────────────────────────────────────────────
etapa "5/7 Agendamento (cron do usuário $(id -un))"
API_CONTAINER=$($COMPOSE ps --format '{{.Name}}' api 2>/dev/null | head -1)
MARCA="# arandu (scripts/instalar.sh)"
LINHAS="$MARCA: pipeline diário (coleta pela cadência de cada fonte; snapshot semanal) e manutenção das contas (exclusão em 30 dias)
0 $HORA * * * cd $REPO_DIR && ARANDU_MODO=due MEM_SAMPLE_API_CONTAINER=${API_CONTAINER:-api} flock -n /tmp/arandurape-run.lock bash scripts/arandu-weekly.sh >> $REPO_DIR/logs/arandu.log 2>&1
20 4 * * * cd $REPO_DIR && $COMPOSE exec -T api python -m api.auth.manutencao >> $REPO_DIR/logs/manutencao.log 2>&1"
if ! $CRON; then
    echo "  (--sem-cron) linhas que entrariam:"; echo "$LINHAS" | sed 's/^/    /'
elif crontab -l 2>/dev/null | grep -qF "$MARCA"; then
    ok "cron já instalado (para refazer, apague as linhas marcadas com '$MARCA' no crontab -e)"
elif crontab -l 2>/dev/null | grep -qE 'run_weekly\.sh'; then
    aviso "o crontab chama run_weekly.sh, que não existe mais: troque essa linha pelas de baixo (crontab -e)"
    echo "$LINHAS" | sed 's/^/    /'
elif crontab -l 2>/dev/null | grep -qE 'arandu-weekly\.sh'; then
    aviso "o crontab já roda o pipeline por outra linha: não acrescentei nada (confira com crontab -l)"
else
    echo "$LINHAS" | sed 's/^/    /'
    $SIMULAR || { (crontab -l 2>/dev/null; echo "$LINHAS") | crontab - && ok "cron instalado"; }
fi

# ── 6. Vigia de saúde ─────────────────────────────────────────────────────
etapa "6/7 Vigia de saúde (systemd)"
if ! $VIGIA; then
    echo "  (--sem-vigia) instalação manual: docker/systemd/arandurape-vigia.service"
elif systemctl is-active --quiet arandurape-vigia.timer 2>/dev/null; then
    ok "arandurape-vigia.timer já ativo"
else
    unidade="$(mktemp)"
    sed -E "s|^User=.*|User=$(id -un)|; s|^WorkingDirectory=.*|WorkingDirectory=$REPO_DIR|" docker/systemd/arandurape-vigia.service > "$unidade"
    echo "  (sudo) instala o serviço e o timer em /etc/systemd/system/"
    faz sudo install -m 644 "$unidade" /etc/systemd/system/arandurape-vigia.service
    faz sudo install -m 644 docker/systemd/arandurape-vigia.timer /etc/systemd/system/arandurape-vigia.timer
    faz sudo systemctl daemon-reload
    faz sudo systemctl enable --now arandurape-vigia.timer
    rm -f "$unidade"
    grep -qE '^TELEGRAM_BOT_KEY=.+' .env && grep -qE '^TELEGRAM_CHAT_ID=.+' .env \
        || aviso "sem TELEGRAM_BOT_KEY/TELEGRAM_CHAT_ID no .env: o vigia e o pipeline não mandam alertas"
    aviso "a verificação externa (scripts/vigia-externo.sh) roda no cron de outra máquina; é sua"
fi

# ── 7. Primeira coleta e resumo ───────────────────────────────────────────
etapa "7/7 Resumo"
PRIMEIRA="cd $REPO_DIR && ARANDU_MODO=due ARANDU_PUBLICAR=1 flock -n /tmp/arandurape-run.lock bash scripts/arandu-weekly.sh >> logs/arandu.log 2>&1"
if [[ -n "$(ls -A data/published 2>/dev/null)" ]]; then
    ok "data/published já tem snapshots: o cron segue a partir deles"
elif $COLETAR; then
    echo "  primeira coleta e publicação (horas; acompanhe logs/arandu.log)"
    faz bash -c "$PRIMEIRA"
else
    echo "  sem snapshot ainda. Primeira coleta e publicação (horas), ou espere o cron das ${HORA}:00 UTC:"
    echo "    $PRIMEIRA"
fi
cat <<EOF

  Pendências que este script não resolve:
    - Cloudflare (regras de cache e bypass de contatos/auth/MCP), origem só acessível por ela, firewall do host;
    - retenção: defina ARANDU_RETENCAO e revise '$COMPOSE --profile worker run --rm worker python -m arandu gc --dry-run' antes de agendar o --apply;
    - backup cifrado fora do servidor (data/auth, published, sources, .env) e teste de restauração;
    - conferência: bash scripts/post-deploy-check.sh --base \$APP_BASE_URL.
EOF
(( AVISOS == 0 )) && echo "  Sem avisos." || echo "  $AVISOS aviso(s) acima."
