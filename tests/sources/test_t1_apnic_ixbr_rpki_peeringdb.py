# SPDX-License-Identifier: AGPL-3.0-or-later
"""T1 — APNIC v6pop, dashboard IX.br, Routinator (RPKI) e PeeringDB (net/netixlan/poc)."""
import io
import json
import os
import time
import urllib.error

import httpx
import pytest
import respx

from sources.apnic_pop import collect as apnic_pop
from sources.ixbr_api import collect as ixbr_api
from sources.peeringdb_contacts import collect as peeringdb_contacts
from sources.peeringdb_ixps import collect as peeringdb_ixps
from sources.peeringdb_networks import collect as peeringdb_networks
from sources.rpki_collector import collect as rpki_collector
from tests.sources.conftest import read_gz, volatile, write_gz


# ── APNIC v6pop (urllib) ───────────────────────────────────────────────────

def test_apnic_pop_extrai_usuarios_por_as(base, log, fx, date_str, monkeypatch):
    html = fx("apnic_pop", "v6pop.sample.html").read_bytes()
    monkeypatch.setattr(apnic_pop, "_get", lambda url: html)
    r = apnic_pop.run(date_str, base, log)
    assert r == {"asns": 6}
    d = read_gz(base / "normalized" / date_str / "summary" / "apnic_pop.json.gz")
    assert d["window_days"] == 60 and d["date"] == date_str
    a = d["asns"]["28573"]
    assert a == {"users": 19776373, "users_pct_cc": 12.05, "v6_users": 16249239, "v6_pct_as": 82.16}
    assert d["asns"]["26599"]["users"] == 12939374


def test_apnic_pop_grava_html_bruto(base, log, fx, date_str, monkeypatch):
    html = fx("apnic_pop", "v6pop.sample.html").read_bytes()
    monkeypatch.setattr(apnic_pop, "_get", lambda url: html)
    apnic_pop.run(date_str, base, log)
    assert (base / "raw" / date_str / f"apnic_v6pop-{date_str}.html").read_bytes() == html


def test_apnic_pop_sem_tabela_nao_grava_normalizado(base, log, date_str, monkeypatch):
    monkeypatch.setattr(apnic_pop, "_get", lambda url: b"<html>manutencao</html>")
    assert apnic_pop.run(date_str, base, log) == {"asns": 0}
    assert not (base / "normalized").exists()


# ── IX.br dashboard (urllib) ───────────────────────────────────────────────

class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_ixbr_fetch_members(fx, monkeypatch):
    body = fx("ixbr_api", "generate_json.sample.json").read_bytes()
    seen = {}

    def fake(url, timeout=0):
        seen["url"] = url
        return _Resp(body)

    monkeypatch.setattr(ixbr_api.urllib.request, "urlopen", fake)
    r = ixbr_api.fetch_ixbr_members("sp")
    assert seen["url"] == "https://dashboard.ix.br/generate_json?ixp=sp"
    assert r["ixp"] == "sp" and r["members_count"] == 6
    assert r["members"][0] == {"asn": 42, "name": "AS42"}


def test_ixbr_membro_sem_asnum_e_ignorado(monkeypatch):
    body = json.dumps({"member_list": [{"asnum": "64500", "name": "A"}, {"name": "sem asn"}]}).encode()
    monkeypatch.setattr(ixbr_api.urllib.request, "urlopen", lambda url, timeout=0: _Resp(body))
    assert ixbr_api.fetch_ixbr_members("rj")["members"] == [{"asn": 64500, "name": "A"}]


def test_ixbr_collect_ixp_grava_raw(base, log, date_str, monkeypatch, fx):
    body = fx("ixbr_api", "generate_json.sample.json").read_bytes()
    monkeypatch.setattr(ixbr_api.urllib.request, "urlopen", lambda url, timeout=0: _Resp(body))
    r = ixbr_api.collect_ixp("sp", date_str, base, log)
    assert r == {"status": "ok", "members_count": 6}
    saved = json.loads((base / "raw" / date_str / "sp" / "ixbr_members.json").read_text())
    assert saved["members_count"] == 6 and saved["ixp"] == "sp"


