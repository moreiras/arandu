# SPDX-License-Identifier: AGPL-3.0-or-later
"""T1 — enriquecimentos locais: orgs (rdap), geolocalização por DB-IP City Lite (prefixos BR e globais)."""
import gzip
import shutil

import httpx
import pytest
import respx

from sources.global_prefix_geo import enrich as global_prefix_geo
from sources.prefix_geo import enrich as prefix_geo
from sources.rdap import enrich as rdap
from tests.sources.conftest import read_gz, write_gz

MMDB = ("dbip", "dbip-city-lite-2026-09.sample.mmdb")


@pytest.fixture()
def registro(base, date_str):
    write_gz(base / "normalized" / date_str / "summary" / "registro_br.json.gz", {"asns": [
        {"asn": 64500, "name": "Provedor Um", "cnpj": "11111111000111", "prefixes_v4": ["200.160.5.0/24"], "prefixes_v6": ["2804:8f8:1::/48"]},
        {"asn": 64501, "name": "Provedor Dois", "cnpj": "", "prefixes_v4": ["200.192.10.0/24", "177.129.168.0/24"], "prefixes_v6": []},
        {"asn": 64502, "name": "Provedor Tres", "cnpj": "22222222000122", "prefixes_v4": ["201.6.1.0/24", "1.1.1.0/24"], "prefixes_v6": []},
    ]})


@pytest.fixture()
def mmdb_cache(base, fx):
    dst = base / "raw" / "dbip" / "dbip-city-lite-2026-09.mmdb"
    dst.parent.mkdir(parents=True)
    shutil.copy(fx(*MMDB), dst)
    return dst


# ── rdap (orgs) ────────────────────────────────────────────────────────────

def test_rdap_extrai_org_por_asn(base, log, registro, date_str):
    r = rdap.run(date_str, base, log)
    assert r["total"] == 3 and r["with_cnpj"] == 2
    assert r["orgs"]["64500"] == {"name": "Provedor Um", "cnpj": "11111111000111"}
    assert read_gz(base / "normalized" / date_str / "summary" / "orgs.json.gz")["total"] == 3


def test_rdap_sem_entrada_levanta(base, log, date_str):
    with pytest.raises(FileNotFoundError):
        rdap.run(date_str, base, log)


# ── prefix_geo ─────────────────────────────────────────────────────────────

def test_prefix_geo_municipio_a_partir_do_bairro_e_desconhecidos(base, log, registro, mmdb_cache, date_str):
    r = prefix_geo.run(date_str, base, None, log)
    p = r["prefixes"]
    assert p["200.160.5.0/24"] == {"lat": -23.5611, "lon": -46.6876, "city": "São Paulo", "country": "BR", "uf": "SP",
                                   "geo_confidence": "city_centroid", "geo_source": "dbip-lite-2026-09"}
    assert p["2804:8f8:1::/48"]["city"] == "Curitiba" and p["2804:8f8:1::/48"]["uf"] == "PR"
    assert p["177.129.168.0/24"]["city"] == "Rio de Janeiro" and p["177.129.168.0/24"]["lat"] == -22.9    # sem cidade na base: o município vem do centroide
    for unknown in ("201.6.1.0/24", "1.1.1.0/24"):                                           # sem coordenadas / fora do banco
        assert p[unknown] == {"lat": None, "lon": None, "geo_confidence": "unknown", "geo_source": "dbip-lite-2026-09"}
    assert (r["total"], r["geolocated"], r["unknown"]) == (6, 4, 2)


def test_prefix_geo_grava_normalizado(base, log, registro, mmdb_cache, date_str):
    prefix_geo.run(date_str, base, None, log)
    assert read_gz(base / "normalized" / date_str / "summary" / "geo_prefixes.json.gz")["mmdb_month"] == "2026-09"


def test_prefix_geo_mes_do_banco_explicito(base, log, registro, mmdb_cache, date_str):
    other = base / "raw" / "dbip" / "dbip-city-lite-2026-08.mmdb"
    shutil.copy(mmdb_cache, other)
    assert prefix_geo.run(date_str, base, "2026-08", log)["geo_source"] == "dbip-lite-2026-08"


def test_prefix_geo_sem_registro_levanta(base, log, mmdb_cache, date_str):
    with pytest.raises(FileNotFoundError, match="registro_br"):
        prefix_geo.run(date_str, base, None, log)


