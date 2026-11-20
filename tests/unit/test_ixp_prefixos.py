# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — camada de prefixos do PTT pré-calculada (`maps/ixp_prefixes/`).

O pipeline grava o mesmo que a API calcularia; a API lê o arquivo sem tocar na base de geolocalização (no SP o cálculo na hora
passa do limite do proxy) e só calcula quando o arquivo falta ou quando há filtro de AS no caminho."""
import gzip
import json
import sys
import types

import structlog

from api import store as store_mod
from core import ixp_geo
from products.mapas_prefixos import ixp_prefixos

D = "2026-11-15"
_CIDADES = {"203": ("Cidade A", 10.0, 20.0), "198": ("Cidade B", 11.0, 21.0)}


class _Reader:
    def __init__(self):
        self.consultas = 0

    def get(self, ip):
        self.consultas += 1
        nome, lat, lon = _CIDADES.get(ip.split(".")[0], ("Cidade C", 12.0, 22.0)) if "." in ip else ("Cidade V6", 13.0, 23.0)
        return {"location": {"latitude": lat, "longitude": lon}, "city": {"names": {"en": nome}}, "country": {"iso_code": "US"}}

    def close(self):
        pass


def _dados(tmp_path):
    norm = tmp_path / "normalized" / D / "xx"
    norm.mkdir(parents=True)
    rotas = {"routes": [
        {"prefix": "203.0.112.0/22", "aspath": [65001, 65001, 65002]},
        {"prefix": "198.51.100.0/24", "aspath": [65003]},
        {"prefix": "192.0.0.0/19", "aspath": [65001, 65004]},       # /19 → dois /20
    ]}
    with gzip.open(norm / "routes-v4.json.gz", "wt") as f:
        json.dump(rotas, f)
    with gzip.open(norm / "routes-v6.json.gz", "wt") as f:
        json.dump({"routes": [{"prefix": "2001:db8::/32", "aspath": [65001]}]}, f)
    (tmp_path / "published" / D).mkdir(parents=True)
    (tmp_path / "raw" / "dbip").mkdir(parents=True)
    (tmp_path / "raw" / "dbip" / "dbip-city-lite-2026-11.mmdb").write_bytes(b"")


def _maxmind(monkeypatch, reader):
    monkeypatch.setitem(sys.modules, "maxminddb", types.SimpleNamespace(open_database=lambda _p: reader))
    monkeypatch.setattr(store_mod, "_maxminddb", types.SimpleNamespace(open_database=lambda _p: reader))


def test_pipeline_grava_o_mesmo_que_a_api_calcularia(tmp_path, monkeypatch):
    _dados(tmp_path)
    _maxmind(monkeypatch, _Reader())
    calculado = store_mod.Store(tmp_path)._geolocalizacao._ixp_geo_prefixes(D, "xx", "v4")
    assert sum(f["properties"]["block_count"] for f in calculado["features"]) == 4

    assert ixp_prefixos.publicar(tmp_path, D, structlog.get_logger()) == 2
    arq = ixp_geo.caminho(tmp_path, D, "xx", "v4")
    meta = json.load(gzip.open(arq, "rt"))
    assert (meta["ixp_code"], meta["afi"], meta["prefixes"], meta["mmdb"]) == ("xx", "v4", 3, "dbip-city-lite-2026-11.mmdb")
    assert ixp_geo.ler(tmp_path, D, "xx", "v4") == calculado


def test_api_le_o_arquivo_sem_consultar_a_base(tmp_path, monkeypatch):
    _dados(tmp_path)
    _maxmind(monkeypatch, _Reader())
    ixp_prefixos.publicar(tmp_path, D, structlog.get_logger())
    leitor_da_api = _Reader()
    _maxmind(monkeypatch, leitor_da_api)
    geo = store_mod.Store(tmp_path)._geolocalizacao
    fc = geo._ixp_geo_prefixes(D, "xx", "v6")
    assert fc["features"] and leitor_da_api.consultas == 0
    # com filtro de AS no caminho o arquivo não serve: calcula
    filtrado = geo._ixp_geo_prefixes(D, "xx", "v4", exclude_asns=frozenset({65001}))
    assert leitor_da_api.consultas > 0
    assert sum(f["properties"]["block_count"] for f in filtrado["features"]) == 1


def test_sem_force_nao_sobrescreve_e_codigo_invalido_nao_vira_caminho(tmp_path, monkeypatch):
    _dados(tmp_path)
    _maxmind(monkeypatch, _Reader())
    assert ixp_prefixos.publicar(tmp_path, D, structlog.get_logger()) == 2
    assert ixp_prefixos.publicar(tmp_path, D, structlog.get_logger(), force=False) == 0
    assert ixp_geo.caminho(tmp_path, D, "../xx", "v4") is None
    assert ixp_geo.caminho(tmp_path, D, "xx", "v5") is None
    assert ixp_geo.ler(tmp_path, D, "../xx", "v4") is None


def test_sem_base_de_geolocalizacao_nao_grava(tmp_path, monkeypatch):
    _dados(tmp_path)
    (tmp_path / "raw" / "dbip" / "dbip-city-lite-2026-11.mmdb").unlink()
    assert ixp_prefixos.publicar(tmp_path, D, structlog.get_logger()) == 0
    assert not (tmp_path / "published" / D / "maps").exists()
