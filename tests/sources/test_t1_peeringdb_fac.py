# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — PeeringDB: instalações, carriers, campus e redes: lista branca sem contatos, escopo Brasil, requisições em lote, sem rede."""
import json
import re

import httpx
import pytest
import respx

from core.common import read_json_gz, write_json_gz
from sources.peeringdb_fac import collect as fonte

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _resp(fx):
    return json.loads(fx("peeringdb_fac", "respostas.json").read_text(encoding="utf-8"))


def _preparar(base, date_str, asns):
    d = base / "normalized" / date_str / "summary"
    d.mkdir(parents=True, exist_ok=True)
    write_json_gz(d / "peeringdb_networks.json.gz", {"networks": {str(a): {} for a in asns}})


def _rotas(fx):
    r = _resp(fx)
    dados = {
        "fac": r["fac"], "net": r["net"],
        "ix": [{"id": 9000, "name": "PTT Fictício", "city": "Arandurápolis", "country": "BR", "tech_email": "tecnico-fake@example.org", "policy_phone": "+55 11 5555-0003"}],
        "ixfac": [{"fac_id": 9101, "ix_id": 9000}, {"fac_id": 9201, "ix_id": 99001}],
        "netfac": [{"fac_id": 9101, "local_asn": 64496, "created": "2020-01-01T00:00:00Z", "updated": "2026-06-01T00:00:00Z"},
                   {"fac_id": 9102, "local_asn": 64498, "created": "2018-01-01T00:00:00Z", "updated": "2019-03-10T00:00:00Z"}],
        "carrierfac": [{"carrier_id": 501, "fac_id": 9101}],
        "carrier": [{"id": 501, "name": "Carrier Exemplo", "org_name": "Carrier Fictícia S.A.", "website": "https://carrier.example.org", "notes": "noc-fake@example.org", "fac_count": 1,
                     "created": "2020-01-01T00:00:00Z", "updated": "2025-01-01T00:00:00Z"}],
        "campus": [{"id": 7, "name": "Campus Exemplo", "org_name": "Operadora Fictícia S.A.", "city": "Arandurápolis", "state": "SP", "country": "BR", "created": "2023-01-01T00:00:00Z",
                    "updated": "2025-06-01T00:00:00Z", "website": "https://campus.example.org"},
                   {"id": 8, "name": "Campus de outro país", "country": "IT"}],
    }
    chamadas = []

    def atender(request: httpx.Request):
        recurso = request.url.path.rsplit("/", 1)[-1]
        chamadas.append((recurso, dict(request.url.params)))
        linhas = dados[recurso]
        p = request.url.params
        if recurso == "fac" and "id__in" in p:                      # PTT externo: instalação fora do Brasil
            linhas = [{"id": 9201, "name": "Datacenter Fictício UY", "country": "UY", "city": "Cidade Exemplo", "updated": "2026-01-01T00:00:00Z", "tech_email": "x-fake@example.org"}]
        elif recurso == "fac":
            linhas = r["fac"]
        return httpx.Response(200, json={"data": linhas, "meta": {}})

    return atender, chamadas


@pytest.fixture()
def pronto(monkeypatch, base, log, fx, date_str):
    monkeypatch.setattr(fonte, "MINIMO_FAC_BR", 1)
    _preparar(base, date_str, [64496, 64498])
    atender, chamadas = _rotas(fx)
    return atender, chamadas


