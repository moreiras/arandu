# SPDX-License-Identifier: AGPL-3.0-or-later
"""T0 — scripts operacionais: cronometragem de etapas e relatório de disco."""
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _bash(script: str, **env) -> subprocess.CompletedProcess:
    import os
    return subprocess.run(["bash", "-c", script], cwd=ROOT, capture_output=True, text=True,
                          env={**os.environ, **env}, timeout=60)


def _records(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines()]


def test_step_registra_sucesso_e_devolve_zero(tmp_path):
    f = tmp_path / "runs" / "d.jsonl"
    r = _bash('source scripts/lib-steps.sh; step lg_ixbr true; echo rc=$?', OPS_RUNS_FILE=str(f))
    assert "rc=0" in r.stdout
    rec = _records(f)[0]
    assert rec["step"] == "lg_ixbr" and rec["exit"] == 0 and rec["status"] == "ok"
    assert rec["duration_s"] >= 0 and rec["start"].endswith("Z") and rec["end"].endswith("Z")


def test_step_preserva_codigo_de_saida_da_falha(tmp_path):
    f = tmp_path / "d.jsonl"
    r = _bash('source scripts/lib-steps.sh; step ixbr_api bash -c "exit 7"; echo rc=$?', OPS_RUNS_FILE=str(f))
    assert "rc=7" in r.stdout
    rec = _records(f)[0]
    assert rec["exit"] == 7 and rec["status"] == "falha"


def test_step_extrai_modulo_do_python_dash_m(tmp_path):
    f = tmp_path / "d.jsonl"
    _bash('source scripts/lib-steps.sh; step lg_ixbr echo python -m sources.lg_ixbr.collect --date 2026-01-01',
          OPS_RUNS_FILE=str(f))
    assert _records(f)[0]["module"] == "sources.lg_ixbr.collect"


def test_step_sanitiza_rotulo_para_json(tmp_path):
    f = tmp_path / "d.jsonl"
    _bash('source scripts/lib-steps.sh; step \'a"b c\' true', OPS_RUNS_FILE=str(f))
    assert _records(f)[0]["step"] == 'a_b_c'


def test_step_nao_falha_sem_arquivo_de_registro():
    r = _bash('unset OPS_RUNS_FILE; source scripts/lib-steps.sh; step X true; echo rc=$?')
    assert "rc=0" in r.stdout


def test_step_nao_falha_se_diretorio_nao_gravavel(tmp_path):
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o500)
    try:
        r = _bash('source scripts/lib-steps.sh; step X true; echo rc=$?', OPS_RUNS_FILE=str(ro / "sub" / "d.jsonl"))
        assert "rc=0" in r.stdout
    finally:
        ro.chmod(0o700)


def test_step_funciona_em_if_e_com_ou(tmp_path):
    f = tmp_path / "d.jsonl"
    r = _bash('source scripts/lib-steps.sh; if step A false; then echo sim; else echo nao; fi; step B false || echo caiu',
              OPS_RUNS_FILE=str(f))
    assert "nao" in r.stdout and "caiu" in r.stdout
    assert [x["step"] for x in _records(f)] == ["A", "B"]