def test_ixbr_collect_ixp_erro_http_nao_levanta(base, log, date_str, monkeypatch):
    def boom(url, timeout=0):
        raise urllib.error.HTTPError(url, 503, "indisponivel", {}, None)

    monkeypatch.setattr(ixbr_api.urllib.request, "urlopen", boom)
    r = ixbr_api.collect_ixp("sp", date_str, base, log)
    assert r["status"] == "error"
    assert not (base / "raw" / date_str / "sp" / "ixbr_members.json").exists()


def test_ixbr_run_filtra_por_codigo(base, log, date_str, monkeypatch, fx):
    body = fx("ixbr_api", "generate_json.sample.json").read_bytes()
    monkeypatch.setattr(ixbr_api.urllib.request, "urlopen", lambda url, timeout=0: _Resp(body))
    monkeypatch.setattr(ixbr_api, "load_ixps", lambda: [{"code": "sp"}, {"code": "rj"}, {"code": "mg"}])
    r = ixbr_api.run(date_str, base, ["sp", "mg"], log)
    assert [x["ixp"] for x in r] == ["sp", "mg"] and all(x["status"] == "ok" for x in r)


# ── RPKI / Routinator avulso ──────────────────────────────────────────────────────

def _rpki_arquivo(tmp_path, payload, idade_h=0.0):
    p = tmp_path / "vrps.json"
    p.write_text(json.dumps(payload))
    if idade_h:
        t = time.time() - idade_h * 3600
        os.utime(p, (t, t))
    return p


def test_rpki_le_arquivo_e_normaliza(fx, log, tmp_path):
    payload = json.loads(fx("rpki", "routinator-json.sample.json").read_text())
    data = rpki_collector.ler_rpki_json(_rpki_arquivo(tmp_path, payload), log)
    vrps = rpki_collector.normalize_vrps(data["roas"])
    assert len(vrps) == len(payload["roas"]) and vrps[0]["asn"] == 262589
    assert set(vrps[0]) == {"asn", "prefix", "maxLength", "ta"} and isinstance(vrps[0]["asn"], int)
    aspas = rpki_collector.normalize_aspas(data["aspas"])
    assert all(isinstance(a["customer"], int) and all(isinstance(p, int) for p in a["providers"]) for a in aspas)


def test_rpki_arquivo_ausente_velho_ou_invalido_devolve_none(fx, log, tmp_path):
    payload = json.loads(fx("rpki", "routinator-json.sample.json").read_text())
    assert rpki_collector.ler_rpki_json(tmp_path / "nao-existe.json", log) is None
    # Arquivo de ontem não vira RPKI de hoje (o avulso falhou e o anterior ficou).
    assert rpki_collector.ler_rpki_json(_rpki_arquivo(tmp_path, payload, idade_h=13), log, max_idade_h=12) is None
    assert rpki_collector.ler_rpki_json(_rpki_arquivo(tmp_path, {"roas": []}), log) is None
    (tmp_path / "vrps.json").write_text('{"roas": [')  # truncado
    assert rpki_collector.ler_rpki_json(tmp_path / "vrps.json", log) is None


@pytest.mark.parametrize("roa, expected", [
    ({"asn": "AS64500", "prefix": "10.0.0.0/24", "maxLength": 24, "ta": "lacnic"}, {"asn": 64500, "prefix": "10.0.0.0/24", "maxLength": 24, "ta": "lacnic"}),
    ({"asn": 64501, "prefix": "10.0.1.0/24", "max_length": 25, "ta": "ripe"}, {"asn": 64501, "prefix": "10.0.1.0/24", "maxLength": 25, "ta": "ripe"}),
])
def test_rpki_normalize_vrps(roa, expected):
    assert rpki_collector.normalize_vrps([roa]) == [expected]


