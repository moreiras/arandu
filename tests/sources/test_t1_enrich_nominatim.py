# SPDX-License-Identifier: AGPL-3.0-or-later
"""T1 — geocodificação por Nominatim/BrasilAPI: outorgas (SCM/SMP/STFC/SeAC), CNPJ de ASN e ASN internacional."""
import json

import httpx
import pytest
import respx

from sources.anatel_scm import collect as anatel_scm
from sources.anatel_outorgas import geo as outorgas_geo
from sources.cnpj_geo import enrich as cnpj_geo
from sources.peeringdb_intl_geo import enrich as peeringdb_intl_geo
from sources.scm_geo import enrich as scm_geo
from sources.seac_geo import enrich as seac_geo
from sources.smp_geo import enrich as smp_geo
from sources.stfc_geo import enrich as stfc_geo
from tests.sources.conftest import read_gz, write_gz

NOM = "https://nominatim.test/search"


@pytest.fixture(autouse=True)
def sem_pausas(monkeypatch):
    monkeypatch.setattr(outorgas_geo, "NOMINATIM_URL", NOM)       # lógica única dos 4 enriquecedores de outorgas
    monkeypatch.setattr(outorgas_geo, "NOMINATIM_DELAY", 0.0)
    monkeypatch.setattr(cnpj_geo, "NOMINATIM_URL", NOM)
    monkeypatch.setattr(cnpj_geo, "NOMINATIM_DELAY", 0.0)
    monkeypatch.setattr(peeringdb_intl_geo, "NOMINATIM_URL", NOM)
    monkeypatch.setattr(peeringdb_intl_geo, "NOMINATIM_DELAY", 0.0)
    monkeypatch.setattr(peeringdb_intl_geo.time, "sleep", lambda s: None)


@pytest.fixture()
def nominatim_ok(fx):
    return json.loads(fx("nominatim", "search.sample.json").read_text())


# ── 4 enriquecedores de outorgas (mesma lógica) ────────────────────────────

GEO = [
    (scm_geo, "scms", "scm"),
    (smp_geo, "smps", "smp"),
    (stfc_geo, "stfcs", "stfc"),
    (seac_geo, "seacs", "seac"),
]


def _records(fx):
    """Registros normalizados de verdade: sai do parser do coletor sobre o CSV de amostra."""
    recs = anatel_scm._parse_csv(fx("anatel_outorgas", "prestadoras_servicos_telecomunicacoes.sample.csv").read_bytes())
    assert recs and recs[0]["logradouro"] and recs[0]["municipio"] and recs[0]["cep"]
    return recs[:2]


def _put(base, date_str, key, name, recs):
    write_gz(base / "normalized" / date_str / "summary" / f"anatel_{name}.json.gz", {key: recs})


@pytest.mark.parametrize("mod, key, name", GEO, ids=[g[2] for g in GEO])
@respx.mock
def test_endereco_completo_vira_exact_address(mod, key, name, base, log, fx, date_str, nominatim_ok):
    recs = _records(fx)
    _put(base, date_str, key, name, recs)
    route = respx.get(NOM).respond(200, json=nominatim_ok)
    r = mod.run(date_str, base, False, log)
    assert r["total"] == 2 and r["geolocated"] == 2 and r[key][0]["geo_confidence"] == "exact_address"
    assert r[key][0]["lat"] == -23.5614 and r[key][0]["geo_source"] == "nominatim"
    q = route.calls[0].request.url.params
    assert q["street"].startswith(recs[0]["logradouro"]) and q["city"] == recs[0]["municipio"]
    assert q["countrycodes"] == "br" and q["format"] == "jsonv2"
    assert set(r["by_cnpj"]) == {x["cnpj"] for x in recs}
    assert read_gz(base / "normalized" / date_str / "summary" / f"anatel_{name}_geo.json.gz")["geolocated"] == 2


@pytest.mark.parametrize("mod, key, name", GEO, ids=[g[2] for g in GEO])
@respx.mock
def test_cai_para_cep_e_depois_municipio(mod, key, name, base, log, fx, date_str, nominatim_ok):
    _put(base, date_str, key, name, _records(fx)[:1])
    seq = []

    def handler(request):
        p = request.url.params
        seq.append("street" if "street" in p else "cep" if "postalcode" in p else "city")
        return httpx.Response(200, json=[] if seq[-1] != "city" else nominatim_ok)

    respx.get(NOM).mock(side_effect=handler)
    r = mod.run(date_str, base, False, log)
    assert seq == ["street", "cep", "city"] and r[key][0]["geo_confidence"] == "city_centroid"


