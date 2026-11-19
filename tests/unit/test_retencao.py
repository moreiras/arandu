# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — retenção: perfis, pisos em código, `--dry-run` obrigatório e remoção segura."""
import json
from pathlib import Path

import pytest

from arandu import cli, retencao
from core.store import registrar

ROOT = Path(__file__).resolve().parents[2]


def _dados(tmp_path, datas, camadas=("published", "normalized", "raw")):
    for d in datas:
        for c in camadas:
            p = tmp_path / c / d
            p.mkdir(parents=True)
            (p / "a.json").write_text("x" * 10)


def _perfil(tmp_path, texto):
    f = tmp_path / "ret.yaml"
    f.write_text(texto)
    return f


DEV = """
perfil_padrao: dev
perfis:
  dev:
    published: {tudo: true}
    normalized: {datas: 2}
    raw: {datas: 2}
    armazem: {versoes: 2}
    protegidas: ['2026-10-11']
  prod:
    published: {semanas: 12, um_por_mes: true}
    normalized: {semanas: 52}
    raw: {datas: 4}
    armazem: {versoes: 4}
"""
DATAS = ["2026-05-03", "2026-05-31", "2026-06-07", "2026-06-28", "2026-08-02", "2026-09-06", "2026-09-27",
         "2026-10-04", "2026-10-11", "2026-10-17", "2026-10-19"]


def test_catalogo_de_retencao_carrega_os_dois_perfis():
    for nome in ("desenvolvimento", "producao"):
        p = retencao.carregar(ROOT / "catalog" / "retencao.yaml", nome)
        assert set(p.camadas) == {"published", "normalized", "raw", "build"}
    dev = retencao.carregar(ROOT / "catalog" / "retencao.yaml", "desenvolvimento")
    assert dev.camadas["published"].tudo and dev.camadas["raw"].datas == 2 and "2026-10-11" in dev.protegidas


def test_perfil_inexistente_ou_incompleto_falha_alto(tmp_path):
    f = _perfil(tmp_path, DEV)
    with pytest.raises(ValueError, match="não existe"):
        retencao.carregar(f, "outro")
    with pytest.raises(ValueError, match="falta a camada"):
        retencao.carregar(_perfil(tmp_path, "perfis: {x: {published: {tudo: true}}}\nperfil_padrao: x\n"), "x")


def test_desenvolvimento_guarda_published_e_so_as_2_datas_de_raw_e_normalized(tmp_path):
    _dados(tmp_path, DATAS)
    p = retencao.plano(tmp_path, "2026-10-19", retencao.carregar(_perfil(tmp_path, DEV), "dev"))
    assert not [i for i in p["itens"] if i["camada"] == "published"]
    for c in ("raw", "normalized"):
        sai = {i["item"] for i in p["itens"] if i["camada"] == c}
        assert sai == set(DATAS) - {"2026-10-19", "2026-10-17", "2026-10-11"}      # 2 recentes + a protegida do replay
    assert {"camada": "raw", "item": "2026-10-11", "motivo": "protegida"} in p["seguradas_pelos_pisos"]


def test_producao_12_semanas_e_um_por_mes(tmp_path):
    _dados(tmp_path, DATAS, camadas=("published",))
    ff = _perfil(tmp_path, DEV.replace("raw: {datas: 2}", "raw: {datas: 2}"))
    p = retencao.plano(tmp_path, "2026-10-13", retencao.carregar(ff, "prod"))
    sai = {i["item"] for i in p["itens"] if i["camada"] == "published"}
    # limite = 2026-07-21; mantém ≥ limite, o mais recente de cada mês e os 4 mais recentes (piso)
    assert sai == {"2026-05-03", "2026-06-07"}


def test_piso_do_codigo_vence_politica_errada(tmp_path):
    """Um perfil que manda guardar 0 datas ainda deixa as 2 mais recentes de raw e normalized e as 4 de published."""
    _dados(tmp_path, DATAS)
    zero = """
perfil_padrao: z
perfis:
  z:
    published: {datas: 0}
    normalized: {datas: 0}
    raw: {datas: 0}
    armazem: {versoes: 0}
"""
    p = retencao.plano(tmp_path, "2026-10-19", retencao.carregar(_perfil(tmp_path, zero), "z"))
    por = lambda c: {i["item"] for i in p["itens"] if i["camada"] == c}
    assert set(DATAS) - por("raw") == {"2026-10-19", "2026-10-17"}
    assert set(DATAS) - por("published") == set(sorted(DATAS)[-4:])
    assert any(s["motivo"] == "recente" for s in p["seguradas_pelos_pisos"])


