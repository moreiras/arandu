# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — Alice-LG do IX.br (sessões dos route servers, níveis 0 e 1): API → normalizado, sem rede."""
import json

import httpx
import pytest
import respx

from core.common import read_json_gz
from sources.ixbr_alice import collect as alice


def _j(fx, nome):
    return json.loads(fx("ixbr_alice", nome).read_text(encoding="utf-8"))


@pytest.fixture()
def api(fx, monkeypatch):
    monkeypatch.setattr(alice, "MINIMO_RS", 3)
    monkeypatch.setattr(alice, "PAUSA_S", 0)
    monkeypatch.setattr(alice, "MAX_FALHA", 0.5)               # 1 de 3 tolerado no recorte pequeno; 2 de 3 falha
    r = respx.mock(assert_all_called=False)
    r.get(f"{alice.BASE}/config").respond(200, json=_j(fx, "config.json"))
    r.get(f"{alice.BASE}/status").respond(200, json=_j(fx, "status.json"))
    r.get(f"{alice.BASE}/routeservers").respond(200, json=_j(fx, "routeservers.json"))
    r.get(f"{alice.BASE}/routeservers/SP-rs1-v4/neighbors").respond(200, json=_j(fx, "neighbors_SP-rs1-v4.json"))
    r.get(f"{alice.BASE}/routeservers/SP-rs2-v4/neighbors").respond(200, json=_j(fx, "neighbors_SP-rs2-v4.json"))
    r.get(f"{alice.BASE}/routeservers/RR-rs1-v6/neighbors").respond(500)
    return r


def test_run_normaliza_rs_sessoes_e_comunidades(api, base, log, date_str):
    with api:
        res = alice.run(date_str, base, log, dormir=lambda s: None)
    assert res == {"rs": 3, "sessoes": 4, "rs_com_erro": 1}
    n = read_json_gz(base / "normalized" / date_str / "summary" / "rs_sessions.json.gz")
    rs = {r["rs"]: r for r in n["rs"]}
    assert rs["SP-rs1-v4"]["ixp"] == "sp" and rs["SP-rs1-v4"]["afi"] == "v4" and rs["SP-rs1-v4"]["numero"] == "rs1"
    assert (rs["SP-rs1-v4"]["sessoes"], rs["SP-rs1-v4"]["sessoes_up"], rs["SP-rs1-v4"]["rotas_importadas"]) == (3, 2, 800)
    # `estado_rotas` é o do cache de ROTAS do Alice; o frescor das sessões é o cached_at do neighbors
    assert rs["SP-rs2-v4"]["estado_rotas"] == "BUSY" and rs["RR-rs1-v6"]["estado_rotas"] == "ERROR" and "estado" not in rs["SP-rs2-v4"]
    assert rs["SP-rs1-v4"]["vizinhos_em"] == "2026-10-30T05:40:00.123456789Z" and rs["SP-rs2-v4"]["vizinhos_em"] == "2026-10-30T05:41:00Z" and rs["RR-rs1-v6"]["vizinhos_em"] is None
    assert rs["SP-rs1-v4"]["rotas_atualizadas_em"] == "2026-10-30T04:00:00Z"
    # consulta que falhou: sem sessões e dito, nunca zero inventado
    assert rs["RR-rs1-v6"]["consultado"] is False and rs["RR-rs1-v6"]["erro"] and rs["RR-rs1-v6"]["sessoes"] == 0
    assert n["versao_alice"] == "6.1.0"
    # ordenadas por ASN e IP; campos derivados
    assert [(s["asn"], s["neighbor_ip"]) for s in n["sessoes"] if s["rs"] == "SP-rs1-v4"] == [(64496, "203.0.113.10"), (64496, "203.0.113.11"), (64497, "203.0.113.20")]
    caida = n["sessoes"][0]
    assert caida["estado"] == "down" and caida["bgp_state"] == "Passive" and caida["last_error"] == "BGP Error: Hold timer expired"
    assert caida["state_changed"] == "2026-10-23 07:34:44" and caida["import_limit"] == 100
    ativa = [s for s in n["sessoes"] if s["neighbor_ip"] == "203.0.113.20" and s["rs"] == "SP-rs1-v4"][0]
    assert ativa["rotas"] == {"recebidas": 90, "aceitas": 90, "filtradas": 0, "exportadas": 500}
    assert ativa["route_changes_import"]["received"] == 93
    c = read_json_gz(base / "normalized" / date_str / "summary" / "ixbr_communities.json.gz")
    assert c["reject_reasons"]["26162"]["300"]["0"] == "Invalid on RPKI" and c["rpki"]["enabled"] is True


def test_nao_guarda_bruto(api, base, log, date_str):
    with api:
        alice.run(date_str, base, log, dormir=lambda s: None)
    assert not (base / "raw").exists()


def test_respeita_a_pausa_entre_requisicoes(api, base, log, date_str, monkeypatch):
    monkeypatch.setattr(alice, "PAUSA_S", 1.0)
    pausas = []
    with api:
        alice.run(date_str, base, log, dormir=pausas.append)
    assert sum(1 for p in pausas if p == 1.0) >= 5            # config→status→routeservers→3 neighbors


def test_repete_com_recuo_e_aceita(api, base, log, date_str, fx, monkeypatch):
    chamadas = {"n": 0}

    def flaky(request):
        chamadas["n"] += 1
        return httpx.Response(503) if chamadas["n"] == 1 else httpx.Response(200, json=_j(fx, "neighbors_SP-rs2-v4.json"))
    with api:
        api.get(f"{alice.BASE}/routeservers/SP-rs2-v4/neighbors").mock(side_effect=flaky)
        res = alice.run(date_str, base, log, dormir=lambda s: None)
    assert chamadas["n"] == 2 and res["rs_com_erro"] == 1       # o RR continua falhando; o SP rs2 recuperou


def test_falha_alto_quando_muitos_rs_nao_respondem(api, base, log, date_str):
    with api:
        api.get(f"{alice.BASE}/routeservers/SP-rs1-v4/neighbors").respond(500)
        with pytest.raises(RuntimeError, match="neighbors falhou em 2 de 3"):
            alice.run(date_str, base, log, dormir=lambda s: None)
    assert not (base / "normalized").exists()


def test_lista_truncada_de_route_servers_falha_alto(api, base, log, date_str, monkeypatch):
    monkeypatch.setattr(alice, "MINIMO_RS", 100)
    with api, pytest.raises(RuntimeError, match="route servers"):
        alice.run(date_str, base, log, dormir=lambda s: None)
