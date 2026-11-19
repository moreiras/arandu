# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T2 — `compose`: com ARANDU_COMPOSE=on o publicado é idêntico, byte a byte, ao do fluxo antigo."""
import shutil

import pytest

from tests.products.conftest import run_pipeline
from tests.products.escritas import contar_escritas
from tests.synth.world import T1


ESCRITAS: dict = {}


def _arquivos(base):
    """Conteúdo dos publicados; .json.gz entra descomprimido (o gzip embute data/hora)."""
    import gzip
    pub = base / "published" / T1
    saida = {}
    for p in sorted(pub.rglob("*")):
        if p.is_file() and p.name not in ("manifest.json", "snapshot_detail.json"):     # carimbos próprios de cada execução
            saida[str(p.relative_to(pub))] = gzip.decompress(p.read_bytes()) if p.name.endswith(".gz") else p.read_bytes()
    return saida


@pytest.fixture(scope="module")
def duas_execucoes(dataset, tmp_path_factory):
    saida = {}
    for modo in ("off", "on"):
        base = tmp_path_factory.mktemp(f"compose_{modo}") / "data"
        shutil.copytree(dataset, base)
        with pytest.MonkeyPatch.context() as mp, contar_escritas(base) as c:
            mp.setenv("ARANDU_COMPOSE", modo)
            run_pipeline(base, T1, mp)
        saida[modo] = (base, _arquivos(base))
        ESCRITAS[modo] = c
    return saida


def _sem_gerado_em(b: bytes) -> bytes:
    import re
    return re.sub(rb'"generated_at": "[^"]*"', b'"generated_at": "X"', b)


def test_published_com_compose_e_identico_ao_fluxo_antigo(duas_execucoes):
    (_, off), (_, on) = duas_execucoes["off"], duas_execucoes["on"]
    assert set(off) == set(on) and sum(k.startswith('asns/') for k in off) > 50      # compara de verdade
    diferentes = [k for k in off if k.endswith((".json", ".geojson", ".gz")) and _sem_gerado_em(off[k]) != _sem_gerado_em(on[k])]
    assert diferentes == []


def test_o_dataset_exercita_ixp_paths_e_sici(duas_execucoes):
    """O teste de igualdade só vale se os blocos que viram fragmento aparecem de fato nos documentos."""
    import json
    base_on, _ = duas_execucoes["on"]
    docs = [json.loads(p.read_text()) for p in (base_on / "published" / T1 / "asns").glob("*.json") if p.stem.isdigit()]
    assert any("ixp_paths" in d for d in docs) and any("sici" in d for d in docs) and any("alerts" in d for d in docs)
    from core import compose
    for produto in ("base", "ixp_paths", "sici", "saude"):
        assert compose.caminho(base_on, T1, produto).is_file(), produto


def test_o_fragmento_base_existe_na_area_de_montagem(duas_execucoes):
    from core import compose
    base_on, _ = duas_execucoes["on"]
    assert compose.caminho(base_on, T1, "base").is_file()
    base_off, _ = duas_execucoes["off"]
    assert not compose.caminho(base_off, T1, "base").exists()


def test_saude_repetida_nao_muda_nada_e_force_recompõe_igual(duas_execucoes, tmp_path, monkeypatch):
    """Rodar o `saude_asn` de novo com fragmento presente é no-op; com --force a saúde é recalculada e o publicado volta idêntico."""
    from core import compose
    from core.common import configure_logging
    from publish import snapshot_builder
    from api.store import Store
    from tests.products.conftest import fake_pix

    base_on, _ = duas_execucoes["on"]
    copia = tmp_path / "data"
    shutil.copytree(base_on, copia)
    antes = _arquivos(copia)
    monkeypatch.setenv("ARANDU_COMPOSE", "on")
    monkeypatch.setattr(Store, "_load_pix_config", lambda self: fake_pix())
    log = configure_logging()
    assert snapshot_builder.build_asn_health_for_asns(copia, T1, log) == 0               # fragmento presente: no-op
    assert _arquivos(copia) == antes
    assert snapshot_builder.build_asn_health_for_asns(copia, T1, log, force=True) > 0
    depois = _arquivos(copia)
    assert {k: _sem_gerado_em(v) for k, v in depois.items() if k.startswith("asns/")} == \
           {k: _sem_gerado_em(v) for k, v in antes.items() if k.startswith("asns/")}


def test_scm_e_mapa_do_scm_sao_escritos_uma_vez_com_a_flag(duas_execucoes):
    """Com a flag, o SICI não reescreve scm.json.gz nem maps/scms.geojson (sem ela: 2 escritas cada)."""
    antes, depois = ESCRITAS["off"], ESCRITAS["on"]
    d = f"{T1}"
    for arq in ("scm.json.gz", "maps/scms.geojson"):
        assert antes[f"{d}/{arq}"] == 2, (arq, antes[f"{d}/{arq}"])
        assert depois[f"{d}/{arq}"] == 1, (arq, depois[f"{d}/{arq}"])


def test_com_a_flag_cada_arquivo_de_asn_e_o_indice_sao_escritos_uma_vez(duas_execucoes):
    """Meta: 1 escrita por arquivo publicado (sem compose: documento de ASN até 4×, índice 2×)."""
    from tests.products.test_t2_escritas import resumo
    antes, depois = resumo(ESCRITAS["off"]), resumo(ESCRITAS["on"])
    assert antes["asns/{n}.json"]["max_escritas"] >= 3 and antes["asns/index.json"]["max_escritas"] == 2
    assert depois["asns/{n}.json"]["max_escritas"] == 1, depois["asns/{n}.json"]
    assert depois["asns/index.json"]["max_escritas"] == 1
    assert depois["asns/{n}.json"]["arquivos"] == antes["asns/{n}.json"]["arquivos"]       # os mesmos documentos
    extras = {k: v["max_escritas"] for k, v in depois.items() if v["max_escritas"] > 1 and not k.endswith(".tmp")}
    assert extras == {}, f"arquivos publicados ainda reescritos: {extras}"
