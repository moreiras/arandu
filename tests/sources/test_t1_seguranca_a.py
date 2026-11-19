# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — AS Rank do CAIDA e bogons (IANA e Team Cymru): formato original → normalizado, sem rede."""
import json

import pytest
import respx

from core.common import read_json_gz
from sources.bogons import collect as bogons
from sources.caida_asrank import collect as asrank


def _j(fx, nome):
    return json.loads(fx("caida_asrank", nome).read_text(encoding="utf-8"))


def _t(fx, nome):
    return fx("bogons", nome).read_text(encoding="utf-8")


def test_extrai_so_os_asns_do_pais_com_rank_cone_e_grau(fx):
    br = asrank.extrair_br(_j(fx, "pagina1.json"))
    assert [a["asn"] for a in br] == [64497]
    assert br[0] == {"asn": 64497, "rank": 7887, "fonte_rir": "LACNIC", "clique": False, "org_id": "b7966dd5a6",
                     "cone": {"asns": 2, "prefixos": 8188, "enderecos": 10895360}, "grau": {"total": 31, "cliente": 1, "par": 29, "provedor": 1}}


@respx.mock
def test_run_pagina_ate_o_fim_e_grava_normalizado(base, log, fx, date_str, monkeypatch):
    monkeypatch.setattr(asrank, "MINIMO_GLOBAL", 5)
    monkeypatch.setattr(asrank, "MINIMO_BR", 2)
    monkeypatch.setattr(asrank, "ESPERA_S", 0)
    rota = respx.get(asrank.URL).mock(side_effect=[respx.MockResponse(200, json=_j(fx, "pagina1.json")), respx.MockResponse(200, json=_j(fx, "pagina2.json"))])
    r = asrank.run(date_str, base, log, espera_s=0)
    assert r == {"asns_br": 2, "total_global": 5} and rota.call_count == 2
    assert rota.calls[1].request.url.params["offset"] == "10000"
    n = read_json_gz(base / "normalized" / date_str / "summary" / "caida_asrank.json.gz")
    assert sorted(n["asns"]) == ["64497", "64499"] and n["asns"]["64499"]["grau"]["provedor"] == 1 and "CAIDA" in n["copyright"]


@respx.mock
def test_listagem_truncada_falha_alto_e_nao_grava(base, log, fx, date_str):
    respx.get(asrank.URL).respond(200, json=_j(fx, "pagina2.json"))             # 5 ASNs na base < 100.000
    with pytest.raises(RuntimeError, match="caida_asrank"):
        asrank.run(date_str, base, log, espera_s=0)
    assert not (base / "normalized" / date_str / "summary" / "caida_asrank.json.gz").exists()


def test_iana_fica_so_com_blocos_nao_alcancaveis_globalmente(fx):
    v4 = bogons.parse_iana_ip(_t(fx, "iana_v4.csv"))
    assert [b["bloco"] for b in v4] == ["0.0.0.0/8", "10.0.0.0/8", "192.0.0.0/24", "198.18.0.0/15"]      # 192.0.0.9/32 é alcançável; "[2]" sai do bloco
    assert v4[0]["nome"] == "This network"
    assert [b["bloco"] for b in bogons.parse_iana_ip(_t(fx, "iana_v6.csv"))] == ["::1/128", "2001:db8::/32", "fc00::/7"]


def test_iana_asns_reservados_com_faixas(fx):
    a = bogons.parse_iana_as(_t(fx, "iana_as.csv"))
    assert {"inicio": 64496, "fim": 64511, "motivo": "For documentation and sample code; reserved by [RFC 5398]"} in a
    assert {"inicio": 4294967295, "fim": 4294967295, "motivo": "Reserved by [RFC 7300]"} in a


def test_cymru_lista_cidrs_e_data_da_lista(fx):
    cidrs, quando = bogons.parse_cymru(_t(fx, "cymru_v4.txt"))
    assert cidrs == ["0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "198.18.0.0/15", "5.0.0.0/16"] and quando == 1793465701


@respx.mock
def test_run_bogons_grava_e_lista_pequena_falha_alto(base, log, fx, date_str, monkeypatch):
    for chave, arq in (("iana_v4", "iana_v4.csv"), ("iana_v6", "iana_v6.csv"), ("iana_as", "iana_as.csv"), ("cymru_v4", "cymru_v4.txt"), ("cymru_v6", "cymru_v6.txt")):
        respx.get(bogons.URLS[chave]).respond(200, text=_t(fx, arq))
    with pytest.raises(RuntimeError, match="truncada"):                            # listas de teste são menores que o mínimo real
        bogons.run(date_str, base, log)
    assert not (base / "normalized" / date_str / "summary" / "bogons.json.gz").exists()
    monkeypatch.setattr(bogons, "MINIMO", {k: 1 for k in bogons.MINIMO})
    r = bogons.run(date_str, base, log)
    assert r["iana_v4"] == 4 and r["cymru_v6"] == 3
    n = read_json_gz(base / "normalized" / date_str / "summary" / "bogons.json.gz")
    assert n["cymru"]["as_of"] == "2026-10-31" and n["iana"]["asns"][0]["inicio"] == 0
