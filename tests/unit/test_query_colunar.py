# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — tabela colunar: o motor colunar responde exatamente como o motor por linhas, em qualquer consulta."""
import json
import random
from pathlib import Path

import pytest

from api import query as q
from api import query_colunar
from api.store import Store
from core import colunar
from products.mapas_prefixos.build import CAMPOS_GLOBAL_PREFIXES, escrever_global_prefixes_colunar

DATA = "2026-10-25"
CIDADES = [("São Paulo", "BR", -23.55, -46.63), ("Mumbai", "IN", 19.07, 72.87), ("Vitória", "BR", -20.31, -40.31),
           ("", "", 0.5, 0.5), ("Ashburn", "US", 39.04, -77.48), ("Linha\u2028Nova\x85", "XX", 1.0, 2.0)]
IXPS = ["sp", "rj", "vix", "mg", "rs"]


def _features(n: int = 600) -> list[dict]:
    rnd = random.Random(7)
    out = []
    for i in range(n):
        cidade, pais, lat, lon = rnd.choice(CIDADES)
        v6 = i % 5 == 0
        out.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "prefix": f"2001:db8:{i:x}::/48" if v6 else f"10.{i // 250}.{i % 250}.0/24",
                        "ip_version": 6 if v6 else 4,
                        "origin_asn": None if i % 17 == 0 else rnd.choice([64500, 64501, 15169, 3356]),
                        "ixps_seen": sorted(rnd.sample(IXPS, rnd.randint(0, 4))),
                        "city": cidade, "country": pais, "geo_confidence": rnd.choice(["city_centroid", "unknown"]),
                        "geo_source": "geolite2-2026-10"}})
    return out


def _linhas(features: list[dict]) -> list[dict]:
    rows = []
    for ft in features:
        props, coords = ft["properties"], ft["geometry"]["coordinates"]
        rows.append({**props, "lon": coords[0], "lat": coords[1]})
    return rows


@pytest.fixture(scope="module")
def mundo(tmp_path_factory):
    feats = _features()
    caminho = tmp_path_factory.mktemp("col") / "g.col"
    escrever_global_prefixes_colunar(feats, caminho)
    tab = colunar.TabelaColunar(caminho)
    yield tab, _linhas(feats)
    tab.fechar()


def P(field, op, value=None):
    return {"field": field, "op": op, "value": value}


CONSULTAS = [
    {},
    {"limit": 5, "page": 3},
    {"filter": P("country", "eq", "BR")},
    {"filter": P("country", "ne", "BR"), "limit": 1000},
    {"filter": P("origin_asn", "eq", None)},
    {"filter": P("origin_asn", "exists", True)},
    {"filter": P("origin_asn", "exists", False)},
    {"filter": P("origin_asn", "gt", 15169), "sort": [{"field": "prefix", "dir": "desc"}]},
    {"filter": P("origin_asn", "in", [64500, 3356]), "select": ["prefix", "origin_asn"]},
    {"filter": P("origin_asn", "nin", [64500])},
    {"filter": P("ixps_seen", "contains", "sp")},
    {"filter": P("ixps_seen", "ncontains", "sp")},
    {"filter": {"and": [P("ixps_seen", "contains", "sp"), P("ixps_seen", "ncontains", "rj")]}},
    {"filter": {"or": [P("city", "contains", "paulo"), P("country", "eq", "IN")]}},
    {"filter": {"not": P("ip_version", "eq", 6)}},
    {"filter": P("prefix", "contains", "2001:db8")},
    {"filter": P("lat", "lte", -20)},
    {"filter": {"op": "within_radius", "centers": [[-23.5, -46.6]], "radius_km": 50}},
    {"filter": {"and": [{"op": "within_radius", "centers": [[-23.5, -46.6], [19, 72.8]], "radius_km": 100},
                        P("ip_version", "eq", 4)]}, "sort": [{"field": "origin_asn", "dir": "asc"}, {"field": "prefix"}]},
    {"group_by": ["country"], "aggregate": [{"fn": "count"}]},
    {"filter": P("ip_version", "eq", 4), "group_by": ["country", "city"],
     "aggregate": [{"fn": "count"}, {"fn": "distinct", "field": "origin_asn"}, {"fn": "max", "field": "origin_asn", "as": "m"}]},
    {"aggregate": [{"fn": "avg", "field": "lat"}, {"fn": "min", "field": "lon"}]},
    {"filter": P("city", "eq", "Inexistente")},
    {"filter": P("campo_que_nao_existe", "eq", 1)},
    {"filter": P("country", "gte", "C"), "sort": [{"field": "country", "dir": "desc"}], "limit": 7},
]


