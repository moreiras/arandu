# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Alertas de falha: alerta-telegram.sh, vigia-saude.sh e os avisos do arandu-weekly.sh, com curl e docker falsos.

Nenhum teste fala com o Telegram: o conftest esvazia o comando de alerta e aponta ALERTA_ENV para um arquivo inexistente; aqui o curl
é um script que só grava o que recebeu.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _exe(path: Path, corpo: str) -> None:
    path.write_text("#!/usr/bin/env bash\n" + corpo)
    path.chmod(0o755)


# ── alerta-telegram.sh ──────────────────────────────────────────────────────

def _alerta(tmp_path, msg, chave=None, key="TOKEN-SECRETO", chat="-100123", rc_curl=0):
    bin_ = tmp_path / "bin"
    bin_.mkdir(exist_ok=True)
    reg = tmp_path / "curl.txt"
    # Grava os argumentos e a configuração recebida pela entrada padrão (-K -), uma chamada por bloco.
    _exe(bin_ / "curl", f'echo "ARGS $*" >> {reg}; echo "STDIN $(cat)" >> {reg}; exit {rc_curl}\n')
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "ALERTA_ESTADO": str(tmp_path / "estado"),
           "ALERTA_ORIGEM": "teste", "TELEGRAM_BOT_KEY": key, "TELEGRAM_CHAT_ID": chat}
    args = ["bash", str(ROOT / "scripts" / "alerta-telegram.sh")] + (["--chave", chave] if chave else [])
    r = subprocess.run(args, input=msg, env=env, capture_output=True, text=True, timeout=30)
    return r, (reg.read_text() if reg.exists() else "")


def test_alerta_envia_com_o_token_fora_da_linha_de_comando(tmp_path):
    r, reg = _alerta(tmp_path, "api unhealthy")
    assert r.returncode == 0
    args = [l for l in reg.splitlines() if l.startswith("ARGS")]
    assert len(args) == 1 and "TOKEN-SECRETO" not in args[0]          # a lista de processos do host é legível por todos
    assert "chat_id=-100123" in args[0] and "[teste] api unhealthy" in args[0]
    assert "api.telegram.org/botTOKEN-SECRETO/sendMessage" in reg   # pela entrada padrão


def test_alerta_repetido_e_suprimido_e_falha_de_envio_nao_marca(tmp_path):
    _alerta(tmp_path, "x", chave="k")
    _, reg = _alerta(tmp_path, "x de novo", chave="k")
    assert reg.count("ARGS") == 1                                       # mesma chave dentro do intervalo
    _alerta(tmp_path, "outra", chave="k2", rc_curl=22)
    _, reg = _alerta(tmp_path, "outra", chave="k2")
    assert reg.count("ARGS") == 3                                       # o envio que falhou não conta como enviado


def test_alerta_sem_configuracao_nao_chama_o_curl_e_sai_zero(tmp_path):
    r, reg = _alerta(tmp_path, "x", key="", chat="")
    assert r.returncode == 0 and reg == ""


# ── vigia-saude.sh ──────────────────────────────────────────────────────────

