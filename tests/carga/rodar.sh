#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
#
# Teste de carga de ponta a ponta: mede a rede até o alvo, liga o amostrador no servidor, roda o Locust no cenário pedido com um
# canário (navegador real) ao lado, recolhe as amostras e o log do nginx do período e gera o relatório.
#
#   bash tests/carga/rodar.sh CENARIO [--alvo URL] [--ssh HOST] [--dir-remoto DIR] [--processos N] [--sem-canario] [--regravar]
#
# Padrões: --alvo $CARGA_ALVO, --ssh $CARGA_SSH (vazio: sem amostras do servidor), --dir-remoto ~/arandurape no servidor, --processos 1.
# No macOS o Locust roda sob `caffeinate -i` (sem sleep por inatividade); sleep manual ou tampa fechada param o gerador e o relatório
# acusa o intervalo sem pedidos.
# Pré-requisitos: .venv-carga (pip install -r tests/carga/requirements.txt), Docker (gravador e canário), SSH sem senha ao alvo.
# O alvo precisa confiar no X-Forwarded-For vindo do gerador (cada usuário virtual tem IP próprio); ver README.md.
# Saída: tests/carga/saida/<cenario>-<UTC>/ (relatorio.md, resumo.json e os brutos).
set -uo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$AQUI/../.." && pwd)"
CENARIO="${1:?uso: rodar.sh CENARIO [opções] (cenários em cenarios.yaml)}"; shift
ALVO="${CARGA_ALVO:-}"; SSH="${CARGA_SSH:-}"; DIR_REMOTO=""; PROCESSOS=1; CANARIO=true; REGRAVAR=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --alvo) ALVO="$2"; shift 2 ;;
        --ssh) SSH="$2"; shift 2 ;;
        --dir-remoto) DIR_REMOTO="$2"; shift 2 ;;
        --processos) PROCESSOS="$2"; shift 2 ;;
        --sem-canario) CANARIO=false; shift ;;
        --regravar) REGRAVAR=true; shift ;;
        *) echo "opção desconhecida: $1" >&2; exit 2 ;;
    esac
done
[[ -n "$ALVO" ]] || { echo "informe o alvo: --alvo URL ou CARGA_ALVO" >&2; exit 2; }
PY="${CARGA_PYTHON:-$RAIZ/.venv-carga/bin/python}"
[[ -x "$PY" ]] || { echo "falta o venv: python3.12 -m venv .venv-carga && .venv-carga/bin/pip install -r tests/carga/requirements.txt" >&2; exit 1; }
XFF_SETUP="${CARGA_XFF_SETUP:-${ALVO#http://}}"; XFF_SETUP="${XFF_SETUP%%[:/]*}"
RUN="$CENARIO-$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$AQUI/saida/$RUN"
mkdir -p "$OUT"
log() { echo "[$(date -u +%H:%M:%S)] $*"; }
PLAYWRIGHT="mcr.microsoft.com/playwright:v1.49.0-jammy"

