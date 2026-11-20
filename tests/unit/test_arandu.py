# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — executor `arandu`: ordem calculada, política de falha, relatório, lock, retomada, status, gc."""
import json
import os
import re
from pathlib import Path

import pytest

from arandu import executor, ops, status
from arandu.runner import FakeRunner
from core.catalog.loader import dependencias_de_etapas, load_catalog, ordem_de_execucao, validate

ROOT = Path(__file__).resolve().parents[2]
ORDEM_ETAPAS = ROOT / "tests" / "contracts" / "ordem_etapas.json"

@pytest.fixture(autouse=True)
def _sem_bloqueio_por_disco(monkeypatch):
    """O disco da máquina de teste não pode decidir o resultado (bloqueio de coleta pesada: teste próprio em test_retencao)."""
    monkeypatch.setenv("ARANDU_BLOQUEIO_DISCO_PCT", "101")



@pytest.fixture(scope="module")
def cat():
    return load_catalog(ROOT / "catalog")


# ── ordem de execução ──────────────────────────────────────────────────────────

def test_catalogo_com_etapas_e_valido(cat):
    assert len(cat.steps) >= 40
    assert validate(cat) == []


def test_ordem_de_execucao_igual_ao_contrato(cat):
    """A ordem calculada (dependências + desempate por `ordem`) é contrato: o desempate cobre dependências que o catálogo não
    declara. Mudança intencional: regrave `tests/contracts/ordem_etapas.json` e REVISE o diff."""
    esperado = json.loads(ORDEM_ETAPAS.read_text(encoding="utf-8"))
    assert ordem_de_execucao(cat) == esperado


def test_todas_as_fontes_com_modulo_tem_etapa(cat):
    com_etapa = {x for s in cat.steps.values() for x in s.fontes}
    assert {f.id for f in cat.sources.values() if f.modulo} <= com_etapa


def test_ids_antigos_de_etapa_seguem_aceitos(cat, tmp_path):
    """Etapa renomeada: o id antigo vale em `--only` e no relatório de retomada (ALIASES_ETAPA)."""
    from core.catalog.loader import ALIASES_ETAPA

    assert set(ALIASES_ETAPA.values()) <= set(cat.steps) and not set(ALIASES_ETAPA) & set(cat.steps)
    assert [s.id for s in executor.planejar(cat, ["p2p3_metrics", "p6b_saude_asn"])] == ["metricas_ixp_asn", "saude_asn"]
    assert executor.etapas_de(cat, "p1_bgp_parser") == ["bgp_ixp"]
    rel = executor.caminho_relatorio(tmp_path, "2026-10-18")
    rel.parent.mkdir(parents=True, exist_ok=True)
    rel.write_text(json.dumps({"etapas": [{"id": "p2p3_metrics", "status": "ok"}]}))
    r, runner = _roda(cat, tmp_path, FakeRunner(), retomar=True, only=None, usar_lock=False)
    # reconhecida como concluída (pelo id antigo); é refeita porque as dependências dela rodaram de novo nesta execução
    assert (_status(r)["metricas_ixp_asn"].motivo or "").startswith("concluída antes, mas refeita porque")


def test_aliases_de_codigo_do_ixp_metrics_e_do_replay():
    import importlib.util

    from products.ixp_metrics import build, documentos_asn, metricas_ixp, p2, p3

    assert p2.run_p2 is metricas_ixp.gerar_metricas_ixp and p3.run_p3 is documentos_asn.gerar_documentos_asn
    chamado = {}
    orig = build.run
    try:
        build.run = lambda **kw: chamado.update(kw) or {}
        build.main(["--date", "2026-10-18", "--no-p3"])
        assert chamado["sem_documentos_asn"] is True and chamado["sem_metricas_ixp"] is False
    finally:
        build.run = orig
    spec = importlib.util.spec_from_file_location("replay", ROOT / "scripts" / "replay.py")
    rp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rp)
    assert {rp.ALIASES_STAGES.get(s, s) for s in ("p1", "p2p3", "p6", "bgp", "p6b")} == set(rp.STAGES_ALL)


def test_ciclo_e_detectado(cat):
    import copy

    c2 = copy.deepcopy(cat)
    c2.steps["lg_ixbr"].depois_de = ["metricas_ixp_asn"]
    with pytest.raises(ValueError):
        ordem_de_execucao(c2)


# ── executor ───────────────────────────────────────────────────────────────────

def _roda(cat, tmp_path, runner=None, **kw):
    runner = runner or FakeRunner()
    rel = executor.executar(cat, "2026-10-18", tmp_path, runner, usar_lock=kw.pop("usar_lock", True),
                            log=lambda *_: None, versao="t", sleep=lambda s: None, **kw)
    return rel, runner


def _status(rel):
    return {e.id: e for e in rel.etapas}


def test_execucao_completa_ok_e_relatorio_gravado(cat, tmp_path):
    rel, runner = _roda(cat, tmp_path)
    assert rel.ok and rel.abortada_em is None
    s = _status(rel)
    assert s["lg_ixbr"].status == "ok" and s["host_warmup"].status == "delegada_ao_host"
    assert _primeira(runner) == "lg_ixbr" and "host_warmup" not in runner.chamadas
    dados = json.loads(executor.caminho_relatorio(tmp_path, "2026-10-18").read_text())
    assert dados["ok"] is True and dados["falhas_criticas"] == [] and dados["versao"] == "t"
    assert [e["id"] for e in dados["etapas"]][35:37] == ["lg_ixbr", "ixbr_api"]      # antes vêm as 35 etapas só do arandu


def test_falha_critica_aborta_o_resto(cat, tmp_path):
    rel, runner = _roda(cat, tmp_path, FakeRunner({"registro_br": 1}))
    s = _status(rel)
    assert not rel.ok and rel.abortada_em == "registro_br"
    assert s["registro_br"].status == "falha"
    assert s["lacnic_delegated"].status == "nao_executada"
    assert "lacnic_delegated" not in runner.chamadas
    dados = json.loads(executor.caminho_relatorio(tmp_path, "2026-10-18").read_text())
    assert dados["falhas_criticas"] == ["registro_br"]