def test_rpki_normalize_vrps_descarta_invalidos():
    assert rpki_collector.normalize_vrps([{"asn": "ASx", "prefix": "10.0.0.0/8"}, {"asn": "AS1", "prefix": ""}]) == []


def test_rpki_normalize_aspas_aceita_formas_de_provider():
    r = rpki_collector.normalize_aspas([{"customer": "AS10", "providers": ["AS1", 2, {"asn": "AS3"}, "lixo"], "tal": "ripe"}])
    assert r == [{"customer": 10, "providers": [1, 2, 3], "tal": "ripe"}]


def test_rpki_main_grava_listas_publicadas(base, fx, monkeypatch, date_str):
    payload = json.loads(fx("rpki", "routinator-json.sample.json").read_text())
    (base / "cache" / "rpki").mkdir(parents=True)
    (base / "cache" / "rpki" / "vrps.json").write_text(json.dumps(payload))
    monkeypatch.delenv("RPKI_JSON", raising=False)
    monkeypatch.setenv("DATA_DIR", str(base))
    assert rpki_collector.main(["--date", date_str, "--no-wait"]) == 0
    vrp = read_gz(base / "published" / date_str / "rpki" / "vrp_list.json.gz")
    aspa = read_gz(base / "published" / date_str / "rpki" / "aspa_list.json.gz")
    assert len(vrp) == len(payload["roas"]) and len(aspa) == len(payload["aspas"])


# ── PeeringDB ──────────────────────────────────────────────────────────────

def test_peeringdb_normalize_net_mantem_so_campos_relevantes(fx):
    net = json.loads(fx("peeringdb", "net.sample.json").read_text())["data"][0]
    out = peeringdb_networks._normalize_net(net)
    assert set(out) <= peeringdb_networks._KEEP
    assert out["asn"] == net["asn"] and "org_id" not in out and "notes" not in out
    assert isinstance(out.get("policy_ratio", False), bool)


def test_peeringdb_normalize_net_omite_vazios_e_converte_bool():
    out = peeringdb_networks._normalize_net({"asn": 1, "name": "", "policy_ratio": 1, "policy_contracts": 0, "info_type": None})
    assert out == {"asn": 1, "policy_ratio": True, "policy_contracts": False}


@respx.mock
def test_peeringdb_networks_run(base, log, fx, date_str):
    write_gz(base / "normalized" / date_str / "summary" / "lacnic_delegated.json.gz", {"br_asns": [1251, 28573, 99999]})
    respx.get(f"{peeringdb_networks.PDB_BASE}/net").respond(200, json=json.loads(fx("peeringdb", "net.sample.json").read_text()))
    r = peeringdb_networks.run(date_str, base, log)
    assert r["total_br_asns"] == 3 and r["pdb_registered"] == 5
    assert "1251" in r["networks"]
    raw = json.loads((base / "raw" / date_str / "summary" / f"peeringdb-networks-{date_str}.json").read_text())
    assert len(raw) == 5


def test_peeringdb_networks_sem_lacnic_nao_roda(base, log, date_str):
    assert peeringdb_networks.run(date_str, base, log) == {}


@respx.mock
def test_peeringdb_networks_retenta_em_429(base, log, fx, date_str, monkeypatch):
    monkeypatch.setattr(peeringdb_networks.time, "sleep", lambda s: None)
    write_gz(base / "normalized" / date_str / "summary" / "lacnic_delegated.json.gz", {"br_asns": [1251]})
    route = respx.get(f"{peeringdb_networks.PDB_BASE}/net")
    route.side_effect = [httpx.Response(429, headers={"Retry-After": "1"}), httpx.Response(200, json=json.loads(fx("peeringdb", "net.sample.json").read_text()))]
    r = peeringdb_networks.run(date_str, base, log)
    assert r["pdb_registered"] == 5 and route.call_count == 2