@pytest.mark.parametrize("mod, key, name", GEO, ids=[g[2] for g in GEO])
@respx.mock
def test_nao_encontrado_e_cacheado_como_unknown(mod, key, name, base, log, fx, date_str):
    _put(base, date_str, key, name, _records(fx)[:1])
    route = respx.get(NOM).respond(200, json=[])
    r = mod.run(date_str, base, False, log)
    assert r[key][0]["lat"] is None and r[key][0]["geo_confidence"] == "unknown" and r["unknown"] == 1
    calls = route.call_count
    mod.run(date_str, base, False, log)                          # 2ª execução: vem do cache
    assert route.call_count == calls


@pytest.mark.parametrize("mod, key, name", GEO, ids=[g[2] for g in GEO])
@respx.mock
def test_erro_de_rede_nao_vai_para_o_cache(mod, key, name, base, log, fx, date_str, nominatim_ok):
    _put(base, date_str, key, name, _records(fx)[:1])
    respx.get(NOM).respond(503)
    r = mod.run(date_str, base, False, log)
    assert r["unknown"] == 1 and r[key][0]["lat"] is None
    assert outorgas_geo._load_cache(base, name) == {}                           # falha transitória não vira "não encontrado"
    respx.get(NOM).respond(200, json=nominatim_ok)
    assert mod.run(date_str, base, False, log)["geolocated"] == 1


@pytest.mark.parametrize("mod, key, name", GEO, ids=[g[2] for g in GEO])
@respx.mock
def test_cache_hit_nao_consulta_e_force_ignora(mod, key, name, base, log, fx, date_str, nominatim_ok):
    _put(base, date_str, key, name, _records(fx)[:1])
    route = respx.get(NOM).respond(200, json=nominatim_ok)
    mod.run(date_str, base, False, log)
    n = route.call_count
    r = mod.run(date_str, base, False, log)
    assert route.call_count == n and r["cached"] == 1
    mod.run(date_str, base, True, log)
    assert route.call_count > n


@pytest.mark.parametrize("mod, key, name", GEO, ids=[g[2] for g in GEO])
@respx.mock
def test_semeia_do_cache_de_cnpj_sem_chamar_nominatim(mod, key, name, base, log, fx, date_str):
    recs = _records(fx)[:1]
    _put(base, date_str, key, name, recs)
    write_gz(base / "normalized" / "geo_cache" / "cnpj.json.gz",
             {recs[0]["cnpj"]: {"lat": -1.5, "lon": -2.5, "geo_confidence": "exact_address"}})
    route = respx.get(NOM).respond(200, json=[])
    r = mod.run(date_str, base, False, log)
    assert route.call_count == 0 and r[key][0]["lat"] == -1.5 and r[key][0]["geo_source"] == "cnpj_cache"


@pytest.mark.parametrize("mod, key, name", GEO, ids=[g[2] for g in GEO])
def test_entrada_ausente_levanta(mod, key, name, base, log, date_str):
    with pytest.raises(FileNotFoundError):
        mod.run(date_str, base, False, log)


def test_scm_checkpoint_publica_so_o_que_esta_no_cache(base, log, fx, date_str):
    recs = _records(fx)
    cache = {outorgas_geo._cache_key(recs[0]): {"lat": 1.0, "lon": 2.0, "geo_confidence": "cep_centroid", "geo_source": "nominatim",
                                           "cache_version": outorgas_geo.CACHE_VERSION, "cached_at": "x"}}
    out = outorgas_geo._flush_output(scm_geo.SERVICO, date_str, base, recs, cache, log)
    assert out["geolocated"] == 1 and out["unknown"] == 1 and out["checkpoint"] is True
    assert out["scms"][0]["lat"] == 1.0 and out["scms"][1]["lat"] is None


# ── cnpj_geo (BrasilAPI + Nominatim) ───────────────────────────────────────