def test_data_do_dia_nunca_sai(tmp_path):
    _dados(tmp_path, ["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04"], camadas=("raw",))
    p = retencao.plano(tmp_path, "2026-10-01", retencao.carregar(_perfil(tmp_path, DEV), "dev"))
    assert "2026-10-01" not in {i["item"] for i in p["itens"]}
    assert {"camada": "raw", "item": "2026-10-01", "motivo": "data do dia"} in p["seguradas_pelos_pisos"]


def _versao(tmp_path, fonte, as_of, conteudo):
    f = tmp_path / "tmp" / f"{fonte}-{as_of}.json"
    f.parent.mkdir(exist_ok=True)
    f.write_text(json.dumps({"v": conteudo}))
    return registrar(tmp_path, fonte, as_of, {"x.json": f})


def test_armazem_guarda_referenciadas_e_a_ultima(tmp_path):
    for i, d in enumerate(["2026-09-01", "2026-09-08", "2026-09-15", "2026-09-22"]):
        _versao(tmp_path, "f", d, i)
    _dados(tmp_path, ["2026-09-08"], camadas=("published",))
    (tmp_path / "published" / "2026-09-08" / "manifest.json").write_text(
        json.dumps({"sources": [{"id": "f", "versao": "2026-09-01"}]}))
    p = retencao.plano(tmp_path, "2026-09-22", retencao.carregar(_perfil(tmp_path, DEV), "dev"))
    sai = {i["item"] for i in p["itens"] if i["camada"] == "armazem"}
    assert sai == {"f/2026-09-08"}      # 2 últimas ficam (piso); 09-01 é citada por um published
    assert {"camada": "armazem", "item": "f/2026-09-01", "motivo": "referenciada por um published"} in p["seguradas_pelos_pisos"]


def test_aplicar_exige_dry_run_antes_e_recusa_com_lock(tmp_path):
    _dados(tmp_path, DATAS, camadas=("raw",))
    p = retencao.plano(tmp_path, "2026-10-19", retencao.carregar(_perfil(tmp_path, DEV), "dev"))
    with pytest.raises(RuntimeError, match="dry-run"):
        retencao.aplicar(tmp_path, p)
    retencao.registrar_dry_run(tmp_path, p)
    with pytest.raises(RuntimeError, match="em andamento"):
        retencao.aplicar(tmp_path, p, lock_ativo=True)
    assert (tmp_path / "raw" / "2026-05-03").exists()


def test_aplicar_remove_so_o_planejado_e_registra(tmp_path):
    _dados(tmp_path, DATAS, camadas=("raw",))
    p = retencao.plano(tmp_path, "2026-10-19", retencao.carregar(_perfil(tmp_path, DEV), "dev"))
    retencao.registrar_dry_run(tmp_path, p)
    rel = retencao.aplicar(tmp_path, p)
    restam = {d.name for d in (tmp_path / "raw").iterdir()}
    assert restam == {"2026-10-19", "2026-10-17", "2026-10-11"} and not rel["falhas"]
    assert json.loads((tmp_path / "ops" / "gc" / "2026-10-19.json").read_text())["liberados_bytes"] == 10 * 8


def test_aplicar_nao_segue_symlink_nem_caminho_forjado(tmp_path):
    _dados(tmp_path, DATAS, camadas=("raw",))
    fora = tmp_path / "fora"
    fora.mkdir()
    (fora / "importante").write_text("x")
    p = retencao.plano(tmp_path, "2026-10-19", retencao.carregar(_perfil(tmp_path, DEV), "dev"))
    p["itens"].append({"camada": "raw", "item": "2026-05-03", "bytes": 0, "caminho": str(fora)})    # caminho forjado
    retencao.registrar_dry_run(tmp_path, p)
    rel = retencao.aplicar(tmp_path, p)
    assert (fora / "importante").exists() and any("fora do esperado" in f["erro"] for f in rel["falhas"])


def test_cli_gc_exige_dry_run_ou_apply(tmp_path, capsys):
    assert cli.main(["gc", "--data-dir", str(tmp_path)]) == 2
    _dados(tmp_path, DATAS, camadas=("raw",))
    assert cli.main(["gc", "--data-dir", str(tmp_path), "--date", "2026-10-19", "--apply"]) == 2     # sem dry-run antes
    assert (tmp_path / "raw" / "2026-05-03").exists()
    assert cli.main(["gc", "--data-dir", str(tmp_path), "--date", "2026-10-19", "--dry-run"]) == 0
    assert "mantida pelo piso do código" in capsys.readouterr().out
    assert cli.main(["gc", "--data-dir", str(tmp_path), "--date", "2026-10-19", "--apply"]) == 0
    assert not (tmp_path / "raw" / "2026-05-03").exists() and (tmp_path / "raw" / "2026-10-11").exists()


# ── `rdap`: tiles, bloqueio por disco, doctor ─────────────────────────────────────

