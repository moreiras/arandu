# SPDX-License-Identifier: AGPL-3.0-or-later
"""T1 — camadas de infraestrutura: ITU (WFS), TeleGeography, ANEEL SIGEL e IBGE BC250."""
import json
import re

import httpx
import pytest
import respx

from sources.aneel_sigel_transmission import collect as aneel
from sources.ibge_bc250_rodovias import collect as ibge
from sources.itu_transmission import collect as itu
from sources.telegeography_cables import collect as tg
from tests.sources.conftest import mount_range_zip, read_gz, volatile


# ── ITU ────────────────────────────────────────────────────────────────────

@respx.mock
def test_itu_mantem_so_linestring_e_conta_status(base, log, fx, date_str):
    respx.get(itu.WFS_BASE).respond(200, json=json.loads(fx("itu", "wfs-getfeature.sample.json").read_text()))
    r = itu.run(date_str, base, log)
    assert r["total"] == 4 and all(f["geometry"]["type"] == "LineString" for f in r["features"])
    assert set(r["features"][0]["properties"]) == {"type_inf", "status"}      # só os campos usados
    assert sum(r["status_counts"].values()) == 4
    assert read_gz(base / "normalized" / date_str / "summary" / "itu_transmission.json.gz")["total"] == 4


@respx.mock
def test_itu_pagina_por_startindex_e_ordena_por_uid(base, log, fx, date_str, monkeypatch):
    monkeypatch.setattr(itu, "PAGE_SIZE", 3)
    sample = json.loads(fx("itu", "wfs-getfeature.sample.json").read_text())
    pages = {0: sample["features"][:3], 3: sample["features"][3:]}
    seen = []

    def handler(request):
        qs = request.url.params
        seen.append((int(qs["startIndex"]), qs["sortBy"], qs["count"]))
        return httpx.Response(200, json={"features": pages[int(qs["startIndex"])], "numberMatched": 5})

    respx.get(itu.WFS_BASE).mock(side_effect=handler)
    r = itu.run(date_str, base, log)
    assert seen == [(0, "uid", "3"), (3, "uid", "3")] and r["total"] == 4


@respx.mock
def test_itu_http_erro(base, log, date_str):
    respx.get(itu.WFS_BASE).respond(502)
    with pytest.raises(httpx.HTTPStatusError):
        itu.run(date_str, base, log)


# ── TeleGeography ──────────────────────────────────────────────────────────

@respx.mock
def test_telegeography_junta_geometria_e_detalhes(base, log, fx, date_str, monkeypatch):
    monkeypatch.setattr(tg, "_DETAIL_PAUSE", 0)
    geo = json.loads(fx("telegeography", "cable-geo.sample.json").read_text())
    det = json.loads(fx("telegeography", "cable-details.sample.json").read_text())
    respx.get(f"{tg.API_BASE}/cable/cable-geo.json").respond(200, json=geo)
    respx.get(f"{tg.API_BASE}/landing-point/landing-point-geo.json").respond(200, json=json.loads(fx("telegeography", "landing-point-geo.sample.json").read_text()))
    for cid, d in det.items():
        respx.get(f"{tg.API_BASE}/cable/{cid}.json").respond(200, json=d)
    respx.get(url__regex=rf"{tg.API_BASE}/cable/(?!cable-geo).*\.json").respond(404)
    r = tg.run(date_str, base, log)
    assert len(r["cables"]) == 3 and len(r["landing_points"]) == 3
    por_id = {c["id"]: c for c in r["cables"]}
    brasil = [c for c in r["cables"] if c["landing_countries"] == ["Brazil"]]
    assert len(brasil) == 2 and brasil[0]["owners"] and brasil[0]["rfs_year"] == 2028
    sem_detalhe = [c for c in r["cables"] if c["length"] == ""]
    assert len(sem_detalhe) == 1 and sem_detalhe[0]["landing_countries"] == [] and sem_detalhe[0]["geometry"]
    assert r["landing_points"][0]["geometry"]["type"] == "Point"


@respx.mock
def test_telegeography_erro_no_geo_levanta(base, log, date_str):
    respx.get(f"{tg.API_BASE}/cable/cable-geo.json").respond(500)
    with pytest.raises(httpx.HTTPStatusError):
        tg.run(date_str, base, log)


# ── ANEEL SIGEL ────────────────────────────────────────────────────────────

@respx.mock
def test_aneel_colapsa_ciclo_extrai_tensao_extensao_e_nome(base, log, fx, date_str):
    respx.get(aneel.QUERY_URL).respond(200, json=json.loads(fx("aneel_sigel", "query-page.sample.json").read_text()))
    r = aneel.run(date_str, base, log)
    assert r["total"] == 4                                # a feição sem geometria é descartada
    f = r["features"][0]
    assert len(f["geometry"]["coordinates"]) == 4         # 12 vértices (×3) → 4 reais
    p = f["properties"]
    assert p["subestacao_origem"] == "SCHARLAU 2" and p["subestacao_destino"] == "CHARQUEADAS" and p["uf"] == "RS"
    assert p["tensao_kv"] == 230.0 and p["extensao_km"] == 72.96