@respx.mock
def test_peeringdb_networks_falha_alto_quando_o_rate_limit_nao_passa(base, log, date_str, monkeypatch):
    """`peeringdb_networks`: devolver [] depois do 429 gravava um snapshot com pdb_registered=False para todos."""
    monkeypatch.setattr(peeringdb_networks.time, "sleep", lambda s: None)
    write_gz(base / "normalized" / date_str / "summary" / "lacnic_delegated.json.gz", {"br_asns": [1251]})
    route = respx.get(f"{peeringdb_networks.PDB_BASE}/net").respond(429, headers={"Retry-After": "1"})
    with pytest.raises(peeringdb_networks.RateLimitedError):
        peeringdb_networks.run(date_str, base, log)
    assert route.call_count == peeringdb_networks._MAX_ATTEMPTS
    assert not (base / "normalized" / date_str / "summary" / "peeringdb_networks.json.gz").exists()


@respx.mock
def test_peeringdb_networks_sanidade_recusa_cobertura_abaixo_do_limite(base, log, date_str):
    asns = list(range(1000, 1100))                       # 100 ASNs BR; o PeeringDB devolve 5 (5% < 20%)
    write_gz(base / "normalized" / date_str / "summary" / "lacnic_delegated.json.gz", {"br_asns": asns})
    respx.get(f"{peeringdb_networks.PDB_BASE}/net").respond(
        200, json={"data": [{"asn": a, "name": f"AS{a}"} for a in asns[:5]]})
    with pytest.raises(RuntimeError, match="sanidade"):
        peeringdb_networks.run(date_str, base, log)
    assert not (base / "normalized" / date_str / "summary" / "peeringdb_networks.json.gz").exists()


@respx.mock
def test_peeringdb_ixps_run_gera_indices_por_ixp_e_por_asn(base, log, fx, date_str, monkeypatch):
    monkeypatch.setattr(peeringdb_ixps.time, "sleep", lambda s: None)
    monkeypatch.setattr(peeringdb_ixps, "load_peeringdb_ixps_config", lambda: {
        "external": [{"code": "decix-sp", "name": "DE-CIX SP", "city": "São Paulo", "country": "BR", "pdb_ix_id": 4642}],
        "ixbr": [{"code": "sp", "pdb_ix_id": 100}],
    })
    sample = json.loads(fx("peeringdb", "netixlan.sample.json").read_text())
    respx.get(f"{peeringdb_ixps.PDB_BASE}/netixlan").respond(200, json=sample)
    r = peeringdb_ixps.run(date_str, base, log)
    ext = r["external_ixps"]["decix-sp"]
    assert ext["member_count"] == 5 and [m["asn"] for m in ext["members"]] == sorted(m["asn"] for m in ext["members"])
    assert r["ixbr_ixps"]["sp"]["member_count"] == 5 and isinstance(r["ixbr_ixps"]["sp"]["asns"][0], int)
    any_asn = next(iter(r["per_asn"]))
    assert r["per_asn"][any_asn] == {"external": ["decix-sp"], "ixbr": ["sp"]}
    assert all("name" not in m for m in ext["members"])        # o `name` do netixlan é o nome do PTT, não o da rede


def test_peeringdb_contacts_normalize_poc_mapeia_net_id(fx):
    poc = json.loads(fx("peeringdb", "poc.sample.json").read_text())["data"][0]
    out = peeringdb_contacts._normalize_poc(poc, {poc["net_id"]: 1251})
    assert out["asn"] == 1251 and out["role"] == poc["role"] and out["email"].endswith("@example.org")
    assert "created" not in out and "net_id" not in out
    assert peeringdb_contacts._normalize_poc(poc, {}) is None