@pytest.fixture()
def orgs(base, date_str, fx):
    cnpjs = list(json.loads(fx("brasilapi", "cnpj.sample.json").read_text()))
    write_gz(base / "normalized" / date_str / "summary" / "orgs.json.gz", {"orgs": {
        "64500": {"name": "Org A", "cnpj": cnpjs[0]},
        "64501": {"name": "Org B", "cnpj": cnpjs[1]},
        "64502": {"name": "Sem CNPJ", "cnpj": ""},
        "64503": {"name": "CNPJ inexistente", "cnpj": "00000000000191"},
    }})
    return cnpjs


def _brasilapi(respx_mock, fx):
    data = json.loads(fx("brasilapi", "cnpj.sample.json").read_text())

    def handler(request):
        cnpj = request.url.path.rsplit("/", 1)[-1]
        if cnpj in data:
            return httpx.Response(200, json=data[cnpj])
        return httpx.Response(404, json={"message": "CNPJ não encontrado"})

    respx_mock.get(url__regex=r"https://brasilapi\.com\.br/api/cnpj/v1/\d+").mock(side_effect=handler)
    return data


@respx.mock
def test_cnpj_geo_extrai_cadastro_e_geocodifica(base, log, fx, orgs, date_str, nominatim_ok):
    data = _brasilapi(respx, fx)
    respx.get(NOM).respond(200, json=nominatim_ok)
    r = cnpj_geo.run(date_str, base, False, log)
    a = r["orgs"]["64500"]
    assert a["razao_social"] == data[orgs[0]]["razao_social"] and a["geo_confidence"] == "exact_address" and a["lat"] == -23.5614
    assert a["cep"].isdigit() and a["email"] == "contato@example.org" and a["name"] == "Org A"
    assert r["orgs"]["64502"]["geo_confidence"] == "unknown" and r["orgs"]["64502"]["lat"] is None     # sem CNPJ
    assert r["orgs"]["64503"]["error"] == "brasilapi_not_found"
    assert (r["total"], r["geolocated"], r["unknown"]) == (4, 2, 2)


@respx.mock
def test_cnpj_geo_cache_versionado(base, log, fx, orgs, date_str, nominatim_ok):
    _brasilapi(respx, fx)
    route = respx.get(NOM).respond(200, json=nominatim_ok)
    cnpj_geo.run(date_str, base, False, log)
    n = route.call_count
    r = cnpj_geo.run(date_str, base, False, log)
    assert route.call_count == n and r["cached"] >= 2
    cache = read_gz(base / "normalized" / "geo_cache" / "cnpj.json.gz")
    cache[orgs[0]]["cache_version"] = "1"                         # versão antiga é descartada
    write_gz(base / "normalized" / "geo_cache" / "cnpj.json.gz", cache)
    cnpj_geo.run(date_str, base, False, log)
    assert route.call_count > n


@respx.mock
def test_cnpj_geo_falha_transitoria_da_brasilapi_e_cacheada_como_desconhecida(base, log, fx, orgs, date_str):
    """Caracterização (comportamento atual): ao contrário de scm_geo, aqui um 503 vira 'não encontrado' e é
    gravado no cache — fica sem geolocalização até o CACHE_VERSION mudar ou rodar com --force."""
    respx.get(url__regex=r"https://brasilapi\.com\.br/api/cnpj/v1/\d+").respond(503)
    r = cnpj_geo.run(date_str, base, False, log)
    assert r["orgs"]["64500"]["error"] == "brasilapi_not_found"
    assert orgs[0] in read_gz(base / "normalized" / "geo_cache" / "cnpj.json.gz")


def test_cnpj_geo_sem_orgs_levanta(base, log, date_str):
    with pytest.raises(FileNotFoundError):
        cnpj_geo.run(date_str, base, False, log)


def test_cnpj_geo_extract_fields_normaliza_cep_e_vazios():
    f = cnpj_geo._extract_fields({"cep": "05001-200", "logradouro": None, "municipio": "SAO PAULO", "uf": "SP", "cnaes_secundarios": None})
    assert f["cep"] == "05001200" and f["logradouro"] == "" and f["cnaes_secundarios"] == [] and f["uf"] == "SP"


# ── peeringdb_intl_geo ─────────────────────────────────────────────────────

PDB = peeringdb_intl_geo.PDB_BASE