def _vigia(tmp_path, saude: dict, pressao_io=0, extra=None, rodadas=1):
    """saude: serviço → estado do healthcheck (ausente = sem contêiner). Devolve (stdout, chamadas ao docker, alertas)."""
    bin_ = tmp_path / "bin"
    bin_.mkdir(exist_ok=True)
    chamadas, alertas = tmp_path / "docker.txt", tmp_path / "alertas.txt"
    casos = "".join(f'    *"ps -q {s}"*) echo cid-{s};;\n' for s in saude)
    estados = "".join(f'    *cid-{s}*) echo {e};;\n' for s, e in saude.items())
    _exe(bin_ / "docker", f'echo "$*" >> {chamadas}\ncase "$*" in\n{casos}    *"ps -q"*) ;;\n'
                          f'    inspect*) case "$*" in\n{estados}    esac;;\nesac\nexit 0\n')
    psi = tmp_path / "psi"
    psi.mkdir(exist_ok=True)
    (psi / "io").write_text(f"some avg10=0.00 avg60=0.00 avg300=0.00 total=0\nfull avg10=0.00 avg60={pressao_io}.50 avg300=0.00 total=0\n")
    (psi / "memory").write_text("some avg10=0.00 avg60=0.00 avg300=0.00 total=0\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=0\n")
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "VIGIA_DIR": str(tmp_path), "VIGIA_ESTADO": str(tmp_path / "estado"),
           "VIGIA_FALHAS": "1", "VIGIA_PSI_DIR": str(psi), "VIGIA_ALERTA_CMD": f"cat >> {alertas}", **(extra or {})}
    out = ""
    for _ in range(rodadas):
        r = subprocess.run(["bash", str(ROOT / "scripts" / "vigia-saude.sh")], env=env, capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, r.stderr
        out += r.stdout
    ler = lambda p: p.read_text() if p.exists() else ""                 # noqa: E731
    return out, ler(chamadas), ler(alertas)


def test_vigia_reinicia_a_api_e_leva_o_frontend_junto(tmp_path):
    _, docker, alertas = _vigia(tmp_path, {"api": "unhealthy", "mcp": "healthy", "frontend": "healthy"})
    assert "compose restart api" in docker and "compose restart frontend" in docker and "restart mcp" not in docker
    assert "reiniciando api" in alertas


def test_vigia_nao_reinicia_com_o_host_sob_pressao(tmp_path):
    out, docker, alertas = _vigia(tmp_path, {"api": "unhealthy", "mcp": "unhealthy", "frontend": "healthy"}, pressao_io=83)
    assert "restart" not in docker
    assert "host está sob pressão" in alertas and "io=83%" in alertas
    # Pressão baixou e a API continua unhealthy: reinicia na rodada seguinte (as falhas não foram zeradas).
    _, docker, _ = _vigia(tmp_path, {"api": "unhealthy", "mcp": "healthy", "frontend": "healthy"}, pressao_io=5)
    assert "compose restart api" in docker


def test_vigia_deixa_o_frontend_quando_o_problema_e_a_api(tmp_path):
    out, docker, alertas = _vigia(tmp_path, {"api": "starting", "mcp": "healthy", "frontend": "unhealthy"})
    assert "restart" not in docker and "o problema é da API" in out and alertas == ""


def test_vigia_avisa_servico_sem_conteiner_e_nao_sobe_nada(tmp_path):
    _, docker, alertas = _vigia(tmp_path, {"api": "healthy", "frontend": "healthy"})
    assert "mcp sem contêiner rodando" in alertas
    assert "up" not in docker.split() and "start" not in docker.split()


def test_vigia_saudavel_nao_manda_nada(tmp_path):
    _, docker, alertas = _vigia(tmp_path, {"api": "healthy", "mcp": "healthy", "frontend": "healthy"}, rodadas=2)
    assert alertas == "" and "restart" not in docker


# ── avisos do pipeline (arandu-weekly.sh) ──────────────────────────────────

def _pipeline(tmp_path, rc_arandu=0, relatorio=None, rpki="off"):
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    _exe(bin_ / "docker", f'case "$*" in *"arandu run --date"*"--retomar"*) exit {rc_arandu};; esac\nexit 0\n')
    dados = tmp_path / "data"
    (dados / "ops" / "runs").mkdir(parents=True)
    if relatorio is not None:
        (dados / "ops" / "runs" / "2026-10-18.json").write_text(json.dumps(relatorio))
    alertas = tmp_path / "alertas.txt"
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "MEM_SAMPLE": "off", "DATE": "2026-10-18", "ARANDU_COMPARE": "off",
           "HOST_STEPS": "true", "RPKI_AVULSO": rpki, "RPKI_DESTINO": str(tmp_path / "rpki"), "ARANDU_DADOS_HOST": str(dados),
           "ALERTA_CMD": f"cat >> {alertas}"}
    r = subprocess.run(["bash", str(ROOT / "scripts" / "arandu-weekly.sh")], env=env, capture_output=True, text=True, timeout=60)
    return r, (alertas.read_text() if alertas.exists() else "")


def test_pipeline_sem_falha_nao_avisa(tmp_path):
    r, alertas = _pipeline(tmp_path, relatorio={"etapas": [{"id": "x", "status": "ok"}]})
    assert r.returncode == 0 and alertas == ""


def test_pipeline_avisa_etapa_opcional_que_falhou(tmp_path):
    rel = {"etapas": [{"id": "ok1", "status": "ok"},
                      {"id": "manrs_participantes", "status": "falha", "politica": "opcional",
                       "motivo": "saída 1", "tentativas": 3}]}
    r, alertas = _pipeline(tmp_path, relatorio=rel)
    assert r.returncode == 0
    assert "pipeline 2026-10-18: terminou com falhas" in alertas and "- manrs_participantes (opcional): saída 1, 3 tentativas" in alertas
    assert "ok1" not in alertas


