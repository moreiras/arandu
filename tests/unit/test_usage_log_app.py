# SPDX-License-Identifier: AGPL-3.0-or-later
"""T0 — o log de uso na aplicação real: o guard informa o tipo de usuário."""
import json

import pytest
from fastapi.testclient import TestClient

from api.usage_log import UsageLogMiddleware


@pytest.fixture(autouse=True)
def _sem_cache_de_diretorio(monkeypatch):
    # A app é um singleton de módulo; cada teste usa um DATA_DIR temporário diferente.
    monkeypatch.setattr(UsageLogMiddleware, "_DIR_TTL", 0.0)


def _lines(base):
    out = []
    for p in sorted((base / "ops" / "usage").glob("*.jsonl")):
        out += [json.loads(l) for l in p.read_text().splitlines()]
    return out


def test_guard_informa_tier_anonimo_e_allowlist(app_client):
    _, app, tmp_path = app_client
    c = TestClient(app, raise_server_exceptions=False)
    c.get("/api/v1/snapshots", headers={"X-Real-IP": "203.0.113.9"})
    c.get("/api/v1/snapshots", headers={"X-Real-IP": "203.0.113.129"})
    tiers = [r["tier"] for r in _lines(tmp_path) if r["route"] == "/api/v1/snapshots"]
    assert tiers == ["anon", "allowed"]


def test_resposta_barrada_pelo_guard_tambem_e_registrada(app_client):
    _, app, tmp_path = app_client
    c = TestClient(app, raise_server_exceptions=False)
    r = c.get("/api/v1/asns/64500/contacts", headers={"X-Real-IP": "203.0.113.9"})
    assert r.status_code == 401
    rec = [x for x in _lines(tmp_path) if "contacts" in x["route"]][0]
    assert rec["status"] == 401 and rec["tier"] == "anon"


def test_nenhum_ip_em_claro_no_arquivo(app_client):
    _, app, tmp_path = app_client
    TestClient(app, raise_server_exceptions=False).get("/api/v1/snapshots", headers={"X-Real-IP": "203.0.113.77"})
    raw = "".join(p.read_text() for p in (tmp_path / "ops" / "usage").glob("*.jsonl"))
    assert "203.0.113.77" not in raw


def test_nome_da_rota_tem_prefixo_e_template_na_app_real(app_client):
    # FastAPI >= 0.13x guarda a rota incluída sem o prefixo do include_router: sem o
    # tratamento em usage_log, o log trazia `/ixps` em vez de `/api/v1/ixps` (visto em produção).
    _, app, tmp_path = app_client
    c = TestClient(app, raise_server_exceptions=False)
    for p in ("/api/v1/snapshots", "/api/v1/ixps", "/api/v1/ixps/sp/potential", "/api/v1/asns/64500"):
        c.get(p, headers={"X-Real-IP": "203.0.113.9"})
    routes = {r["route"] for r in _lines(tmp_path)}
    assert {"/api/v1/snapshots", "/api/v1/ixps", "/api/v1/ixps/{code}/potential", "/api/v1/asns/{asn}"} <= routes
    assert not any(r.startswith(("/ixps", "/asns", "/snapshots")) for r in routes)


def test_route_template_sem_roteador_ativo(app_client):
    from api.usage_log import route_template

    _, app, _ = app_client
    assert route_template(app, "/api/v1/ixps/sp/potential") == "/api/v1/ixps/{code}/potential"
    assert route_template(app, "/api/v1/asns/64500") == "/api/v1/asns/{asn}"
    assert route_template(app, "/api/v1/map/asns") == "/api/v1/map/asns"
    assert route_template(app, "/rota/inexistente") is None
