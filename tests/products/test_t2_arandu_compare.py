# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T2 — `arandu run --compare` sobre o snapshot sintético: mesmas etapas do catálogo, mesmo critério do replay."""
import pytest

from arandu import compare
from core.catalog.loader import load_catalog
from scripts import replay
from tests.products.conftest import fake_ixps, fake_pix, patch_area_influencia
from tests.synth.world import PTTS, T1


@pytest.fixture(scope="module")
def monkeypatch_module():
    with pytest.MonkeyPatch.context() as mp:
        yield mp


@pytest.fixture(scope="module")
def configurado(pipeline, monkeypatch_module):
    from products.bgp_routes import build as bgp_parser
    from products.ixp_metrics import build as metrics
    from api.store import Store
    from publish import snapshot_builder
    from tests.synth.infra import EXTERNAL_IXP

    for mod in (bgp_parser, metrics, snapshot_builder):
        monkeypatch_module.setattr(mod, "load_ixps", fake_ixps, raising=False)
    monkeypatch_module.setattr(snapshot_builder, "load_peeringdb_ixps_config", lambda: {
        "external": [EXTERNAL_IXP], "ixbr": [{"code": c, "pdb_ix_id": 9000 + i} for i, (c, _, _) in enumerate(PTTS)]})
    monkeypatch_module.setattr(Store, "_load_pix_config", lambda self: fake_pix())
    patch_area_influencia(monkeypatch_module)
    from core import marcas as marcas_mod
    from tests.synth.qualidade import CURADA

    monkeypatch_module.setattr(marcas_mod, "CAMINHO_CURADA", CURADA)      # tabela marca → CNPJ sintética
    from products import passos
    monkeypatch_module.setattr(passos, "_ixps_atual", fake_ixps)
    monkeypatch_module.setattr(passos, "_config_atual", lambda: {
        "external": [EXTERNAL_IXP], "ixbr": [{"code": c, "pdb_ix_id": 9000 + i} for i, (c, _, _) in enumerate(PTTS)]})
    return pipeline[0]


def test_etapas_do_compare_sao_as_do_replay(pipeline):
    cat = load_catalog()
    base, _ = pipeline
    ids = [s.id for s in compare.etapas_do_compare(cat, base / "published" / T1)]
    # bgp_ixp, metricas_ixp_asn, passos do build, análise BGP (routing_analysis, bgp_stability, bgp_stability_deep) e saude_asn — só os artefatos que o publicado tem
    nomes = ids
    # os passos do build substituem o snapshot_completo no compare; bgp_ixp vem antes de metricas_ixp_asn e este antes do índice de ASNs
    assert nomes.index("bgp_ixp") < nomes.index("metricas_ixp_asn") < nomes.index("asn_indice") < nomes.index("snapshot_resumo")
    assert "snapshot_completo" not in nomes and ids[-1].endswith("manifesto") and ids[-2].endswith("manrs") and ids[-3].endswith("prontidao") and ids[-4].endswith("saude_asn")


def test_compare_do_sintetico_nao_tem_diferencas_novas_e_equivale_ao_replay(configurado, tmp_path_factory):
    base = configurado
    cat = load_catalog()
    rep = compare.comparar(cat, T1, base, work_dir=tmp_path_factory.mktemp("cmp"), replay_mod=replay, log=lambda *_: None)
    assert rep["etapa_falhou"] is None, rep["etapas"]
    assert compare.diferencas_novas(rep) == 0, [r for r in rep["arquivos"] if r["classe"] in ("nova", "ordem")][:5]
    ref = replay.replay(T1, base, work_dir=tmp_path_factory.mktemp("ref"), expected=[])
    assert rep["contagem"].get("igual") == ref["contagem"].get("igual")
    assert rep["contagem"].get("igual", 0) > 50