def test_pipeline_avisa_quando_o_arandu_falha_e_quando_o_rpki_avulso_falha(tmp_path):
    r, alertas = _pipeline(tmp_path, rc_arandu=2, relatorio={"etapas": [], "abortada_em": "snapshot_completo"}, rpki="on")
    assert r.returncode == 2
    assert "falhou (código 2)" in alertas and "abortado em snapshot_completo" in alertas and "Routinator avulso falhou" in alertas


# ── vigia-externo.sh ────────────────────────────────────────────────────────

_CURL_FALSO = r"""out=""; cab=""; url=""; metodo=GET
while [ $# -gt 0 ]; do
  case "$1" in -o) out=$2; shift;; -D) cab=$2; shift;; -X) metodo=$2; shift;; -H|-d|-m|-w) shift;; http*) url=$1;; esac
  shift
done
echo "$metodo $url" >> "$REG"
case "$metodo $url" in
  "GET "*/health) code=$C_API; body=$B_API;;
  "GET "*/) code=$C_FRONT; body=$B_FRONT;;
  "POST "*/mcp) code=$C_MCP; body=$B_MCP; [ -n "$cab" ] && printf 'mcp-session-id: s123\r\n' > "$cab";;
  *) code=200; body="";;
esac
[ -n "$out" ] && printf '%s' "$body" > "$out"
printf '%s' "$code"
"""
_OK = {"C_FRONT": "200", "B_FRONT": '<html><div id="root"></div></html>', "C_API": "200", "B_API": '{"status":"ok"}',
       "C_MCP": "200", "B_MCP": 'event: message\ndata: {"result":{"serverInfo":{"name":"x"}}}'}


def _externo(tmp_path, **troca):
    bin_ = tmp_path / "bin"
    bin_.mkdir(exist_ok=True)
    _exe(bin_ / "curl", _CURL_FALSO)
    alertas, reg = tmp_path / "alertas.txt", tmp_path / "curl.txt"
    env = {**os.environ, **_OK, **troca, "PATH": f"{bin_}:{os.environ['PATH']}", "REG": str(reg),
           "VIGIA_EXTERNO_ESTADO": str(tmp_path / "estado"), "VIGIA_ALERTA_CMD": f"cat >> {alertas}"}
    r = subprocess.run(["bash", str(ROOT / "scripts" / "vigia-externo.sh"), "https://exemplo.invalid"], env=env,
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return (alertas.read_text() if alertas.exists() else ""), reg.read_text()


def test_vigia_externo_testa_os_tres_alvos_e_fecha_a_sessao_do_mcp(tmp_path):
    alertas, reg = _externo(tmp_path)
    assert alertas == ""
    assert "GET https://exemplo.invalid/" in reg and "GET https://exemplo.invalid/health" in reg
    assert "POST https://exemplo.invalid/mcp" in reg and "DELETE https://exemplo.invalid/mcp" in reg


def test_vigia_externo_criterio_por_alvo(tmp_path):
    ruim = {"B_FRONT": "<html>página de erro da Cloudflare</html>", "B_API": '{"status":"degradado"}', "B_MCP": '{"error":{}}'}
    assert _externo(tmp_path, **ruim)[0] == ""                       # uma falha não avisa (rede instável)
    alertas, _ = _externo(tmp_path, **ruim)
    assert "frontend fora" in alertas and "sem o HTML da aplicação" in alertas
    assert "api fora" in alertas and "sem \"status\":\"ok\"" in alertas
    assert "mcp fora" in alertas and "não trouxe serverInfo" in alertas


def test_vigia_externo_so_avisa_depois_de_falhas_seguidas_e_zera_no_sucesso(tmp_path):
    assert _externo(tmp_path, C_API="502")[0] == ""
    alertas, _ = _externo(tmp_path, C_API="502")
    assert "api fora" in alertas and "HTTP 502, 2 verificações seguidas" in alertas and "frontend" not in alertas
    _externo(tmp_path)
    assert _externo(tmp_path, C_API="000")[0].count("\n") == 1        # zerou: a primeira falha nova não avisa de novo