@pytest.mark.parametrize("corpo", CONSULTAS, ids=lambda c: json.dumps(c, ensure_ascii=False)[:70])
def test_equivale_ao_motor_por_linhas(mundo, corpo):
    tab, linhas = mundo
    assert query_colunar.execute(tab, dict(corpo)) == q.execute(linhas, dict(corpo))


def test_linhas_reconstruidas_sao_identicas_inclusive_ordem_das_chaves(mundo):
    tab, linhas = mundo
    assert tab.n == len(linhas)
    for i in (0, 1, 17, len(linhas) - 1):
        assert tab.linha(i) == linhas[i]
        assert list(tab.linha(i)) == list(linhas[i])
    assert list(tab.linha(0))[:len(CAMPOS_GLOBAL_PREFIXES)] == list(CAMPOS_GLOBAL_PREFIXES)


@pytest.mark.parametrize("corpo", [{"filter": {"op": "within_radius", "radius_km": 5}}, {"filter": "x"},
                                   {"filter": P("country", "zz", 1)}, {"sort": [{"dir": "asc"}]}])
def test_erros_de_consulta_sao_querryerror(mundo, corpo):
    tab, _ = mundo
    with pytest.raises(q.QueryError):
        query_colunar.execute(tab, corpo)


def test_escrita_e_atomica_e_arquivo_invalido_vira_none(tmp_path):
    colunar.escrever(tmp_path / "t.col", {"a": [1, 2, 2], "b": ["x", None, "x"]})
    assert not (tmp_path / "t.col.tmp").exists()
    t = colunar.TabelaColunar(tmp_path / "t.col")
    assert t.n == 3 and t.linha(1) == {"a": 2, "b": None} and t.colunas["a"].distintos == 2
    t.fechar()
    (tmp_path / "ruim.col").write_bytes(b"nao e tabela")
    assert colunar.aberta_ou_none(tmp_path / "ruim.col") is None
    assert colunar.aberta_ou_none(tmp_path / "nao-existe.col") is None


def test_tabela_vazia(tmp_path):
    colunar.escrever(tmp_path / "v.col", {"a": []})
    t = colunar.TabelaColunar(tmp_path / "v.col")
    assert t.n == 0
    assert query_colunar.execute(t, {})["total"] == 0
    t.fechar()


def _store(tmp_path: Path, com_col: bool) -> Store:
    feats = _features(120)
    maps = tmp_path / "published" / DATA / "maps"
    maps.mkdir(parents=True)
    (maps / "global_prefixes.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "snapshot_date": DATA, "features": feats}), encoding="utf-8")
    if com_col:
        escrever_global_prefixes_colunar(feats, maps / "global_prefixes.col")
    return Store(tmp_path)


def test_store_usa_a_tabela_colunar_e_cai_no_geojson_sem_ela(tmp_path):
    corpo = {"filter": P("ixps_seen", "contains", "sp"), "sort": [{"field": "prefix"}], "limit": 20}
    com = _store(tmp_path / "a", True).query(DATA, "global_prefixes", dict(corpo))
    sem_store = _store(tmp_path / "b", False)
    sem = sem_store.query(DATA, "global_prefixes", dict(corpo))
    assert com == sem and com["total"] > 0
    assert sem_store.colunar(DATA, "global_prefixes") is None
    # o caminho colunar não monta a tabela de dicionários em memória
    st = _store(tmp_path / "c", True)
    st.query(DATA, "global_prefixes", {})
    assert f"{DATA}/global_prefixes" not in st._query_tables


def test_store_near_funciona_na_tabela_colunar(tmp_path):
    st = _store(tmp_path, True)
    r = st.query(DATA, "global_prefixes", {"near": {"point": [-23.55, -46.63], "radius_km": 30}, "limit": 1000})
    assert r["total"] > 0 and not any({"city", "lat", "lon"} & set(i) for i in r["items"])      # `near` usa a posição por dentro, não a devolve
    assert r["near"]["radius_km"] == 30


def test_limite_de_tabelas_abertas(tmp_path):
    import shutil

    st = _store(tmp_path, True)
    shutil.copytree(tmp_path / "published" / DATA, tmp_path / "published" / "2026-10-26")
    st._consultas.COLUNARES_ABERTAS = 1
    a = st.colunar(DATA, "global_prefixes")
    assert a is st.colunar(DATA, "global_prefixes")
    assert st.colunar("2026-10-26", "global_prefixes") is not None
    assert list(st._consultas._colunares) == ["2026-10-26/global_prefixes"]