def test_falha_opcional_segue_e_aparece_nos_avisos(cat, tmp_path):
    rel, runner = _roda(cat, tmp_path, FakeRunner({"anatel_scm": 1, "rpki_collector": 3}))
    assert rel.ok
    assert "asn_indice" in runner.chamadas
    dados = json.loads(executor.caminho_relatorio(tmp_path, "2026-10-18").read_text())
    assert sorted(dados["avisos"]) == ["anatel_scm", "rpki_collector"]


def test_falha_opcional_restaura_a_ultima_versao_boa_do_armazem(cat, tmp_path):
    """O manifesto declara a versão do armazém para a fonte; o arquivo tem de estar na data (senão cabos somem do snapshot)."""
    _versao_antiga(tmp_path, "anatel_scm", "2026-10-10", "normalized/summary/scm.json.gz", "2026-10-10T05:00:00Z")
    rel, _ = _roda(cat, tmp_path, FakeRunner({"anatel_scm": 1}))
    e = _status(rel)["anatel_scm"]
    assert e.status == "falha" and e.reutilizadas and e.reutilizadas[0]["as_of"] == "2026-10-10"
    assert (tmp_path / "normalized" / "2026-10-18" / "summary" / "scm.json.gz").read_text() == "conteudo anatel_scm 2026-10-10"


def test_receita_pulada_por_marcador_recente_reaproveita_a_ultima(cat, tmp_path):
    ant = tmp_path / "normalized" / "2026-10-04" / "summary"
    ant.mkdir(parents=True)
    (ant / "receita_socios.json.gz").write_bytes(b"x")
    (tmp_path / "receita_socios_last_run.json").write_text(json.dumps({"date": "2026-10-04"}))
    rel, runner = _roda(cat, tmp_path, env={})
    e = _status(rel)["receita_socios"]
    assert e.status == "pulada" and "reaproveitado de 2026-10-04" in e.motivo
    assert "receita_socios" not in runner.chamadas
    assert (tmp_path / "normalized" / "2026-10-18" / "summary" / "receita_socios.json.gz").read_bytes() == b"x"


def test_receita_vencida_roda_e_grava_marcador(cat, tmp_path):
    (tmp_path / "receita_socios_last_run.json").write_text(json.dumps({"date": "2026-08-01"}))
    rel, runner = _roda(cat, tmp_path, env={})
    assert "receita_socios" in runner.chamadas
    assert json.loads((tmp_path / "receita_socios_last_run.json").read_text()) == {"date": "2026-10-18"}


def test_receita_limite_pode_vir_do_ambiente(cat, tmp_path):
    (tmp_path / "receita_socios_last_run.json").write_text(json.dumps({"date": "2026-10-10"}))
    rel, runner = _roda(cat, tmp_path, env={"RECEITA_SOCIOS_MAX_AGE_DAYS": "3"})
    assert "receita_socios" in runner.chamadas


def test_receita_falha_usa_ultima_valida_e_nao_aborta(cat, tmp_path):
    ant = tmp_path / "normalized" / "2026-09-20" / "summary"
    ant.mkdir(parents=True)
    (ant / "receita_socios.json.gz").write_bytes(b"velho")
    rel, _ = _roda(cat, tmp_path, FakeRunner({"receita_socios": 1}), env={})
    e = _status(rel)["receita_socios"]
    assert rel.ok and e.status == "falha" and "reaproveitado de 2026-09-20" in e.motivo
    assert (tmp_path / "normalized" / "2026-10-18" / "summary" / "receita_socios.json.gz").exists()
    assert not (tmp_path / "receita_socios_last_run.json").exists()      # marcador só após sucesso


def test_retomar_continua_o_que_ja_concluiu(cat, tmp_path):
    _roda(cat, tmp_path, FakeRunner({"anatel_scm": 1}))
    rel, runner = _roda(cat, tmp_path, retomar=True, env={})
    s = _status(rel)
    assert s["lg_ixbr"].status == "retomada"
    assert runner.chamadas.count("anatel_scm") == 1 and "lg_ixbr" not in runner.chamadas


def test_only_executa_so_as_escolhidas_na_ordem(cat, tmp_path):
    rel, runner = _roda(cat, tmp_path, only=["asn_indice", "lg_ixbr"])
    assert runner.chamadas == ["lg_ixbr", "asn_indice"]
    with pytest.raises(KeyError):
        _roda(cat, tmp_path, only=["nao_existe"])


def test_dry_run_nao_executa_nem_grava(cat, tmp_path):
    rel, runner = _roda(cat, tmp_path, dry_run=True)
    assert runner.chamadas == [] and not executor.caminho_relatorio(tmp_path, "2026-10-18").exists()
    assert all(e.status in ("planejada", "delegada_ao_host", "pulada") for e in rel.etapas)


def test_lock_impede_execucao_simultanea_e_ignora_lock_orfao(cat, tmp_path):
    """O lock é um flock: só vale enquanto um processo vivo o segura. Um arquivo deixado por um contêiner morto (pid 1)
    não trava as rodadas seguintes."""
    import fcntl

    lk = tmp_path / "ops" / "arandu.lock"
    lk.parent.mkdir(parents=True)
    fd = os.open(lk, os.O_CREAT | os.O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX)                                   # outra execução viva
    os.write(fd, json.dumps({"pid": 4242, "inicio": "2026-11-10T12:00:00Z"}).encode())
    try:
        with pytest.raises(executor.LockOcupado) as exc:
            _roda(cat, tmp_path)
        assert "4242" in str(exc.value)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    lk.write_text(json.dumps({"pid": 1, "inicio": "2026-11-07T12:00:10Z", "quem": "arandu"}))      # lock órfão: ninguém o segura
    rel, _ = _roda(cat, tmp_path)
    assert rel.ok
    from arandu import lockfile
    assert lockfile.ocupado(lk) is None                                # liberado ao fim da execução


def test_lockfile_ocupado_enxerga_quem_segura_e_ignora_arquivo_ausente(tmp_path):
    from arandu import lockfile

    lk = tmp_path / "x.lock"
    assert lockfile.ocupado(lk) is None
    with lockfile.lock(lk, quem="teste"):
        info = lockfile.ocupado(lk)
        assert info is not None and info["quem"] == "teste" and info["pid"] == os.getpid()
        with pytest.raises(lockfile.LockOcupado):
            with lockfile.lock(lk):
                pass
    assert lockfile.ocupado(lk) is None