# ── duração total do cenário (para o canário e o amostrador) ──
DURACAO=$("$PY" -c "
import yaml,sys; c=yaml.safe_load(open('$AQUI/cenarios.yaml')); x={**c['padrao'],**c['cenarios']['$CENARIO']}
print(int(len(x['degraus'])*x['degrau_s']))") || exit 1
log "cenário $CENARIO: $((DURACAO / 60)) min contra $ALVO; saída em $OUT"

# ── páginas gravadas ──
if $REGRAVAR || [[ ! -f "$AQUI/saida/paginas.json" ]]; then
    log "gravando as páginas (navegador real)"
    docker run --rm -v "$AQUI:/carga" -w /carga -e BASE_URL="$ALVO" -e XFF="$XFF_SETUP" "$PLAYWRIGHT" \
        bash -c "npm i playwright@1.49.0 >/dev/null 2>&1 && node gravar_paginas.js" || exit 1
fi
cp "$AQUI/saida/paginas.json" "$OUT/"

# ── rede e estado do alvo ──
log "medindo a rede até o alvo"
"$PY" - "$ALVO" "$XFF_SETUP" > "$OUT/rede.json" <<'PY'
import json, sys, time, urllib.request, concurrent.futures as cf
alvo, xff = sys.argv[1], sys.argv[2]
def get(p, rng=None):
    h = {"X-Forwarded-For": xff, "User-Agent": "arandu-carga/1"}
    if rng: h["Range"] = rng
    t = time.perf_counter(); b = urllib.request.urlopen(urllib.request.Request(alvo + p, headers=h), timeout=120).read()
    return time.perf_counter() - t, len(b), b
rtts = sorted(get("/health")[0] * 1000 for _ in range(10))
saude = json.loads(get("/health")[2])
t = time.perf_counter()
with cf.ThreadPoolExecutor(8) as ex:
    tot = sum(ex.map(lambda i: get("/tiles/current.pmtiles", f"bytes={100_000_000 + i * 2_000_000}-{100_000_000 + (i + 1) * 2_000_000 - 1}")[1], range(8)))
banda = tot / (time.perf_counter() - t) / 1e6
print(json.dumps({"health_ms_mediana": round(rtts[5], 1), "health_ms_min": round(rtts[0], 1), "banda_MBps": round(banda, 2),
                  "versao": saude.get("version"), "snapshot": saude.get("latest_snapshot")}))
PY
cat "$OUT/rede.json"

# o alvo tem de honrar o X-Forwarded-For do gerador: senão todos os usuários virtuais viram um IP só (e o teste mede o limite dele)
VISTO=$(curl -s -H "X-Forwarded-For: 198.18.0.1" "$ALVO/auth/diag" | "$PY" -c "import json,sys; print(json.load(sys.stdin).get('ip_visto'))")
if [[ "$VISTO" != "198.18.0.1" ]]; then
    echo "o alvo não honra o X-Forwarded-For deste gerador (vê $VISTO): inclua esse endereço em set_real_ip_from no real-ip.inc do alvo (README.md)" >&2
    exit 1
fi

REMOTO_OK=false
if [[ -n "$SSH" ]] && ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH" true 2>/dev/null; then
    REMOTO_OK=true
    DIR_REMOTO="${DIR_REMOTO:-$(ssh -n "$SSH" 'echo $HOME')/arandurape}"
    ssh -n "$SSH" "pgrep -f '^python -m arandu run' >/dev/null && echo sim || echo nao" > "$OUT/pipeline_rodando.txt"
    log "pipeline rodando no alvo: $(cat "$OUT/pipeline_rodando.txt")"
    API_CT=$(ssh -n "$SSH" "cd $DIR_REMOTO && docker compose ps --format '{{.Name}}' api" | head -1)
    FRONT_CT=$(ssh -n "$SSH" "cd $DIR_REMOTO && docker compose ps --format '{{.Name}}' frontend" | head -1)
    AMOSTRA="/tmp/arandu-carga-$RUN.jsonl"
    # `cd || exit;` e não `cd &&`: com `&&` a lista toda vai para segundo plano num subshell que segura a saída do ssh (trava)
    SAMPLER_PID=$(ssh -n "$SSH" "cd $DIR_REMOTO || exit 1; nohup python3 scripts/mem_sample.py --out $AMOSTRA --interval 5 --max-hours $((DURACAO / 3600 + 1)) --diag-container $API_CT </dev/null >/dev/null 2>&1 & echo \$!")
    log "amostrador no alvo: pid $SAMPLER_PID, contêineres $API_CT e $FRONT_CT"
else
    log "sem SSH ao alvo: o relatório sai só com o lado do cliente"
fi

limpar() {
    [[ -n "${CANARIO_CT:-}" ]] && docker stop "$CANARIO_CT" >/dev/null 2>&1
    [[ -n "${SAMPLER_PID:-}" ]] && ssh -n "$SSH" "kill $SAMPLER_PID 2>/dev/null" 2>/dev/null
}
trap 'limpar; exit 130' INT TERM

# ── canário ──
CANARIO_CT=""
if $CANARIO; then
    CANARIO_CT="arandu-canario-$$"
    docker run -d --rm --name "$CANARIO_CT" -v "$AQUI:/carga" -w /carga -e BASE_URL="$ALVO" -e XFF_SETUP="$XFF_SETUP" \
        -e DURACAO_S="$DURACAO" -e SAIDA="saida/$RUN/canario.jsonl" "$PLAYWRIGHT" \
        bash -c "npm i playwright@1.49.0 >/dev/null 2>&1 && node canario.js" >/dev/null && log "canário: $CANARIO_CT"
fi

# ── Locust ──
T0=$(date -u +%Y-%m-%dT%H:%M:%SZ)
log "Locust: $PROCESSOS processo(s)"   # 1 = processo único (com --processes 1 o Locust cria mestre e trabalhador, e um travamento de 60 s no gerador derruba o teste)
( cd "$AQUI" && CARGA_CENARIO="$CENARIO" CARGA_SAIDA="$OUT" CARGA_PAGINAS="$OUT/paginas.json" CARGA_XFF_SETUP="$XFF_SETUP" \
    $(command -v caffeinate >/dev/null && echo "caffeinate -i") "$(dirname "$PY")/locust" -f locustfile.py --host "$ALVO" --headless $( (( PROCESSOS > 1 )) && echo "--processes $PROCESSOS" ) \
    --csv "$OUT/locust" --html "$OUT/locust.html" --logfile "$OUT/locust.log" --loglevel INFO --only-summary ) > "$OUT/locust-resumo.txt" 2>&1
T1=$(date -u +%Y-%m-%dT%H:%M:%SZ)
log "Locust terminou ($T0 → $T1)"

# ── recolhe ──
[[ -n "$CANARIO_CT" ]] && docker stop "$CANARIO_CT" >/dev/null 2>&1
if $REMOTO_OK; then
    ssh -n "$SSH" "kill $SAMPLER_PID 2>/dev/null; cat $AMOSTRA; rm -f $AMOSTRA" > "$OUT/servidor.jsonl"
    # só as linhas dos usuários virtuais (IP na faixa de testes) e do canário
    ssh -n "$SSH" "docker logs --since $T0 --until $T1 $FRONT_CT 2>/dev/null | grep -E '^198\.(18|19)\.|^2001:db8:'" > "$OUT/nginx.log"
    log "recolhido: $(wc -l < "$OUT/servidor.jsonl") amostras do servidor, $(wc -l < "$OUT/nginx.log") linhas do nginx"
fi
"$PY" "$AQUI/relatorio.py" "$OUT" && log "relatório: $OUT/relatorio.md"