@respx.mock
def test_run_grava_normalizado_so_com_lista_branca_e_sem_contato(pronto, base, log, date_str):
    atender, chamadas = pronto
    respx.route(host="www.peeringdb.com").mock(side_effect=atender)
    r = fonte.run(date_str, base, log, espera_s=0, retry_s=0)
    norm = read_json_gz(base / "normalized" / date_str / "summary" / "peeringdb_fac.json.gz")
    assert r["facilities"] == 3 and set(norm["facilities"]) == {"9101", "9102", "9201"}            # as do Brasil e a do PTT externo
    f = norm["facilities"]["9101"]
    assert f["nome"] == "Datacenter Exemplo SP-1" and f["uf"] == "SP" and f["lat"] == -23.6 and f["campus_id"] == 7 and f["site"] == "https://dc1.example.org"
    assert not set(f) & {"tech_email", "sales_email", "tech_phone", "sales_phone", "notes", "social_media", "address1", "zipcode"}
    assert "site" not in norm["facilities"]["9102"] and "lat" not in norm["facilities"]["9102"]      # site que não é URL some; coordenada nula some
    assert norm["netfac"] == [[9101, 64496, "2020-01-01T00:00:00Z", "2026-06-01T00:00:00Z"], [9102, 64498, "2018-01-01T00:00:00Z", "2019-03-10T00:00:00Z"]]
    assert norm["ixfac"] == [[9101, 9000], [9201, 99001]] and norm["ixps"]["9000"] == {"id": 9000, "nome": "PTT Fictício", "cidade": "Arandurápolis", "pais": "BR"}
    assert norm["carriers"]["501"]["nome"] == "Carrier Exemplo" and "notes" not in norm["carriers"]["501"] and norm["carrierfac"] == [[501, 9101]]
    assert set(norm["campus"]) == {"7"}                                                              # campus de outro país fica de fora (o filtro country é ignorado pela API)
    assert norm["redes"]["64496"]["looking_glass"] == "https://lg.example.org/" and norm["redes"]["64496"]["route_server"] == "telnet://rs.example.org"
    assert "looking_glass" not in norm["redes"]["64498"] and "route_server" not in norm["redes"]["64498"]   # credencial embutida e e-mail não passam
    assert norm["redes"]["64496"]["ipv6"] is True and norm["redes"]["64498"]["ipv6"] is False         # False é informação, não ausência
    assert not EMAIL.search(json.dumps(norm, ensure_ascii=False)) and "+55" not in json.dumps(norm)
    # o /net pede só os campos da lista branca (sem notes nem contatos)
    net = next(p for rec, p in chamadas if rec == "net")
    assert "notes" not in net["fields"] and "asn__in" in net and net["depth"] == "0"


@respx.mock
def test_requisicoes_do_brasil_pausa_user_agent_e_sem_chave_no_manifesto(pronto, base, log, date_str, monkeypatch):
    atender, chamadas = pronto
    visto = []

    def espiar(request):
        visto.append(request.headers)
        return atender(request)

    respx.route(host="www.peeringdb.com").mock(side_effect=espiar)
    monkeypatch.setenv("PEERINGDB_API_KEY", "chave-de-teste-123")
    pausas = []
    monkeypatch.setattr(fonte.time, "sleep", lambda s: pausas.append(s))
    fonte.run(date_str, base, log, espera_s=1.5, retry_s=0)
    assert all(h["user-agent"].startswith("arandurape/") and h["authorization"] == "Api-Key chave-de-teste-123" for h in visto)
    assert all(p.get("country", "BR") == "BR" for rec, p in chamadas if rec in ("fac", "ixfac", "netfac", "ix") and "id__in" not in p and "ix_id__in" not in p)
    assert pausas and all(p == 1.5 for p in pausas)                                                  # uma requisição por vez, pausa entre elas
    manifesto = (base / "raw" / date_str / "summary" / f"peeringdb-fac-requisicoes-{date_str}.json").read_text(encoding="utf-8")
    assert "chave-de-teste-123" not in manifesto and "Api-Key" not in manifesto and json.loads(manifesto)
    assert not list((base / "raw" / date_str / "summary").glob("peeringdb-fac-[!r]*"))               # o bruto (com contatos) não é gravado


@respx.mock
def test_poucas_instalacoes_falham_alto(base, log, fx, date_str):
    _preparar(base, date_str, [64496])
    atender, _ = _rotas(fx)
    respx.route(host="www.peeringdb.com").mock(side_effect=atender)
    with pytest.raises(RuntimeError, match="instalações no Brasil"):
        fonte.run(date_str, base, log, espera_s=0, retry_s=0)                                         # 2 < MINIMO_FAC_BR (100)
    assert not (base / "normalized" / date_str / "summary" / "peeringdb_fac.json.gz").exists()


@respx.mock
def test_429_repete_e_esgotado_falha(pronto, base, log, date_str, monkeypatch):
    atender, _ = pronto
    monkeypatch.setattr(fonte.time, "sleep", lambda s: None)
    rota = respx.route(host="www.peeringdb.com").mock(return_value=httpx.Response(429, headers={"Retry-After": "1"}))
    with pytest.raises(fonte.LimiteError):
        fonte.run(date_str, base, log, espera_s=0, retry_s=0)
    assert rota.call_count == fonte.MAX_TENTATIVAS


def test_sem_peeringdb_networks_falha_alto(base, log, date_str):
    with pytest.raises(RuntimeError, match="peeringdb_networks"):
        fonte.run(date_str, base, log, espera_s=0, retry_s=0)


def test_url_publica():
    assert fonte.url_publica("https://lg.exemplo.org/x") and fonte.url_publica("telnet://rs.exemplo.org")
    for ruim in ("https://u:p@lg.exemplo.org", "noc@exemplo.org", "n/a", "", None, "https://a.org/ com espaço", "ftp://x.org", 5):
        assert fonte.url_publica(ruim) is None
