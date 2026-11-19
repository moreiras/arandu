# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""caches indexados pelo que o cliente pede não crescem sem limite."""
import json
from pathlib import Path

from api.repos.base import ArtifactRepo
from api.store import Store, _SafeLRU
from api.services.geolocalizacao import GeolocalizacaoService


def _snapshot(base: Path, data: str) -> Path:
    pub = base / "published" / data
    pub.mkdir(parents=True)
    (pub / "manifest.json").write_text(json.dumps({"snapshot_date": data}))
    return pub


def test_data_inventada_nao_vira_entrada_nos_caches_do_store(tmp_path):
    _snapshot(tmp_path, "2026-11-13")
    s = Store(tmp_path)
    for i in range(50):
        d = f"2099-01-{i % 28 + 1:02d}"
        assert s.asn_detail(d, 65000 + i) is None and s.ixp_detail(d, "sp") is None
    assert s._asn_detail_cache == {} and s._ixp_detail_cache == {}


def test_repositorio_so_guarda_o_none_de_snapshot_que_existe(tmp_path):
    _snapshot(tmp_path, "2026-11-13")
    repo = ArtifactRepo(lambda d: tmp_path / "published" / d)
    assert repo.ler("2026-11-13", "nao_existe.json.gz") is None and ("2026-11-13", "nao_existe.json.gz") in repo._cache   # ausência real: cacheada
    for i in range(30):
        assert repo.ler(f"2099-02-{i % 28 + 1:02d}", "x.json.gz") is None
    assert len(repo._cache) == 1


def test_lru_tem_teto_e_get_e_atomico():
    c = _SafeLRU(maxsize=3)
    for i in range(10):
        c[i] = i
    assert c.get(0) is None and c.get(9) == 9 and c.get("x", "padrao") == "padrao"


def test_geolocalizacao_usa_lru_com_teto():
    g = GeolocalizacaoService.__new__(GeolocalizacaoService)
    GeolocalizacaoService.__init__(g, store=None)
    for nome in ("_ixp_geo_cache", "_asn_geo_cache", "_origin_prefixes_cache"):
        assert isinstance(getattr(g, nome), _SafeLRU), nome