@respx.mock
def test_peeringdb_contacts_run(base, log, fx, date_str, monkeypatch):
    monkeypatch.setattr(peeringdb_contacts.time, "sleep", lambda s: None)
    write_gz(base / "normalized" / date_str / "summary" / "peeringdb_networks.json.gz", {"networks": {"1251": {}}})
    nets = json.loads(fx("peeringdb", "net.sample.json").read_text())["data"]
    pocs = json.loads(fx("peeringdb", "poc.sample.json").read_text())
    net_id = next(p["net_id"] for p in pocs["data"] if p["visible"] == "Public")

    pedidos_poc = []

    def route(request):
        if request.url.path.endswith("/net"):
            return httpx.Response(200, json={"data": [{"id": net_id, "asn": 1251}]})
        pedidos_poc.append(dict(request.url.params))
        # a API do PeeringDB aplica o filtro `visible`; o mock também, para o teste refletir o que chega de verdade
        vis = request.url.params.get("visible")
        return httpx.Response(200, json={"data": [p for p in pocs["data"] if vis is None or p["visible"] == vis]})

    respx.get(url__regex=rf"{peeringdb_contacts.PDB_BASE}/(net|poc).*").mock(side_effect=route)
    r = peeringdb_contacts.run(date_str, base, log)
    # Só POCs `Public`: `Users` é restrito pelo dono da rede a usuários do PeeringDB
    assert pedidos_poc and all(q.get("visible") == "Public" and "visible__in" not in q for q in pedidos_poc)
    esperados = [p for p in pocs["data"] if p["net_id"] == net_id and p["visible"] == "Public"]
    assert esperados and len(r["contacts"]["1251"]) == len(esperados)
    assert all("asn" not in c and c["visible"] == "Public" for c in r["contacts"].get("1251", []))
    # o bruto com nome, e-mail e telefone não vai para raw/: só o manifesto das requisições
    rd = base / "raw" / date_str / "summary"
    assert not (rd / f"peeringdb-contacts-{date_str}.json").exists()
    manifesto = (rd / f"peeringdb-contacts-requisicoes-{date_str}.json").read_text()
    assert "@" not in manifesto and json.loads(manifesto)[0]["recurso"] == "poc"


def _cfg_um_ixp(monkeypatch):
    monkeypatch.setattr(peeringdb_ixps.time, "sleep", lambda s: None)
    monkeypatch.setattr(peeringdb_ixps, "load_peeringdb_ixps_config", lambda: {
        "external": [{"code": "decix-sp", "name": "DE-CIX SP", "city": "São Paulo", "country": "BR", "pdb_ix_id": 4642}],
        "ixbr": [{"code": "sp", "pdb_ix_id": 100}]})


@respx.mock
def test_peeringdb_ixps_retenta_em_timeout_e_conclui(base, log, fx, date_str, monkeypatch):
    """Um read timeout não pode abortar o `peeringdb_ixps` (e o pipeline inteiro)."""
    _cfg_um_ixp(monkeypatch)
    sample = json.loads(fx("peeringdb", "netixlan.sample.json").read_text())
    route = respx.get(f"{peeringdb_ixps.PDB_BASE}/netixlan")
    route.side_effect = [httpx.ReadTimeout("The read operation timed out"), httpx.Response(200, json=sample),
                         httpx.Response(200, json=sample)]
    r = peeringdb_ixps.run(date_str, base, log)
    assert r["external_ixps"]["decix-sp"]["member_count"] == 5 and route.call_count == 3


@respx.mock
def test_peeringdb_ixps_falha_alto_quando_nunca_responde(base, log, date_str, monkeypatch):
    """Dois 429 não podem devolver [] e gravar o IXP sem membros em silêncio."""
    _cfg_um_ixp(monkeypatch)
    route = respx.get(f"{peeringdb_ixps.PDB_BASE}/netixlan").respond(429, headers={"Retry-After": "1"})
    with pytest.raises(peeringdb_ixps.RateLimitedError):
        peeringdb_ixps.run(date_str, base, log)
    assert route.call_count == peeringdb_ixps._MAX_ATTEMPTS
    assert not (base / "normalized" / date_str / "summary" / "peeringdb_ixps.json.gz").exists()