@respx.mock
def test_aneel_nome_atipico_e_milhar_brasileiro(base, log, fx, date_str):
    respx.get(aneel.QUERY_URL).respond(200, json=json.loads(fx("aneel_sigel", "query-page.sample.json").read_text()))
    p = aneel.run(date_str, base, log)["features"][3]["properties"]
    assert p["uf"] == "PI/CE" and p["tensao_kv"] == 34.5 and p["extensao_km"] == 1234.5


@respx.mock
def test_aneel_pagina_por_resultoffset(base, log, fx, date_str, monkeypatch):
    monkeypatch.setattr(aneel, "PAGE_SIZE", 2)
    feats = json.loads(fx("aneel_sigel", "query-page.sample.json").read_text())["features"]
    offsets = []

    def handler(request):
        off = int(request.url.params["resultOffset"])
        offsets.append((off, request.url.params["f"]))
        return httpx.Response(200, json={"features": feats[off:off + 2]})

    respx.get(aneel.QUERY_URL).mock(side_effect=handler)
    r = aneel.run(date_str, base, log)
    assert offsets == [(0, "json"), (2, "json"), (4, "json")] and r["total"] == 4


@respx.mock
def test_aneel_erro_no_corpo_levanta(base, log, date_str):
    respx.get(aneel.QUERY_URL).respond(200, json={"error": {"code": 400, "message": "boom"}})
    with pytest.raises(RuntimeError, match="SIGEL query error"):
        aneel.run(date_str, base, log)


@pytest.mark.parametrize("coords, esperado", [
    ([[1, 1], [2, 2], [1, 1], [2, 2]], [[1, 1], [2, 2]]),
    ([[1, 1], [2, 2], [3, 3]], [[1, 1], [2, 2], [3, 3]]),                    # sem repetição
    ([[1, 1], [2, 2]], [[1, 1], [2, 2]]),
    ([[1, 1], [2, 2], [3, 3]] * 4, [[1, 1], [2, 2], [3, 3]]),
])
def test_aneel_dedupe_ciclo(coords, esperado):
    assert aneel._dedupe_repeated_cycle(coords) == esperado


def test_aneel_multilinha_e_geometria_vazia():
    g = aneel._esri_paths_to_geometry({"paths": [[[0, 0], [1, 1]], [[2, 2], [3, 3]]]})
    assert g["type"] == "MultiLineString" and len(g["coordinates"]) == 2
    assert aneel._esri_paths_to_geometry({}) is None


@pytest.mark.parametrize("raw, esperado", [("1.234,5", 1234.5), ("230", 230.0), ("72,96", 72.96), ("x", None)])
def test_aneel_parse_float_br(raw, esperado):
    assert aneel._parse_float_br(raw) == esperado


# ── IBGE BC250 (shapefile binário via HTTP Range) ──────────────────────────

def _shapefile_members(fx):
    return {f"BC250/rod_trecho_rodoviario_l.{ext}": fx("ibge_bc250", f"rod_trecho_rodoviario_l.{ext}").read_bytes()
            for ext in ("shp", "shx", "dbf")}


@respx.mock
def test_ibge_parse_dbf_e_shp_normalizam_tres_trechos(base, log, fx, date_str):
    members = {f"rod_trecho_rodoviario_l.{ext}": fx("ibge_bc250", f"rod_trecho_rodoviario_l.{ext}").read_bytes() for ext in ("shp", "shx", "dbf")}
    mount_range_zip(respx, ibge.ZIP_URL, members)
    r = ibge.run(date_str, base, log)
    assert r["total"] == 3
    f = r["features"][0]
    assert f["geometry"]["type"] == "LineString" and len(f["geometry"]["coordinates"]) >= 2
    props = f["properties"]
    assert set(props) >= {"tipo_via", "jurisdicao", "administracao", "revestimento", "sigla", "pavimentada", "nr_pistas"}
    assert isinstance(props["pavimentada"], (bool, type(None)))
    assert read_gz(base / "normalized" / date_str / "summary" / "ibge_rodovias.json.gz")["total"] == 3


@respx.mock
def test_ibge_zip_sem_membros_levanta(base, log, date_str):
    mount_range_zip(respx, ibge.ZIP_URL, {"outro.txt": b"x"})
    with pytest.raises(RuntimeError, match="membros do shapefile"):
        ibge.run(date_str, base, log)


@pytest.mark.parametrize("raw, esperado", [("pavimentado", True), ("Pavimentado", True), ("Sem revestimento (leito natural)", False),
                                           ("Primário (solto)", False), ("", None), ("outro", None)])
def test_ibge_pavimentada(raw, esperado):
    assert ibge._pavimentada(raw) is esperado


@pytest.mark.parametrize("raw, esperado", [("2", 2), ("80.5", 80.5), ("*", None), ("", None), ("abc", None), ("60*", 60)])
def test_ibge_to_number(raw, esperado):
    assert ibge._to_number(raw) == esperado


def test_ibge_registro_sem_geometria_e_descartado():
    assert ibge._normalize_record(None, {"sigla": "BR-101"}) is None