def test_somente_se_executou_pula_validacao_do_basemap_sem_build(cat):
    s = cat.steps["host_basemap_validate"]
    assert s.somente_se_executou == ["host_basemap_build"] and s.runner == "host"


# ── status, doctor, gc ─────────────────────────────────────────────────────────

def test_status_acha_ultima_versao_e_frescor(cat, tmp_path):
    for d in ("2026-10-04", "2026-10-11"):
        p = tmp_path / "normalized" / d / "summary"
        p.mkdir(parents=True)
        (p / "registro_br.json.gz").write_bytes(b"")
    linhas = {l["fonte"]: l for l in status.status_das_fontes(cat, tmp_path, "2026-10-13")}
    assert linhas["registro_br"]["as_of"] == "2026-10-11" and linhas["registro_br"]["estado"] == "ok"
    assert linhas["lacnic_delegated"]["estado"] == "ausente"
    assert linhas["curada_cdns"]["estado"] == "curada"
    atrasado = {l["fonte"]: l for l in status.status_das_fontes(cat, tmp_path, "2026-11-30")}
    assert atrasado["registro_br"]["estado"] == "atrasado"


def test_status_mostra_falha_da_ultima_execucao(cat, tmp_path):
    _roda(cat, tmp_path, FakeRunner({"anatel_scm": 1}))
    linhas = {l["fonte"]: l for l in status.status_das_fontes(cat, tmp_path, "2026-10-18")}
    assert linhas["anatel_scm"]["ultima_falha"] == "saída 1"


def test_doctor_reporta_disco_catalogo_e_ultima_execucao(cat, tmp_path):
    _roda(cat, tmp_path, FakeRunner({"registro_br": 1}))
    r = {x["nome"]: x for x in ops.diagnostico(cat, tmp_path, ROOT, "2026-10-18")}
    assert r["disco"]["estado"] in ("ok", "aviso", "erro")
    assert r["catalogo"]["estado"] == "ok" and r["lock"]["estado"] == "ok"
    assert r["ultima_execucao"]["estado"] == "erro" and "registro_br" in r["ultima_execucao"]["detalhe"]


# ── repair ─────────────────────────────────────────────────────────────────────

def test_repair_detecta_etapa_sem_saida_e_inclui_dependentes(cat, tmp_path):
    from arandu import repair

    d = "2026-10-11"
    # tudo presente exceto lacnic_delegated
    for s in cat.steps.values():
        if s.runner != "worker" or s.id == "lacnic_delegated":
            continue
        for sub, pad in repair.saidas_primarias(cat, s):
            alvo = tmp_path / sub / d / re.sub(r"\{[^}]+\}", "x", pad)
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_bytes(b"")
    plano = repair.plano_de_reparo(cat, tmp_path, d)
    assert plano["faltam"] == ["lacnic_delegated"]
    assert plano["reexecutar"][0] == "lacnic_delegated"
    assert "peeringdb_networks" in plano["reexecutar"] and "peeringdb_contacts" in plano["reexecutar"]
    assert "metricas_ixp_asn" in plano["reexecutar"] and "asn_indice" in plano["reexecutar"]   # lacnic alimenta asn_docs
    assert "lg_ixbr" not in plano["reexecutar"]


def test_repair_conhece_todas_as_etapas_de_worker(cat, tmp_path):
    from arandu import repair

    sem_saida = [s.id for s in cat.steps.values() if s.runner == "worker" and not s.so_com_only and not repair.saidas_primarias(cat, s)]
    # etapas sem saída própria declarada: só as que refrescam/são parciais (ex.: bgp_stability, saude_asn é produtos asn_saude)
    from products import passos
    assert set(sem_saida) <= {"bgp_stability", "saude_asn", "snapshot_completo", "history", "ipv4_vigia", "ioda_outages", *passos.ORDEM}, sem_saida     # sem produto próprio: passos do build e fechamento; history grava em data/history/, fora de data/<camada>/<data>
    assert set(repair.etapas_faltantes(cat, tmp_path, "2026-10-11")) == {s.id for s in cat.steps.values()
                                                                        if s.runner == "worker" and not s.so_com_only and s.id not in sem_saida}


# ── tentativas, retomada pelo registro legado, painel e etapas de host ──────────

def test_tentativas_repete_etapa_com_falha_transitoria(cat, tmp_path):
    esperas = []

    class Instavel(FakeRunner):
        def run(self, step, date):
            r = super().run(step, date)
            if step.id == "peeringdb_ixps" and self.chamadas.count("peeringdb_ixps") < 3:
                r.rc, r.motivo = 1, "timeout"
            return r

    runner = Instavel()
    rel = executor.executar(cat, "2026-10-18", tmp_path, runner, only=["peeringdb_ixps"], usar_lock=False,
                            log=lambda *_: None, sleep=esperas.append)
    e = rel.etapas[0]
    assert rel.ok and e.status == "ok" and e.tentativas == 3
    assert runner.chamadas.count("peeringdb_ixps") == 3 and esperas == [60, 60]


def test_tentativas_esgotadas_valem_a_politica_da_etapa(cat, tmp_path):
    runner = FakeRunner({"peeringdb_ixps": 1})
    rel = executor.executar(cat, "2026-10-18", tmp_path, runner, usar_lock=False, log=lambda *_: None, sleep=lambda s: None)
    assert not rel.ok and rel.abortada_em == "peeringdb_ixps"
    assert runner.chamadas.count("peeringdb_ixps") == 3
    assert _status(rel)["peeringdb_ixps"].tentativas == 3


def test_etapa_sem_tentativas_extras_roda_uma_vez(cat, tmp_path):
    runner = FakeRunner({"anatel_scm": 1})
    _roda(cat, tmp_path, runner)
    assert runner.chamadas.count("anatel_scm") == 1