@respx.mock
def test_peeringdb_networks_retenta_em_timeout(base, log, fx, date_str, monkeypatch):
    monkeypatch.setattr(peeringdb_networks.time, "sleep", lambda s: None)
    write_gz(base / "normalized" / date_str / "summary" / "lacnic_delegated.json.gz", {"br_asns": [1251]})
    route = respx.get(f"{peeringdb_networks.PDB_BASE}/net")
    route.side_effect = [httpx.ConnectTimeout("timeout"), httpx.Response(200, json=json.loads(fx("peeringdb", "net.sample.json").read_text()))]
    assert peeringdb_networks.run(date_str, base, log)["pdb_registered"] == 5 and route.call_count == 2


@respx.mock
def test_peeringdb_contacts_get_repete_em_timeout(log, monkeypatch):
    monkeypatch.setattr(peeringdb_contacts.time, "sleep", lambda s: None)
    route = respx.get(f"{peeringdb_contacts.PDB_BASE}/poc")
    route.side_effect = [httpx.ReadTimeout("timeout"), httpx.Response(200, json={"data": [{"net_id": 1}]})]
    with httpx.Client() as client:
        assert peeringdb_contacts._get(client, f"{peeringdb_contacts.PDB_BASE}/poc", {}, log) == [{"net_id": 1}]
    assert route.call_count == 2


@respx.mock
def test_peeringdb_contacts_get_falha_alto_em_vez_de_devolver_vazio(log, monkeypatch):
    """Dois 429 não podem devolver [] e sumir com o lote de contatos em silêncio."""
    monkeypatch.setattr(peeringdb_contacts.time, "sleep", lambda s: None)
    route = respx.get(f"{peeringdb_contacts.PDB_BASE}/poc").respond(429, headers={"Retry-After": "1"})
    with httpx.Client() as client, pytest.raises(peeringdb_contacts.RateLimitedError):
        peeringdb_contacts._get(client, f"{peeringdb_contacts.PDB_BASE}/poc", {}, log)
    assert route.call_count == peeringdb_contacts._MAX_ATTEMPTS


def test_peeringdb_ixps_normaliza_portas_do_ixbr_e_refaz_do_bruto(base, log, date_str, monkeypatch):
    """O normalizado do IX.br guarda as portas (ASN, velocidade); `--do-bruto` refaz do bruto, sem rede."""
    import json
    cfg = {"external": [{"code": "ext", "name": "Ext IX", "pdb_ix_id": 9}], "ixbr": [{"code": "sp", "pdb_ix_id": 171}]}
    bruto = {"date": date_str,
             "external": {"ext": {"member_count": 1, "members": [{"asn": 64500, "name": "A", "speed": 10000}]}},
             "ixbr": {"sp": {"member_count": 2, "members": [{"asn": 64500, "name": "A", "speed": 100000}, {"asn": 64501, "name": "B", "speed": 0}]}}}
    n = peeringdb_ixps.normalizar(bruto, cfg, date_str)
    assert n["ixbr_ixps"]["sp"]["portas"] == [[64500, 100000], [64501, 0]]
    assert n["ixbr_ixps"]["sp"]["asns"] == [64500, 64501]
    assert n["per_asn"]["64500"] == {"external": ["ext"], "ixbr": ["sp"]}
    raw_dir = base / "raw" / date_str / "summary"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"peeringdb-ixps-{date_str}.json").write_text(json.dumps(bruto), encoding="utf-8")
    monkeypatch.setattr(peeringdb_ixps, "load_peeringdb_ixps_config", lambda: cfg)
    feito = peeringdb_ixps.do_bruto(date_str, base, log)
    assert feito["ixbr_ixps"]["sp"]["portas"][0] == [64500, 100000]