def test_disk_report_gera_json_com_tipos_datas_df_e_inodes(tmp_path):
    data = tmp_path / "data"
    (data / "raw" / "2026-09-20").mkdir(parents=True)
    (data / "raw" / "2026-09-20" / "a.txt").write_text("x" * 5000)
    (data / "published" / "2026-09-20").mkdir(parents=True)
    (data / "raw" / "geolite2").mkdir()
    (data / "raw" / "geolite2" / "b.mmdb").write_text("y" * 5000)
    (data / "raw" / "21-06-2026").mkdir()
    (data / "tiles").mkdir()
    r = subprocess.run(["bash", "scripts/disk-report.sh", "--date", "2026-10-11", "--data-dir", str(data)],
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    doc = json.loads((data / "ops" / "disk" / "2026-10-11.json").read_text())
    assert doc["date"] == "2026-10-11" and doc["unit"] == "KiB"
    assert set(doc["by_type"]) >= {"raw", "published", "tiles"}
    assert doc["by_date"]["raw"]["2026-09-20"] >= 4
    # pastas que não são data (por fonte/cache) não entram em by_date
    assert set(doc["by_date"]["raw"]) == {"2026-09-20"}
    assert set(doc["outros"]["raw"]) == {"geolite2", "21-06-2026"}
    assert doc["df"]["size_kb"] > 0 and 0 <= doc["df"]["use_pct"] <= 100
    # overlayfs/btrfs (containers, CI) não reportam inodes: total 0 e use_pct nulo — o relatório não pode quebrar
    ino = doc["inodes"]
    assert ino["total"] > 0 or (ino["total"] == 0 and ino["use_pct"] is None)


def test_disk_report_falha_se_data_dir_nao_existe(tmp_path):
    r = subprocess.run(["bash", "scripts/disk-report.sh", "--data-dir", str(tmp_path / "nao")],
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 1


def test_disk_report_rejeita_argumento_desconhecido():
    r = subprocess.run(["bash", "scripts/disk-report.sh", "--bobagem"], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 2


def test_restart_safe_tem_sintaxe_valida_e_verificacao_pos_implantacao_nao_bloqueante():
    assert subprocess.run(["bash", "-n", "restart-safe.sh"], cwd=ROOT).returncode == 0
    text = (ROOT / "restart-safe.sh").read_text()
    i = text.index("5c — Verificação pós-implantação")
    bloco = text[i:text.index("# 6. LIMPEZA", i)]
    assert "post-deploy-check.sh" in bloco
    assert "rollback" not in bloco.lower().replace("nunca aborta nem dispara rollback", "").replace("rollback automático continua", "")


def test_rpki_vem_antes_da_publicacao_da_analise_bgp_e_da_saude_dos_asns():
    """O RPKI vem antes do BGP: depois dele, todas as rotas do routing_analysis sairiam 'not_found'. E vem antes do índice de
    ASNs, que nasce com has_rpki (1 escrita)."""
    from core.catalog.loader import load_catalog, ordem_de_execucao

    ordem = ordem_de_execucao(load_catalog(ROOT / "catalog"))
    assert ordem.index("rpki_collector") < ordem.index("asn_indice") < ordem.index("routing_analysis") < ordem.index("saude_asn")


def test_restart_safe_aquecimento_com_freio_de_memoria_e_sem_post_warmup_por_padrao():
    """Com 7 GiB a API toma OOM (exit 137) no meio dos /potential do aquecimento."""
    text = (ROOT / "restart-safe.sh").read_text()
    i = text.index('header "5b — Pré-aquecimento de cache"')
    bloco = text[i:text.index("# 5c. VERIFICAÇÃO PÓS-IMPLANTAÇÃO", i)]
    assert 'RESTART_SAFE_POST_WARMUP:-0' in bloco          # POST /warmup só se pedido
    assert "cgroup_mem_pct" in bloco and "WARM_MEM_MAX_PCT" in bloco and "WARM_PAUSE" in bloco
    assert "interrompido por segurança" in bloco
    # nunca aborta nem faz rollback por causa do aquecimento
    assert "rollback" not in bloco.lower()


def test_compose_prod_limite_da_api_e_de_9g():
    import re

    text = (ROOT / "docker-compose.prod.yml").read_text()
    m = re.search(r"memory:\s*(\d+)G", text.split("api:", 1)[1])
    assert m and int(m.group(1)) == 9


# ── scripts/arandu-exclusivo.sh: coleta manual e pipeline não rodam juntos ─────────────────────────────────────────────────────────

_FLOCK = pytest.mark.skipif(__import__("shutil").which("flock") is None, reason="flock (util-linux) não existe neste host")


@_FLOCK
def test_exclusivo_roda_o_comando_e_devolve_a_saida_dele(tmp_path):
    lock = tmp_path / "run.lock"
    r = _bash('bash scripts/arandu-exclusivo.sh -- bash -c "echo feito; exit 3"', ARANDU_LOCK=str(lock))
    assert "feito" in r.stdout and r.returncode == 3 and "lock obtido" in r.stderr


@_FLOCK
def test_exclusivo_desiste_com_75_se_o_pipeline_segura_o_lock(tmp_path):
    lock = tmp_path / "run.lock"
    # o pipeline do cron: `flock -n LOCK comando` segurando o lock enquanto o wrapper tenta
    r = _bash(f'flock -n {lock} sleep 5 & sleep 0.5; bash scripts/arandu-exclusivo.sh -- echo nao-deve-rodar; echo rc=$?; wait',
              ARANDU_LOCK=str(lock))
    assert "nao-deve-rodar" not in r.stdout and "rc=75" in r.stdout and "outra execução" in r.stderr


@_FLOCK
def test_exclusivo_com_esperar_aguarda_o_lock_soltar(tmp_path):
    lock = tmp_path / "run.lock"
    r = _bash(f'flock -n {lock} sleep 1 & sleep 0.3; bash scripts/arandu-exclusivo.sh --esperar 10 -- echo rodou; echo rc=$?; wait',
              ARANDU_LOCK=str(lock))
    assert "rodou" in r.stdout and "rc=0" in r.stdout


@_FLOCK
def test_exclusivo_exige_comando_e_espera_numerica(tmp_path):
    lock = tmp_path / "run.lock"
    assert _bash("bash scripts/arandu-exclusivo.sh", ARANDU_LOCK=str(lock)).returncode == 2
    assert _bash("bash scripts/arandu-exclusivo.sh --esperar x -- true", ARANDU_LOCK=str(lock)).returncode == 2


def test_compose_poe_teto_de_memoria_no_worker_e_na_api_sem_swap_extra():
    import yaml
    c = yaml.safe_load((ROOT / "docker-compose.exemplo.yml").read_text())["services"]
    for nome in ("api", "worker"):
        s = c[nome]
        assert "memory" in s["deploy"]["resources"]["limits"], nome
        assert "memswap_limit" in s, f"{nome}: sem memswap_limit, o teto vale só para a RAM e o excedente vai para o swap do host"
    assert "WORKER_MEM_LIMIT" in c["worker"]["deploy"]["resources"]["limits"]["memory"]
    # o swap da API não pode ser ligado ao `memory`: os overrides de produção (9G) e .no-nginx (3G) trocam `memory` e o Docker exige memswap >= memory
    assert "API_MEMSWAP_LIMIT" in c["api"]["memswap_limit"] and "API_MEM_LIMIT" not in c["api"]["memswap_limit"]


# ── Docker rootless: os scripts de implantação funcionam com o daemon com root e com o rootless ──────────────────────────────────────

def _preparar_isolado(tmp_path: Path) -> Path:
    """Cópia do preparar-dados e da lib num repositório falso: o script acha data/ pelo próprio caminho."""
    import shutil
    (tmp_path / "scripts").mkdir()
    for nome in ("preparar-dados-api-sem-root.sh", "lib-docker.sh"):
        shutil.copy(ROOT / "scripts" / nome, tmp_path / "scripts" / nome)
    (tmp_path / "data" / "published").mkdir(parents=True)
    return tmp_path / "scripts" / "preparar-dados-api-sem-root.sh"


def test_lib_docker_respeita_o_modo_forcado():
    assert _bash("source scripts/lib-docker.sh; docker_rootless && echo sim", ARANDU_DOCKER_ROOTLESS="1").stdout.strip() == "sim"
    assert _bash("source scripts/lib-docker.sh; docker_rootless || echo nao", ARANDU_DOCKER_ROOTLESS="0").stdout.strip() == "nao"
    assert _bash("source scripts/lib-docker.sh; docker_host_atual",
                 DOCKER_HOST="unix:///run/user/1002/docker.sock").stdout.strip() == "unix:///run/user/1002/docker.sock"


@pytest.mark.skipif(__import__("os").geteuid() == 0, reason="o teste roda como usuário comum")
def test_preparar_no_rootless_faz_o_chown_dentro_de_um_conteiner_sem_sudo(tmp_path):
    # No rootless o UID 1001 do contêiner é outro UID no host: o chown tem de rodar lá dentro, e o script não pode pedir sudo.
    script = _preparar_isolado(tmp_path)
    r = subprocess.run(["bash", str(script), "--dry-run"], capture_output=True, text=True, timeout=30,
                       env={**__import__("os").environ, "ARANDU_DOCKER_ROOTLESS": "1"})
    assert r.returncode == 0, r.stderr
    assert "docker run --rm --network none --user 0:0 --entrypoint sh" in r.stdout
    assert f"-v {tmp_path / 'data'}:/data arandurape-api:latest" in r.stdout
    assert 'chown -R "$u:0"' in r.stdout and "sh 1001 /data" in r.stdout
    assert "rode com sudo" not in r.stderr


@pytest.mark.skipif(__import__("os").geteuid() == 0, reason="o teste roda como usuário comum")
def test_preparar_com_docker_com_root_continua_exigindo_sudo(tmp_path):
    script = _preparar_isolado(tmp_path)
    r = subprocess.run(["bash", str(script), "--dry-run"], capture_output=True, text=True, timeout=30,
                       env={**__import__("os").environ, "ARANDU_DOCKER_ROOTLESS": "0"})
    assert r.returncode == 1 and "rode com sudo" in r.stderr


def test_preparar_rejeita_uid_nao_numerico(tmp_path):
    script = _preparar_isolado(tmp_path)
    r = subprocess.run(["bash", str(script), "--uid", "1001;x"], capture_output=True, text=True, timeout=30)
    assert r.returncode == 2


def test_instalar_no_rootless_nao_pede_sudo_e_passa_o_docker_host_ao_cron():
    text = (ROOT / "scripts" / "instalar.sh").read_text()
    assert 'source "$REPO_DIR/scripts/lib-docker.sh"' in text
    # permissões de data/ só depois do build (o chown roda num contêiner da imagem da API) e antes de subir os serviços
    i_build, i_prep, i_up = (text.index("faz $COMPOSE build api frontend"),
                             text.index("faz bash scripts/preparar-dados-api-sem-root.sh"), text.index("faz $COMPOSE up -d"))
    assert i_build < i_prep < i_up
    # as duas linhas do cron levam o DOCKER_HOST (o cron não o herda da sessão)
    assert "&& ${CRON_ENV}ARANDU_MODO=due" in text and "&& ${CRON_ENV}$COMPOSE exec -T api" in text
    # vigia no systemd do usuário, sem sudo
    bloco = text[text.index("elif $ROOTLESS; then"):text.index("elif systemctl is-active")]
    assert "systemctl --user enable --now arandurape-vigia.timer" in bloco and "sudo" not in bloco


def test_restart_safe_aceita_rootless_sem_sudo_e_mantem_a_exigencia_de_root_no_docker_com_root():
    text = (ROOT / "restart-safe.sh").read_text()
    assert 'source "$REPO_DIR/scripts/lib-docker.sh"' in text
    ramo = text[text.index("if docker_rootless; then"):text.index('ok "Executando como root"')]
    assert 'die "Docker rootless: rode como o usuário do serviço, sem sudo."' in ramo
    assert "Execute com sudo ou como root" in ramo


def test_restart_safe_constroi_pelo_compose_para_levar_a_identidade_do_env():
    """`docker build` puro não recebe os build args do .env: o frontend sairia com o nome e os contatos padrão."""
    text = (ROOT / "restart-safe.sh").read_text()
    codigo = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
    assert "docker build" not in codigo
    assert '$COMPOSE_BASE build --no-cache "$servico"' in codigo
    assert 'build_image "arandurape-frontend" frontend' in codigo and 'build_image "arandurape-api"      api' in codigo


def test_vigia_de_usuario_aponta_para_o_socket_rootless_e_tem_o_mesmo_timer():
    svc = (ROOT / "docker" / "systemd" / "user" / "arandurape-vigia.service").read_text()
    assert "Environment=DOCKER_HOST=unix://%t/docker.sock" in svc
    assert not any(l.startswith("User=") for l in svc.splitlines())
    assert "ExecStart=/usr/bin/env bash scripts/vigia-saude.sh" in svc
    corpo = lambda p: [l for l in p.read_text().splitlines() if not l.startswith("#")]
    assert corpo(ROOT / "docker" / "systemd" / "user" / "arandurape-vigia.timer") == corpo(ROOT / "docker" / "systemd" / "arandurape-vigia.timer")
