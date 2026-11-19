# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — camadas GeoJSON grandes não ficam em memória (risco de OOM da API).

`ibge_rodovias` (~135 MB) e `global_prefixes` (~100 MB) viram 1–2 GB de objetos Python por data. Por isso a
camada acima do limite é lida sob demanda e solta; a rota de rodovias filtra feição a feição direto do arquivo."""
import json
from pathlib import Path

from api.store import Store

DATA = "2026-10-24"


def _store(tmp_path: Path, layer: str, doc: dict) -> Store:
    maps = tmp_path / "published" / DATA / "maps"
    maps.mkdir(parents=True)
    (maps / f"{layer}.geojson").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return Store(tmp_path)


def _feicao(i: int, juris: str, pav: bool, sigla: str) -> dict:
    return {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-40 + i, -10], [-41 + i, -11]]},
            "properties": {"jurisdicao": juris, "pavimentada": pav, "sigla": sigla, "nome": "Trecho {é}"}}


DOC = {"type": "FeatureCollection", "snapshot_date": DATA, "source": "IBGE — teste",
       "features": [_feicao(0, "Federal", True, "BR-101"), _feicao(1, "Estadual/Distrital", False, "ES-010"),
                    _feicao(2, "Federal", False, "BR-262"), _feicao(3, "Municipal", True, "")]}


def test_filtro_em_streaming_equivale_ao_filtro_do_documento_inteiro(tmp_path):
    st = _store(tmp_path, "ibge_rodovias", DOC)
    for aceita in (lambda f: True, lambda f: f["properties"]["jurisdicao"] == "Federal",
                   lambda f: f["properties"]["pavimentada"] is True, lambda f: False):
        esperado = {**DOC, "features": [f for f in DOC["features"] if aceita(f)]}
        assert st.geo_map_filtrado(DATA, "ibge_rodovias", aceita) == esperado


def test_filtro_preserva_chaves_depois_das_feicoes(tmp_path):
    doc = {"type": "FeatureCollection", "features": DOC["features"][:2], "snapshot_date": DATA, "source": "depois"}
    st = _store(tmp_path, "ibge_rodovias", doc)
    r = st.geo_map_filtrado(DATA, "ibge_rodovias", lambda f: True)
    assert r["source"] == "depois" and r["snapshot_date"] == DATA and len(r["features"]) == 2


def test_camada_ausente_ou_ilegivel_e_none(tmp_path):
    st = Store(tmp_path)
    assert st.geo_map_filtrado(DATA, "ibge_rodovias", lambda f: True) is None
    st2 = _store(tmp_path / "x", "ibge_rodovias", DOC)
    (tmp_path / "x" / "published" / DATA / "maps" / "ibge_rodovias.geojson").write_text("{quebrado", encoding="utf-8")
    assert st2.geo_map_filtrado(DATA, "ibge_rodovias", lambda f: True) is None


def test_camada_pequena_fica_em_cache_e_grande_nao(tmp_path):
    st = _store(tmp_path, "prefixes", DOC)
    assert st.geo_map(DATA, "prefixes") is st.geo_map(DATA, "prefixes")        # mesma instância = cache
    st._mapas.GEO_CAMADA_GRANDE_BYTES = 10                                             # tudo passa a ser "grande"
    a, b = st.geo_map(DATA, "prefixes"), st.geo_map(DATA, "prefixes")
    assert a == b and a is not b                                                # relido a cada chamada
    assert "global_prefixes" not in st._mapas._geo_maps.get(DATA, {})


def test_geo_map_arquivo_devolve_o_caminho(tmp_path):
    st = _store(tmp_path, "ibge_rodovias", DOC)
    assert st.geo_map_arquivo(DATA, "ibge_rodovias").name == "ibge_rodovias.geojson"
    assert st.geo_map_arquivo(DATA, "outra") is None
