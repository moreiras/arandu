# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T2 — armazém de versões sobre o dataset sintético: composição, fidelidade, cadências e frescor."""
import filecmp
import json
import shutil
from pathlib import Path

import pytest

from arandu import executor
from arandu.runner import FakeRunner
from core.catalog.loader import load_catalog
from core.store import compor_fontes, listar, materializar, registrar_da_fonte, resolver
from tests.synth.world import T0, T1

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def cat():
    return load_catalog(ROOT / "catalog")


@pytest.fixture()
def base(pipeline, tmp_path):
    """Cópia do dataset sintético já processado (published + normalized), com o armazém vazio."""
    src, _ = pipeline
    dst = tmp_path / "data"
    for sub in ("published", "normalized"):
        shutil.copytree(src / sub, dst / sub)
    return dst


def _registrar_todas(cat, base, date):
    feitos = {}
    for s in cat.sources.values():
        r = registrar_da_fonte(cat, base, s.id, date, pipeline_version="t7")
        if r:
            feitos[s.id] = r[0]
    return feitos


def test_toda_fonte_com_arquivos_vira_versao_e_a_restauracao_e_identica(cat, base, tmp_path):
    feitas = _registrar_todas(cat, base, T1)
    assert {"registro_br", "anatel_scm", "anatel_sici", "peeringdb_networks", "receita_socios"} <= set(feitas)
    destino = tmp_path / "restaurado"
    for fid, v in feitas.items():
        materializar(destino, v, T1)
        for rel in v.arquivos:
            tipo, _, resto = rel.partition("/")
            original = base / tipo / T1 / resto
            assert filecmp.cmp(original, destino / tipo / T1 / resto, shallow=False), (fid, rel)


def test_composicao_duas_fontes_com_cadencias_diferentes_e_uma_atrasada(cat, base):
    """60 dias depois da coleta do T0: Registro.br (semanal) reconfirmado há 3 dias → ok; sócios (mensal, limite 45 d)
    reconfirmados há 20 dias → ok; anatel_scm (semanal) nunca mais coletada → atrasada."""
    _registrar_todas(cat, base, T0)
    import core.store.versions as vs

    d = "2026-11-12"
    for fid, quando in (("registro_br", "2026-11-09"), ("receita_socios", "2026-10-23")):
        vs._log(base, fid, "confirmada", listar(base, fid)[-1], quando)
    fontes = {f["id"]: f for f in compor_fontes(cat, base, d)}
    assert fontes["registro_br"]["origem"] == "armazem" and fontes["registro_br"]["frescor"] == "ok"
    assert fontes["receita_socios"]["frescor"] == "ok"
    assert fontes["anatel_scm"]["origem"] == "armazem" and fontes["anatel_scm"]["frescor"] == "atrasado"
    # FONT-E4: a data da verificação (em que o frescor foi medido) e o limite vão junto, para a tela dizer "atrasada (limite N dias)"
    assert fontes["registro_br"]["verificado_em"] == "2026-11-09" and fontes["registro_br"]["limite_dias"] == 8
    assert fontes["anatel_scm"]["limite_dias"] is not None and fontes["anatel_scm"]["verificado_em"] <= d


def test_fonte_sem_versao_cai_no_legado_e_sem_arquivos_e_ausente(cat, base):
    fontes = {f["id"]: f for f in compor_fontes(cat, base, T1)}
    assert fontes["registro_br"]["origem"] == "legado" and fontes["registro_br"]["legado"] is True
    assert fontes["bgp_stability_deep"]["origem"] == "ausente" and fontes["bgp_stability_deep"]["frescor"] == "ausente"
    assert fontes["bgp_stability_deep"]["ativa"] is True and "verificado_em" not in fontes["bgp_stability_deep"]       # FONT-E3: ativa sem versão
    inativas = [s.id for s in cat.sources.values() if not s.ativa and s.tipo != "curada" and s.cadencia.coleta_atual != "manual"]
    assert inativas and all(fontes[i]["ativa"] is False for i in inativas)                                                 # desativada se distingue de ausente


def test_manifesto_do_pipeline_traz_layout_version_e_sources(pipeline):
    src, _ = pipeline
    m = json.loads((src / "published" / T1 / "manifest.json").read_text())
    assert m["layout_version"] == 1 and isinstance(m["sources"], list)
    por_id = {s["id"]: s for s in m["sources"]}
    assert por_id["registro_br"]["as_of"] == T1 and por_id["anatel_sici"]["as_of"] == "2026-08"
    assert all(s["origem"] in ("armazem", "legado", "ausente") for s in m["sources"])


def test_composicao_resolve_a_melhor_versao_disponivel_em_cada_data(cat, base):
    """Duas coletas semanais: o snapshot de T0 vê a de T0; o de T1 vê a de T1 (o snapshot compõe versões)."""
    v0 = registrar_da_fonte(cat, base, "registro_br", T0)[0]
    v1 = registrar_da_fonte(cat, base, "registro_br", T1)[0]
    assert resolver(base, "registro_br", T0).nome == v0.nome and resolver(base, "registro_br", T1).nome == v1.nome
    assert v0.nome == T0 and v1.nome == T1                  # duas as_of, duas versões (o conteúdo pode coincidir)


def test_reconstrucao_com_pin_sources_repoe_as_versoes_do_manifesto(cat, base):
    """Snapshot T1 com as fontes apagadas de normalized/: --pin-sources as restaura do armazém, byte a byte."""
    feitas = _registrar_todas(cat, base, T1)
    man = json.loads((base / "published" / T1 / "manifest.json").read_text())
    man["sources"] = [{"id": fid, "versao": v.nome, "origem": "armazem"} for fid, v in feitas.items()]
    (base / "published" / T1 / "manifest.json").write_text(json.dumps(man))
    originais = {rel: (base / rel.partition("/")[0] / T1 / rel.partition("/")[2]).read_bytes()
                 for v in feitas.values() for rel in v.arquivos if rel.startswith("normalized/")}
    for rel in originais:
        (base / "normalized" / T1 / rel.partition("/")[2]).unlink()
    rel_ = executor.executar(cat, T1, base, FakeRunner(), pin_sources=True, usar_lock=False, log=lambda *_: None)
    assert rel_.ok
    for rel, conteudo in originais.items():
        assert (base / "normalized" / T1 / rel.partition("/")[2]).read_bytes() == conteudo