def test_tiles_guardam_a_atual_e_a_anterior(tmp_path):
    for d in ("2026-08-01", "2026-09-07", "2026-10-11", "2026-10-18"):
        (tmp_path / "tiles" / d).mkdir(parents=True)
        (tmp_path / "tiles" / d / "basemap.pmtiles").write_text("x")
    (tmp_path / "tiles" / "_cache").mkdir()
    (tmp_path / "tiles" / "current.json").write_text('{"date": "2026-10-11"}')
    p = retencao.plano(tmp_path, "2026-10-19", retencao.carregar(_perfil(tmp_path, DEV), "dev"))
    assert {i["item"] for i in p["itens"] if i["camada"] == "tiles"} == {"2026-08-01", "2026-09-07"}
    mot = {s["item"]: s["motivo"] for s in p["seguradas_pelos_pisos"] if s["camada"] == "tiles"}
    assert mot == {"2026-10-11": "versão atual", "2026-10-18": "versão anterior"}


def test_coleta_pesada_e_bloqueada_com_disco_acima_do_limite(tmp_path, monkeypatch):
    monkeypatch.delenv("ARANDU_BLOQUEIO_DISCO_PCT", raising=False)
    import shutil
    from collections import namedtuple
    from arandu import executor
    from core.catalog.loader import load_catalog

    cat = load_catalog(ROOT / "catalog")
    pesadas = {s.id for s in cat.steps.values() if s.pesada}
    assert pesadas == {"fulltable_routeviews", "bgp_updates_routeviews", "bgp_stability_deep_coleta"}
    DU = namedtuple("DU", "total used free")
    monkeypatch.setattr(shutil, "disk_usage", lambda p: DU(100, 90, 10))
    assert "bloqueada" in executor.bloqueada_por_disco(cat.steps["fulltable_routeviews"], tmp_path)
    assert executor.bloqueada_por_disco(cat.steps["registro_br"], tmp_path) is None      # leve: segue
    monkeypatch.setattr(shutil, "disk_usage", lambda p: DU(100, 50, 50))
    assert executor.bloqueada_por_disco(cat.steps["fulltable_routeviews"], tmp_path) is None


def test_etapa_critica_pesada_aborta_com_disco_cheio_sem_rodar_nem_repetir(tmp_path, monkeypatch):
    monkeypatch.delenv("ARANDU_BLOQUEIO_DISCO_PCT", raising=False)
    import shutil
    from collections import namedtuple
    from arandu import executor
    from core.catalog.loader import load_catalog

    DU = namedtuple("DU", "total used free")
    monkeypatch.setattr(shutil, "disk_usage", lambda p: DU(100, 90, 10))
    chamadas = []

    class R:
        def run(self, step, date):
            chamadas.append(step.id)
            from arandu.runner import Resultado
            return Resultado(0, None)

    cat = load_catalog(ROOT / "catalog")
    rel = executor.executar(cat, "2026-10-19", tmp_path, R(), only=["fulltable_routeviews"], usar_lock=False,
                            gravar_relatorio=False, sleep=lambda s: None, log=lambda m: None)
    assert chamadas == [] and rel.abortada_em == "fulltable_routeviews"
    e = next(x for x in rel.etapas if x.id == "fulltable_routeviews")
    assert e.status == "falha" and "bloqueada" in e.motivo and e.tentativas is None


def test_doctor_avisa_espaco_para_reconstruir_o_basemap(tmp_path):
    from arandu import ops
    from core.catalog.loader import load_catalog

    (tmp_path / "tiles" / "2026-10-11").mkdir(parents=True)
    (tmp_path / "tiles" / "2026-10-11" / "basemap.pmtiles").write_bytes(b"x" * 1024)
    (tmp_path / "tiles" / "current.json").write_text('{"date": "2026-10-11"}')
    r = {x["nome"]: x for x in ops.diagnostico(load_catalog(ROOT / "catalog"), tmp_path, ROOT, "2026-10-19")}
    assert r["basemap"]["estado"] == "ok" and "2×" in r["basemap"]["detalhe"]


def test_gc_nao_toca_na_camada_de_historico(tmp_path):
    """data/history/ é derivada e pequena, com retenção indefinida como o publicado: o plano do gc nunca a lista."""
    _dados(tmp_path, DATAS)
    for d in DATAS:
        h = tmp_path / "history" / "weekly" / d
        h.mkdir(parents=True)
        (h / "asn.jsonl.gz").write_text("x")
    p = retencao.plano(tmp_path, "2026-10-19", retencao.carregar(_perfil(tmp_path, DEV), "prod"))
    assert p["itens"], "o perfil de produção deveria remover algo (senão o teste não prova nada)"
    assert not [i for i in p["itens"] if "history" in json.dumps(i)]