def _primeira(runner):
    """Primeira etapa chamada, sem as que rodam no início por ordem negativa (download das outorgas, listas diárias, CAIDA, IBGE, APNIC Labs, bogons…)."""
    return next(c for c in runner.chamadas if c not in ("apnic_dnssec", "apnic_irov", "bogons", "caida_asrank", "caida_as2org", "abusech", "ioda_outages", "ooni_bloqueios", "caida_asrel", "ibge_censo_pnad", "cetic_tic_domicilios_tabelas", "cetic_tic_provedores_tabelas", "cetic_tic_domicilios_microdados", "ixbr_alice", "ixbr_alice_rotas", "decix_alice", "anatel_rqual", "anatel_reclamacoes", "qualidade", "consumidor_gov", "consumidor", "rs_policy", "route_servers", "cetic", "registrobr_listas", "lacnic_listas", "anatel_outorgas", "anatel_erbs", "anatel_fust", "anatel_multas", "anatel_pdff", "anatel_satelites", "caida_spoofer", "irr_route_objects", "manrs_participantes", "manrs", "regulatorio", "ipv4_vigia", "ipv4_listas", "ipv4_delegated", "ipv4_subasignacao"))


def test_painel_le_o_relatorio_do_arandu(cat, tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("scorecard", ROOT / "scripts" / "scorecard.py")
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    rel, _ = _roda(cat, tmp_path, FakeRunner({"anatel_scm": 1}))
    p = sc.secao_pipeline(tmp_path)
    assert p["executor"] == "arandu" and p["data"] == "2026-10-18"
    assert "anatel_scm" in p["falhas"] and p["etapas"] >= 40


def test_painel_le_so_o_relatorio_do_arandu(tmp_path):
    """O registro de tempos das etapas de host (`AAAA-MM-DD.host.jsonl`) não toma o lugar do relatório do arandu."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("scorecard", ROOT / "scripts" / "scorecard.py")
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    d = tmp_path / "ops" / "runs"
    d.mkdir(parents=True)
    (d / "2026-10-19.json").write_text(json.dumps({"duracao_s": 7, "ok": True, "etapas": [{"id": "lg_ixbr", "status": "ok", "duracao_s": 3}]}))
    (d / "2026-10-19.host.jsonl").write_text(json.dumps({"step": "host_warmup", "duration_s": 5, "status": "ok"}))
    p = sc.secao_pipeline(tmp_path)
    assert p["executor"] == "arandu" and p["data"] == "2026-10-19" and p["mais_lentas"][0]["etapa"] == "lg_ixbr"


def _host_steps(tmp_path, marcador=None, data="2026-10-17"):
    """Executa run_host_steps com `docker compose` e scripts falsos; devolve a saída."""
    import subprocess

    (tmp_path / "scripts").mkdir()
    for nome in ("build-basemap-tiles.sh", "validate-basemap-tiles.sh", "disk-report.sh"):
        (tmp_path / "scripts" / nome).write_text(f'echo "RODOU {nome} $@"\n')
    (tmp_path / "data" / "tiles").mkdir(parents=True)
    if marcador:
        (tmp_path / "data" / "tiles" / "current.json").write_text(json.dumps({"date": marcador}))
    script = f'''
        REPO_DIR="{tmp_path}"; COMPOSE="echo compose"; DATE="{data}"
        log() {{ echo "LOG $*"; }}
        step() {{ local l="$1"; shift; echo "STEP $l"; "$@"; }}
        source "{ROOT}/scripts/host-steps.sh"
        run_host_steps
    '''
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60).stdout


def test_etapas_de_host_basemap_recente_nao_reconstroi(tmp_path):
    out = _host_steps(tmp_path, marcador="2026-10-11")
    assert "STEP host_warmup" in out and "STEP host_disk_report" in out and "RODOU disk-report.sh --date 2026-10-17" in out
    assert "STEP host_basemap_build" not in out and "dentro do limite" in out


def test_etapas_de_host_basemap_velho_ou_ausente_reconstroi_e_valida(tmp_path):
    antigo = tmp_path / "a"; antigo.mkdir()
    out = _host_steps(antigo, marcador="2026-08-01")
    assert "STEP host_basemap_build" in out and "STEP host_basemap_validate" in out
    ausente = tmp_path / "b"; ausente.mkdir()
    assert "STEP host_basemap_build" in _host_steps(ausente)


def test_subprocess_runner_executa_modulo_real_e_devolve_o_codigo_de_saida(tmp_path):
    from arandu.runner import SubprocessRunner
    from core.catalog.schema import Step

    s = Step(id="falso", nome="f", ordem=1, modulo="tests.fakes.step_falso", politica_falha="opcional")
    assert SubprocessRunner({"ARANDU_TESTE_RC": "0"}, python=os.sys.executable).run(s, "2026-10-17").rc == 0
    r = SubprocessRunner({"ARANDU_TESTE_RC": "7"}, python=os.sys.executable).run(s, "2026-10-17")
    assert r.rc == 7 and "7" in r.motivo
    assert SubprocessRunner(python="/caminho/inexistente/python").run(s, "2026-10-17").rc == 127


def test_relatorio_e_legivel_por_outros_usuarios(cat, tmp_path):
    _roda(cat, tmp_path)
    modo = executor.caminho_relatorio(tmp_path, "2026-10-18").stat().st_mode & 0o777
    assert modo == 0o644


# ── scripts/arandu-weekly.sh ────────────────────────────────────────────────────

def _arandu_weekly(tmp_path, rc_arandu=0, compare="off", rpki="off", extra=None):
    import subprocess

    bin_ = tmp_path / "bin"
    bin_.mkdir()
    chamadas = tmp_path / "chamadas.txt"
    (bin_ / "docker").write_text(
        f'#!/usr/bin/env bash\necho "docker $*" >> {chamadas}\n'
        f'case "$*" in *"arandu run --date"*"--retomar"*) exit {rc_arandu};; esac\nexit 0\n')
    (bin_ / "docker").chmod(0o755)
    host = tmp_path / "host.sh"
    host.write_text(f'echo HOST >> {chamadas}\n')
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "MEM_SAMPLE": "off", "DATE": "2026-10-18",
           "ARANDU_COMPARE": compare, "HOST_STEPS": f"bash {host}", "RPKI_AVULSO": rpki, "RPKI_DESTINO": str(tmp_path / "rpki"),
           "ARANDU_DADOS_HOST": str(tmp_path / "data"), **(extra or {})}
    r = subprocess.run(["bash", str(ROOT / "scripts" / "arandu-weekly.sh")], env=env, capture_output=True, text=True, timeout=60)
    linhas = chamadas.read_text().splitlines() if chamadas.exists() else []
    return r, linhas


def test_arandu_weekly_roda_arandu_depois_etapas_de_host(tmp_path):
    r, linhas = _arandu_weekly(tmp_path)
    assert r.returncode == 0
    assert "python -m arandu run --date 2026-10-18 --retomar" in linhas[0]
    assert linhas[1] == "HOST" and len(linhas) == 2                       # sem compare por padrão


def test_arandu_weekly_aborta_sem_etapas_de_host_quando_o_arandu_falha(tmp_path):
    r, linhas = _arandu_weekly(tmp_path, rc_arandu=1)
    assert r.returncode == 1 and "HOST" not in linhas and "etapas de host não executadas" in r.stdout


def test_arandu_weekly_roda_o_rpki_avulso_antes_do_worker_e_segue_se_ele_falha(tmp_path):
    # O docker falso não devolve JSON: o avulso falha, o pipeline avisa e roda o arandu mesmo assim (etapa RPKI opcional).
    r, linhas = _arandu_weekly(tmp_path, rpki="on")
    i_rpki = next(i for i, l in enumerate(linhas) if "--profile rpki run" in l)
    i_arandu = next(i for i, l in enumerate(linhas) if "python -m arandu run --date" in l)
    assert i_rpki < i_arandu and r.returncode == 0
    assert "Routinator avulso falhou" in r.stdout and not (tmp_path / "rpki" / "vrps.json").exists()


def _rpki_avulso(tmp_path, saida_json, rc=0, aceitar=False):
    import subprocess

    bin_ = tmp_path / "bin"
    bin_.mkdir(exist_ok=True)
    (tmp_path / "saida.json").write_text(saida_json)
    (bin_ / "docker").write_text(
        f'#!/usr/bin/env bash\ncase "$*" in *"--profile rpki run"*) cat {tmp_path / "saida.json"}; exit {rc};; esac\nexit 0\n')
    (bin_ / "docker").chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "RPKI_DESTINO": str(tmp_path / "rpki")}
    args = ["bash", str(ROOT / "scripts" / "rpki-avulso.sh")] + (["--aceitar"] if aceitar else [])
    return subprocess.run(args, env=env, capture_output=True, text=True, timeout=60)


_TAS = ("afrinic", "apnic", "arin", "lacnic", "ripe")


def _vrps(n_por_ta=1, tas=_TAS, asn="AS1"):
    roas = [{"asn": asn, "prefix": "10.0.0.0/8", "maxLength": 8, "ta": t} for t in tas for _ in range(n_por_ta)]
    return json.dumps({"metadata": {}, "roas": roas, "aspas": []})


def test_rpki_avulso_recusa_saida_sem_uma_ta_ou_com_queda_grande(tmp_path):
    # 2026-11-19: o snapshot RRDP do RIPE falhou e o Routinator entregou um JSON válido sem nenhum ROA do RIPE.
    destino = tmp_path / "rpki" / "vrps.json"
    assert _rpki_avulso(tmp_path, _vrps(n_por_ta=10)).returncode == 0
    r = _rpki_avulso(tmp_path, _vrps(n_por_ta=12, tas=_TAS[:4], asn="AS2"))
    assert r.returncode == 1 and "sem ROA de: ripe" in r.stdout + r.stderr
    r = _rpki_avulso(tmp_path, _vrps(n_por_ta=8, asn="AS3"))   # 40 de 50: abaixo de 90%
    assert r.returncode == 1 and "menos de 90%" in r.stdout + r.stderr
    d = json.loads(destino.read_text())
    assert d["roas"][0]["asn"] == "AS1" and len(d["roas"]) == 50
    assert _rpki_avulso(tmp_path, _vrps(n_por_ta=9, asn="AS4")).returncode == 0   # 45 de 50: dentro
    assert _rpki_avulso(tmp_path, _vrps(n_por_ta=1, tas=_TAS[:4], asn="AS5"), aceitar=True).returncode == 0
    assert json.loads(destino.read_text())["roas"][0]["asn"] == "AS5"


def test_rpki_avulso_grava_o_json_e_preserva_o_anterior_quando_falha(tmp_path):
    ok = _vrps()
    r = _rpki_avulso(tmp_path, ok)
    destino = tmp_path / "rpki" / "vrps.json"
    assert r.returncode == 0 and json.loads(destino.read_text())["roas"][0]["asn"] == "AS1"
    for saida, rc in (('{"roas": [', 0), (json.dumps({"roas": []}), 0), (ok, 1)):   # truncado, vazio, Routinator com erro
        r = _rpki_avulso(tmp_path, saida, rc)
        assert r.returncode == 1 and json.loads(destino.read_text())["roas"][0]["asn"] == "AS1"
        assert not (tmp_path / "rpki" / "vrps.json.tmp").exists()


def test_arandu_weekly_nao_roda_o_rpki_avulso_fora_da_janela_de_publicacao(tmp_path):
    # A etapa rpki_collector grava em published/ e fica de fora nos dias sem publicação: o Routinator também.
    (tmp_path / "data" / "published" / "2026-10-15").mkdir(parents=True)
    (tmp_path / "data" / "published" / "2026-10-15" / "manifest.json").write_text("{}")
    r, linhas = _arandu_weekly(tmp_path, rpki="on", extra={"ARANDU_MODO": "due"})
    assert not any("--profile rpki run" in l for l in linhas) and "fora da janela de publicação" in r.stdout
    forcado = tmp_path / "forcado"
    forcado.mkdir()
    _, linhas = _arandu_weekly(forcado, rpki="on", extra={"ARANDU_MODO": "due", "ARANDU_PUBLICAR": "1"})
    assert any("--profile rpki run" in l for l in linhas)


def test_arandu_weekly_compare_so_com_a_variavel(tmp_path):
    r, linhas = _arandu_weekly(tmp_path, compare="on")
    assert any("python -m arandu run --compare --date 2026-10-18" in l for l in linhas)


# ── armazém de versões ──────────────────────────────────────────────────

def test_executor_registra_a_versao_da_fonte_depois_da_coleta(cat, tmp_path):
    import gzip

    def cria(step, date):
        if step.id == "registro_br":
            p = tmp_path / "normalized" / date / "summary" / "registro_br.json.gz"
            p.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(p, "wt") as f:
                f.write("{}")

    rel, _ = _roda(cat, tmp_path, FakeRunner(antes=cria), only=["registro_br"])
    e = rel.etapas[0]
    assert e.versoes and e.versoes[0]["fonte"] == "registro_br" and e.versoes[0]["evento"] == "nova"
    from core.store import resolver
    assert resolver(tmp_path, "registro_br", "2026-10-18").as_of == "2026-10-18"
    rel2, _ = _roda(cat, tmp_path, FakeRunner(), only=["registro_br"])          # mesma coleta de novo: confirma, não duplica
    assert rel2.etapas[0].versoes[0]["evento"] == "confirmada"


def test_falha_no_armazem_nao_derruba_a_etapa(cat, tmp_path, monkeypatch):
    import core.store.fontes as f

    monkeypatch.setattr(f, "registrar", lambda *a, **k: (_ for _ in ()).throw(OSError("disco cheio")))
    def cria(step, date):
        p = tmp_path / "normalized" / date / "summary" / "registro_br.json.gz"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    mensagens = []
    rel = executor.executar(cat, "2026-10-18", tmp_path, FakeRunner(antes=cria), only=["registro_br"], usar_lock=False,
                            log=mensagens.append, sleep=lambda s: None)
    assert rel.ok and rel.etapas[0].status == "ok" and rel.etapas[0].versoes is None
    assert any("não registrou a versão" in m for m in mensagens)


# ── cadência (--due) e composição pelo armazém ──────────────────────────

def _versao_antiga(tmp_path, fonte, dia, arquivo_rel, coletado):
    """Registra no armazém uma versão antiga da fonte, como se tivesse sido coletada em `coletado`."""
    from core.store import registrar

    p = tmp_path / "ori" / f"{fonte}-{dia}"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"conteudo {fonte} {dia}")
    return registrar(tmp_path, fonte, dia, {arquivo_rel: p}, coletado_em=coletado, disponivel_desde=coletado[:10])[0]


def test_due_pula_fonte_semanal_coletada_ha_poucos_dias_e_restaura_a_versao(cat, tmp_path):
    _versao_antiga(tmp_path, "asn_names", "2026-10-15", "normalized/summary/asn_names.json.gz", "2026-10-15T05:00:00Z")
    rel, runner = _roda(cat, tmp_path, FakeRunner(), due=True, env={})
    e = _status(rel)["asn_names"]
    assert e.status == "pulada" and "dentro da cadência semanal" in e.motivo
    assert e.reutilizadas[0]["as_of"] == "2026-10-15"
    assert "asn_names" not in runner.chamadas
    assert (tmp_path / "normalized" / "2026-10-18" / "summary" / "asn_names.json.gz").read_text() == "conteudo asn_names 2026-10-15"


def test_due_coleta_quando_a_cadencia_venceu(cat, tmp_path):
    _versao_antiga(tmp_path, "asn_names", "2026-10-10", "normalized/summary/asn_names.json.gz", "2026-10-10T05:00:00Z")
    rel, runner = _roda(cat, tmp_path, FakeRunner(), due=True, env={})
    assert "asn_names" in runner.chamadas and _status(rel)["asn_names"].status == "ok"


def test_due_sem_nada_no_armazem_coleta(cat, tmp_path):
    rel, runner = _roda(cat, tmp_path, FakeRunner(), due=True, env={})
    assert "registro_br" in runner.chamadas


def test_due_nao_pula_analises_e_produtos(cat, tmp_path):
    rel, runner = _roda(cat, tmp_path, FakeRunner(), due=True, env={})
    for etapa in ("bgp_ixp", "metricas_ixp_asn", "asn_indice", "saude_asn"):
        assert etapa in runner.chamadas


def test_due_com_only_ignora_a_cadencia(cat, tmp_path):
    _versao_antiga(tmp_path, "registro_br", "2026-10-17", "normalized/summary/registro_br.json.gz", "2026-10-17T05:00:00Z")
    rel, runner = _roda(cat, tmp_path, FakeRunner(), due=True, only=["registro_br"], env={})
    assert runner.chamadas == ["registro_br"]


def test_due_nao_roda_fonte_sob_demanda_nem_manual(cat, tmp_path):
    import copy

    c2 = copy.deepcopy(cat)
    c2.sources["registro_br"].cadencia.coleta_atual = "sob_demanda"
    _versao_antiga(tmp_path, "registro_br", "2026-09-01", "normalized/summary/registro_br.json.gz", "2026-09-01T05:00:00Z")
    rel, runner = _roda(c2, tmp_path, FakeRunner(), due=True, env={})
    assert "registro_br" not in runner.chamadas and _status(rel)["registro_br"].status == "pulada"


def test_sem_due_tudo_roda_como_antes(cat, tmp_path):
    _versao_antiga(tmp_path, "registro_br", "2026-10-17", "normalized/summary/registro_br.json.gz", "2026-10-17T05:00:00Z")
    rel, runner = _roda(cat, tmp_path, FakeRunner(), env={})
    assert "registro_br" in runner.chamadas


def test_due_fonte_mensal_usa_o_armazem_no_lugar_do_marcador(cat, tmp_path):
    """Sócios: coletados há 13 dias → reaproveita a versão; o marcador em shell deixa de mandar."""
    _versao_antiga(tmp_path, "receita_socios", "2026-09", "normalized/summary/receita_socios.json.gz", "2026-10-05T05:00:00Z")
    rel, runner = _roda(cat, tmp_path, FakeRunner(), due=True, env={})
    e = _status(rel)["receita_socios"]
    assert e.status == "pulada" and e.reutilizadas[0]["as_of"] == "2026-09" and "receita_socios" not in runner.chamadas


def test_status_usa_o_armazem_e_mede_a_idade_pela_ultima_coleta(cat, tmp_path):
    """SICI: o mês de referência (as_of 2026-08) pode ser antigo sem a fonte estar atrasada."""
    _versao_antiga(tmp_path, "anatel_sici", "2026-08", "normalized/summary/sici_acessos.json.gz", "2026-10-15T05:00:00Z")
    linhas = {l["fonte"]: l for l in status.status_das_fontes(cat, tmp_path, "2026-10-18")}
    l = linhas["anatel_sici"]
    assert l["origem_dados"] == "armazem" and l["as_of"] == "2026-08" and l["idade_dias"] == 3 and l["estado"] == "ok"
    atrasado = {l["fonte"]: l for l in status.status_das_fontes(cat, tmp_path, "2026-12-30")}["anatel_sici"]
    assert atrasado["estado"] == "atrasado"


def test_pin_sources_restaura_a_versao_do_manifesto_e_so_roda_o_que_nao_e_fonte(cat, tmp_path):
    antiga = _versao_antiga(tmp_path, "registro_br", "2026-10-10", "normalized/summary/registro_br.json.gz", "2026-10-10T05:00:00Z")
    _versao_antiga(tmp_path, "registro_br", "2026-10-17", "normalized/summary/registro_br.json.gz", "2026-10-17T05:00:00Z")
    man = tmp_path / "published" / "2026-10-18" / "manifest.json"
    man.parent.mkdir(parents=True)
    man.write_text(json.dumps({"sources": [{"id": "registro_br", "versao": antiga.nome, "origem": "armazem"},
                                           {"id": "anatel_scm", "versao": None, "origem": "legado"}]}))
    rel, runner = _roda(cat, tmp_path, FakeRunner(), pin_sources=True)
    assert "registro_br" not in runner.chamadas and "anatel_scm" not in runner.chamadas
    assert {"bgp_ixp", "metricas_ixp_asn", "asn_indice"} <= set(runner.chamadas)
    assert _status(rel)["registro_br"].status == "pulada" and _status(rel)["registro_br"].reutilizadas[0]["versao"] == "2026-10-10"
    assert (tmp_path / "normalized" / "2026-10-18" / "summary" / "registro_br.json.gz").read_text() == "conteudo registro_br 2026-10-10"


def test_pin_sources_com_versao_ausente_no_armazem_falha_a_etapa(cat, tmp_path):
    man = tmp_path / "published" / "2026-10-18" / "manifest.json"
    man.parent.mkdir(parents=True)
    man.write_text(json.dumps({"sources": [{"id": "registro_br", "versao": "2026-01-01", "origem": "armazem"}]}))
    rel, runner = _roda(cat, tmp_path, FakeRunner(), pin_sources=True)
    assert not rel.ok and rel.abortada_em == "registro_br" and "2026-01-01" in (_status(rel)["registro_br"].motivo or "")


def test_due_coleta_o_lg_se_a_versao_do_armazem_nao_tem_o_bruto(cat, tmp_path):
    """Versão registrada só com o manifesto (antes do bruto versionado) não restaura o que o `bgp_ixp` lê: o lg_ixbr coleta."""
    assert cat.sources["lg_ixbr"].armazem.sempre_coletar is False
    _versao_antiga(tmp_path, "lg_ixbr", "2026-10-18", "raw/collection_manifest.json", "2026-10-18T05:00:00Z")
    rel, runner = _roda(cat, tmp_path, FakeRunner(), due=True, env={})
    assert "lg_ixbr" in runner.chamadas and "registro_br" in runner.chamadas


def test_due_reutiliza_o_lg_quando_a_versao_tem_o_bruto(cat, tmp_path):
    from core.store import registrar
    for rel_ in ("raw/collection_manifest.json", "raw/sp/bgp-v4-sp-2026-10-18.txt.gz", "raw/sp/bgp-v6-sp-2026-10-18.txt.gz"):
        f = tmp_path / "_src" / rel_
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"x")
        arquivos = locals().setdefault("arquivos", {})
        arquivos[rel_] = f
    registrar(tmp_path, "lg_ixbr", "2026-10-18", arquivos, origem="teste")
    from arandu import executor as ex
    assert ex.versao_incompleta(cat, tmp_path, "lg_ixbr") is None
    assert ex.versao_incompleta(cat, tmp_path, "ixbr_api") is None                       # sem registro: nada a dizer


def test_relatorio_de_cada_execucao_fica_no_historico(cat, tmp_path):
    _roda(cat, tmp_path, FakeRunner({"anatel_scm": 1}))
    _roda(cat, tmp_path, FakeRunner())
    hist = sorted((tmp_path / "ops" / "runs" / "history").glob("2026-10-18T*.json"))
    assert len(hist) >= 1 and all(json.loads(h.read_text())["date"] == "2026-10-18" for h in hist)
    assert (tmp_path / "ops" / "runs" / "2026-10-18.json").exists()          # o do dia continua sendo o último


def test_retomar_refaz_o_que_depende_de_uma_etapa_executada_de_novo(cat, tmp_path):
    """Fontes recoletadas depois que o `snapshot_completo` já rodou deixariam o snapshot publicado
    inconsistente com as entradas. Etapa concluída antes é refeita se alguma dependência rodou de novo."""
    _roda(cat, tmp_path, FakeRunner())                                       # tudo ok no dia
    rel_json = executor.caminho_relatorio(tmp_path, "2026-10-18")
    d = json.loads(rel_json.read_text())
    for e in d["etapas"]:                                                    # simula: `registro_br` não tinha concluído
        if e["id"] == "registro_br":
            e["status"] = "pulada"
    rel_json.write_text(json.dumps(d))
    rel, runner = _roda(cat, tmp_path, FakeRunner(), retomar=True, env={})
    assert "registro_br" in runner.chamadas
    for dependente in ("rdap", "metricas_ixp_asn", "asn_indice"):
        assert dependente in runner.chamadas, dependente                     # refeitas
    assert _status(rel)["lg_ixbr"].status == "retomada"                      # não depende de registro_br
    assert "refeita porque registro_br" in _status(rel)["metricas_ixp_asn"].motivo or _status(rel)["metricas_ixp_asn"].status == "ok"


def test_saida_por_sinal_informa_o_nome_do_sinal():
    from arandu.runner import _motivo_da_saida
    assert _motivo_da_saida(-13) == "saída -13 (sinal SIGPIPE)"
    assert _motivo_da_saida(-9) == "saída -9 (sinal SIGKILL)"
    assert _motivo_da_saida(2) == "saída 2"


def test_listas_diarias_rodam_antes_do_p6_para_entrar_no_manifesto_do_dia(cat):
    """`registrobr_listas` e `lacnic_listas` rodam antes do `snapshot_completo`; depois dele, `sources[]` do manifesto as mostraria 'ausente' no dia da coleta."""
    ordem = ordem_de_execucao(cat)
    for s in ("registrobr_listas", "lacnic_listas"):
        assert ordem.index(s) < ordem.index("snapshot_completo"), s


def test_etapa_manual_so_roda_com_only(cat, tmp_path):
    """O backfill do LACNIC (`so_com_only`) nunca entra no pipeline normal, nem com --retomar."""
    rel, runner = _roda(cat, tmp_path, FakeRunner())
    assert "lacnic_historico" not in runner.chamadas and _status(rel)["lacnic_historico"].status == "pulada"
    rel2, runner2 = _roda(cat, tmp_path, FakeRunner(), only=["lacnic_historico"])
    assert runner2.chamadas == ["lacnic_historico"]


def test_compare_restaura_o_fragmento_relacoes_do_publicado(tmp_path):
    """O ARC não roda no compare; o fragmento do publicado volta ao work dir sempre que o `base` regravado o apagar."""
    from arandu.compare import restaurar_relacoes

    data, work = tmp_path / "data", tmp_path / "work"
    frag = data / "build" / "2026-10-26" / "fragments" / "asn" / "relacoes.jsonl.gz"
    frag.parent.mkdir(parents=True)
    frag.write_bytes(b"x")
    restaurar_relacoes(data, work, "2026-10-26")
    copia = work / "build" / "2026-10-26" / "fragments" / "asn" / "relacoes.jsonl.gz"
    assert copia.read_bytes() == b"x"
    copia.unlink()                                   # o `base` regravado apaga os derivados
    restaurar_relacoes(data, work, "2026-10-26")
    assert copia.exists()
    restaurar_relacoes(data, work, "2026-10-27")     # data sem fragmento: nada a fazer
    assert not (work / "build" / "2026-10-27").exists()


# ── janela de publicação: coleta por fonte todo dia, snapshot só a cada N dias ─────────────

def _publicado(tmp_path, dia):
    d = tmp_path / "published" / dia
    d.mkdir(parents=True)
    (d / "manifest.json").write_text("{}")


def test_publicacao_intervalo_vem_do_ambiente_e_o_padrao_e_sete():
    from arandu import publicacao

    assert publicacao.intervalo_dias({}) == 7
    assert publicacao.intervalo_dias({"ARANDU_PUBLICACAO_DIAS": "14"}) == 14
    assert publicacao.intervalo_dias({"ARANDU_PUBLICACAO_DIAS": "0"}) == 0
    assert publicacao.intervalo_dias({"ARANDU_PUBLICACAO_DIAS": "abc"}) == 7


def test_publicacao_conta_so_pastas_com_manifest_e_anteriores_a_data(tmp_path):
    from arandu import publicacao

    _publicado(tmp_path, "2026-10-04")
    (tmp_path / "published" / "2026-10-11").mkdir()           # sem manifest.json: não é snapshot
    _publicado(tmp_path, "2026-10-18")                        # a própria data não conta como "anterior"
    assert publicacao.ultimo_publicado_antes(tmp_path, "2026-10-18") == "2026-10-04"
    assert publicacao.ultimo_publicado_antes(tmp_path / "nada", "2026-10-18") is None


def test_due_dentro_da_janela_so_coleta_e_nao_publica(cat, tmp_path):
    _publicado(tmp_path, "2026-10-15")                        # 3 dias antes de 2026-10-18
    rel, runner = _roda(cat, tmp_path, FakeRunner(), due=True, env={})
    st = _status(rel)
    for etapa in ("bgp_ixp", "metricas_ixp_asn", "asn_indice", "saude_asn"):
        assert etapa not in runner.chamadas
        assert st[etapa].status == "pulada" and "fora da janela de publicação" in st[etapa].motivo
    assert "registro_br" in runner.chamadas                    # a coleta por fonte continua pela cadência dela


def test_due_depois_do_intervalo_publica(cat, tmp_path):
    _publicado(tmp_path, "2026-10-11")                        # 7 dias antes
    rel, runner = _roda(cat, tmp_path, FakeRunner(), due=True, env={})
    for etapa in ("bgp_ixp", "metricas_ixp_asn", "asn_indice", "saude_asn"):
        assert etapa in runner.chamadas


def test_due_retomar_a_propria_data_de_publicacao_continua_na_janela(cat, tmp_path):
    _publicado(tmp_path, "2026-10-11")
    _publicado(tmp_path, "2026-10-18")                        # publicação do dia já começou (falhou no meio)
    rel, runner = _roda(cat, tmp_path, FakeRunner(), due=True, env={})
    assert "metricas_ixp_asn" in runner.chamadas


def test_due_publicar_forca_a_janela(cat, tmp_path):
    _publicado(tmp_path, "2026-10-17")
    rel, runner = _roda(cat, tmp_path, FakeRunner(), due=True, publicar=True, env={})
    assert "metricas_ixp_asn" in runner.chamadas


def test_due_intervalo_um_publica_a_cada_execucao(cat, tmp_path):
    _publicado(tmp_path, "2026-10-17")
    rel, runner = _roda(cat, tmp_path, FakeRunner(), due=True, env={"ARANDU_PUBLICACAO_DIAS": "1"})
    assert "metricas_ixp_asn" in runner.chamadas


def test_sem_due_a_janela_de_publicacao_nao_se_aplica(cat, tmp_path):
    _publicado(tmp_path, "2026-10-17")
    rel, runner = _roda(cat, tmp_path, FakeRunner(), env={})
    assert "metricas_ixp_asn" in runner.chamadas


def test_due_com_only_ignora_a_janela(cat, tmp_path):
    _publicado(tmp_path, "2026-10-17")
    rel, runner = _roda(cat, tmp_path, FakeRunner(), due=True, only=["metricas_ixp_asn"], env={})
    assert runner.chamadas == ["metricas_ixp_asn"]


def test_janela_tambem_prende_a_coleta_derivada_que_le_etapa_de_produto(cat, tmp_path):
    """`global_prefix_geo` e `bgp_stability_deep_coleta` leem a saída de etapas sem fonte: fora da janela essa entrada não existe.
    O `rpki_collector` grava direto em published/<data>/: fora da janela deixaria uma pasta sem manifesto."""
    _publicado(tmp_path, "2026-10-15")
    rel, runner = _roda(cat, tmp_path, FakeRunner(), due=True, env={})
    st = _status(rel)
    for etapa in ("global_prefix_geo", "bgp_stability_deep_coleta", "rpki_collector"):
        assert etapa not in runner.chamadas
        assert st[etapa].status == "pulada" and "fora da janela de publicação" in st[etapa].motivo
