# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T2 — replay do snapshot sintético: reconstruir o publicado a partir de raw/normalized dá o mesmo."""
import shutil

import pytest

from scripts import replay
from tests.products.conftest import fake_ixps, fake_pix, patch_area_influencia
from tests.synth.world import T1


@pytest.fixture(scope="module")
def relatorio(pipeline, tmp_path_factory, monkeypatch_module):
    base, _ = pipeline
    from products.bgp_routes import build as bgp_parser
    from products.ixp_metrics import build as metrics
    from publish import snapshot_builder

    from api.store import Store
    from tests.synth.infra import EXTERNAL_IXP
    from tests.synth.world import PTTS

    for mod in (bgp_parser, metrics, snapshot_builder):
        monkeypatch_module.setattr(mod, "load_ixps", fake_ixps, raising=False)
    monkeypatch_module.setattr(snapshot_builder, "load_peeringdb_ixps_config", lambda: {
        "external": [EXTERNAL_IXP], "ixbr": [{"code": c, "pdb_ix_id": 9000 + i} for i, (c, _, _) in enumerate(PTTS)]})
    monkeypatch_module.setattr(Store, "_load_pix_config", lambda self: fake_pix())
    patch_area_influencia(monkeypatch_module)
    from core import marcas as marcas_mod
    from tests.synth.qualidade import CURADA

    monkeypatch_module.setattr(marcas_mod, "CAMINHO_CURADA", CURADA)      # tabela marca → CNPJ sintética
    return replay.replay(T1, base, work_dir=tmp_path_factory.mktemp("replay"), expected=[])


@pytest.fixture(scope="module")
def monkeypatch_module():
    with pytest.MonkeyPatch.context() as mp:
        yield mp


def test_replay_do_dataset_sintetico_nao_tem_diferencas_novas(relatorio):
    c = relatorio["contagem"]
    novas = [r for r in relatorio["arquivos"] if r["classe"] in ("nova", "ordem")]
    assert not novas, novas[:5]
    assert c.get("igual", 0) > 50


def test_replay_deixa_o_data_dir_original_intacto(pipeline, relatorio):
    base, _ = pipeline
    assert (base / "published" / T1 / "manifest.json").exists()
    assert not (base / "published" / T1 / "replay").exists()