@pytest.fixture()
def intl(base, date_str):
    write_gz(base / "normalized" / date_str / "summary" / "lacnic_delegated.json.gz", {"br_asns": [64500]})
    d = base / "raw" / date_str / "sp"
    d.mkdir(parents=True)
    (d / "ixbr_members.json").write_text(json.dumps({"members": [{"asn": 64500}, {"asn": 65001}, {"asn": 65002}, {"asn": 65003}, {"asn": 65004}]}))


def _pdb(respx_mock, fx):
    org = json.loads(fx("peeringdb", "org.sample.json").read_text())
    nets = {"data": [{"asn": 65001, "name": "Rede Frankfurt", "org_id": 9001},
                     {"asn": 65002, "name": "Rede Buenos Aires", "org_id": 9002},
                     {"asn": 65003, "name": "Rede Sem Cidade", "org_id": 9003}]}      # 65004 não existe no PeeringDB
    respx_mock.get(f"{PDB}/net").respond(200, json=nets)
    respx_mock.get(f"{PDB}/org").respond(200, json=org)


@respx.mock
def test_intl_usa_coordenadas_da_org_depois_nominatim_depois_unknown(base, log, fx, intl, date_str):
    _pdb(respx, fx)
    respx.get(NOM).respond(200, json=[{"lat": "-34.6", "lon": "-58.4"}])
    r = peeringdb_intl_geo.run(date_str, base, False, log)
    a = r["asns"]
    assert "64500" not in a and set(a) == {"65001", "65002", "65003", "65004"}                 # ASN BR fica de fora
    assert a["65001"]["geo_confidence"] == "org_coords" and a["65001"]["lat"] == 50.11 and a["65001"]["city"] == "Frankfurt"
    assert a["65002"]["geo_confidence"] == "city_centroid" and a["65002"]["lat"] == -34.6
    assert a["65003"]["geo_confidence"] == "unknown" and a["65003"]["lat"] is None
    assert a["65004"]["geo_confidence"] == "unknown"
    assert (r["total"], r["geolocated"]) == (4, 2)


@respx.mock
def test_intl_segunda_execucao_usa_caches(base, log, fx, intl, date_str):
    _pdb(respx, fx)
    nom = respx.get(NOM).respond(200, json=[{"lat": "-34.6", "lon": "-58.4"}])
    peeringdb_intl_geo.run(date_str, base, False, log)
    net_calls = [c for c in respx.calls if c.request.url.path.endswith("/net")]
    peeringdb_intl_geo.run(date_str, base, False, log)
    assert [c for c in respx.calls if c.request.url.path.endswith("/net")] == net_calls and nom.call_count == 1


def test_intl_sem_asns_grava_vazio(base, log, date_str):
    r = peeringdb_intl_geo.run(date_str, base, False, log)
    assert r["total"] == 0 and read_gz(base / "normalized" / date_str / "summary" / "geo_intl_asns.json.gz")["asns"] == {}


@respx.mock
def test_intl_peeringdb_fora_do_ar_nao_levanta(base, log, intl, date_str):
    respx.get(url__regex=rf"{PDB}/.*").respond(500)
    r = peeringdb_intl_geo.run(date_str, base, False, log)
    assert r["geolocated"] == 0 and r["total"] == 4


@pytest.mark.parametrize("mod, key, name", GEO, ids=[g[2] for g in GEO])
def test_checkpoint_vale_para_os_quatro_servicos(mod, key, name, base, log, fx, date_str, monkeypatch):
    """O --checkpoint existia só no SCM; a lógica única o dá aos quatro."""
    recs = _records(fx)
    _put(base, date_str, key, name, recs)
    cache = {outorgas_geo._cache_key(recs[0]): {"lat": 1.0, "lon": 2.0, "geo_confidence": "cep_centroid", "geo_source": "nominatim",
                                                "cache_version": outorgas_geo.CACHE_VERSION, "cached_at": "x"}}
    outorgas_geo._save_cache(base, name, cache)
    out = outorgas_geo._flush_output(mod.SERVICO, date_str, base, recs, outorgas_geo._load_cache(base, name), log)
    assert out["checkpoint"] is True and out["geolocated"] == 1 and key in out
    assert read_gz(base / "normalized" / date_str / "summary" / f"anatel_{name}_geo.json.gz")["checkpoint"] is True