def test_prefix_geo_registro_sem_prefixos_levanta(base, log, mmdb_cache, date_str):
    write_gz(base / "normalized" / date_str / "summary" / "registro_br.json.gz", {"asns": [{"asn": 1, "prefixes_v4": [], "prefixes_v6": []}]})
    with pytest.raises(FileNotFoundError, match="Nenhum prefixo"):
        prefix_geo.run(date_str, base, None, log)


@respx.mock
def test_prefix_geo_baixa_e_descompacta_o_mmdb_do_dbip(base, log, registro, fx, date_str):
    corpo = gzip.compress(fx(*MMDB).read_bytes())
    route = respx.get("https://download.db-ip.com/free/dbip-city-lite-2026-09.mmdb.gz").respond(200, content=corpo)
    r = prefix_geo.run(date_str, base, None, log)
    assert r["geolocated"] == 4 and r["geo_source"] == "dbip-lite-2026-09"
    assert route.calls[0].request.headers["user-agent"].startswith("arandurape/")        # identificado, sem chave nem querystring
    assert (base / "raw" / "dbip" / "dbip-city-lite-2026-09.mmdb").exists()
    assert not list((base / "raw" / "dbip").glob("*.tmp"))                               # escrita atômica


@respx.mock
def test_prefix_geo_usa_o_mes_anterior_se_o_do_mes_ainda_nao_saiu(base, log, registro, fx, date_str):
    respx.get("https://download.db-ip.com/free/dbip-city-lite-2026-09.mmdb.gz").respond(404)
    respx.get("https://download.db-ip.com/free/dbip-city-lite-2026-08.mmdb.gz").respond(200, content=gzip.compress(fx(*MMDB).read_bytes()))
    assert prefix_geo.run(date_str, base, None, log)["geo_source"] == "dbip-lite-2026-08"


@respx.mock
def test_prefix_geo_falha_se_nenhum_dos_dois_meses_existe(base, log, registro, date_str):
    respx.get(url__regex=r"https://download\.db-ip\.com/free/.*").respond(404)
    with pytest.raises(httpx.HTTPStatusError):
        prefix_geo.run(date_str, base, None, log)



@pytest.mark.parametrize("prefix, esperado", [("200.160.5.0/24", "200.160.5.0"), ("200.160.5.7/24", "200.160.5.0"), ("2804:8f8::/32", "2804:8f8::")])
def test_prefix_geo_first_ip(prefix, esperado):
    assert prefix_geo._first_ip(prefix) == esperado


# ── global_prefix_geo ──────────────────────────────────────────────────────

@pytest.fixture()
def ixp_prefixes(base, date_str):
    d = base / "normalized" / date_str
    write_gz(d / "sp" / "prefix-set-v4.json.gz", ["200.160.5.0/24", "200.192.10.0/24", "8.8.8.0/24"])
    write_gz(d / "rj" / "prefix-set-v4.json.gz", ["200.160.5.0/24"])
    write_gz(d / "sp" / "prefix-set-v6.json.gz", ["2804:8f8:1::/48"])
    write_gz(d / "sp" / "origin-prefixes-v4.json.gz", {"64500": ["200.160.5.0/24"], "64501": ["200.192.10.0/24"]})
    write_gz(d / "rj" / "origin-prefixes-v4.json.gz", {"64999": ["200.160.5.0/24"]})     # o primeiro IXP vence
    (d / "summary").mkdir(parents=True, exist_ok=True)


def test_global_prefix_geo_indexa_ixps_e_origem(base, log, ixp_prefixes, mmdb_cache, date_str):
    r = global_prefix_geo.run(date_str, base, None, log)
    p = r["prefixes"]
    sp = p["200.160.5.0/24"]
    assert sp["ixps_seen"] == ["rj", "sp"] and sp["origin_asn"] == 64999      # "rj" é lido antes de "sp"
    assert sp["ip_version"] == 4 and sp["city"] == "São Paulo" and sp["geo_confidence"] == "city_centroid"
    assert p["8.8.8.0/24"]["country"] == "US" and p["8.8.8.0/24"]["origin_asn"] is None
    assert p["2804:8f8:1::/48"]["ip_version"] == 6
    assert r["total"] == 4 and r["geolocated"] == 4


def test_global_prefix_geo_sem_prefix_set_levanta(base, log, mmdb_cache, date_str):
    (base / "normalized" / date_str / "summary").mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="prefix-set"):
        global_prefix_geo.run(date_str, base, None, log)


def test_global_prefix_geo_sem_pasta_de_normalizado_levanta(base, log, mmdb_cache, date_str):
    with pytest.raises(FileNotFoundError, match="normalized"):
        global_prefix_geo.run(date_str, base, None, log)
