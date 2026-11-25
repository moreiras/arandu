# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — PT-15: na collection `asns` do `query`, `ixps_direct` vinha do cadastro de participantes e não da sessão com o route server.

O nome certo do cadastro é `ixps_membro`; `ixps_sessao_rs` é a sessão (a regra de `ixps_direct_count` e do documento do ASN);
`ixps_direct` segue como alias de `ixps_membro`, com o mesmo valor e aviso de depreciação.
"""
from tests.products.api_contract import ALLOWED


def _linhas(api, corpo=None):
    r = api.post("/api/v1/query/asns", json={"limit": 1000, **(corpo or {})}, headers=ALLOWED)
    assert r.status_code == 200, r.text
    return r.json()


def test_asns_tem_membro_e_sessao_com_route_server_e_o_alias_vale_o_membro(api):
    j = _linhas(api)
    assert j["items"] and "aviso_obsoleta" not in j
    for a in j["items"]:
        assert a["ixps_direct"] == a["ixps_membro"]                       # alias do nome antigo: mesmo valor
        assert len(a["ixps_sessao_rs"]) == a["ixps_direct_count"]         # sessão com o route server é o que ixps_direct_count conta
    assert any(a["ixps_sessao_rs"] for a in j["items"])


def test_sessao_com_route_server_do_query_e_a_do_documento_do_as(api):
    com = [a for a in _linhas(api)["items"] if a["ixps_sessao_rs"]][:5]
    assert com
    for a in com:
        doc = api.get(f"/api/v1/asns/{a['asn']}", headers=ALLOWED).json()
        assert sorted(doc["ixps_direct"]) == a["ixps_sessao_rs"]          # no documento, `ixps_direct` sempre foi a sessão


def test_filtrar_pelo_nome_antigo_avisa_e_pelo_novo_nao(api):
    pelo_antigo = _linhas(api, {"filter": {"field": "ixps_direct", "op": "exists", "value": True}, "select": ["asn"]})
    assert "ixps_membro" in pelo_antigo["aviso_obsoleta"] and "ixps_sessao_rs" in pelo_antigo["aviso_obsoleta"]
    assert "ixps_direct" in pelo_antigo["aviso_obsoleta"] and "cadastro" in pelo_antigo["aviso_obsoleta"]
    for novo in ("ixps_membro", "ixps_sessao_rs"):
        assert "aviso_obsoleta" not in _linhas(api, {"filter": {"field": novo, "op": "exists", "value": True}, "select": ["asn"]})
    ordenado = _linhas(api, {"sort": [{"field": "ixps_direct", "dir": "asc"}], "select": ["asn"]})
    assert "aviso_obsoleta" in ordenado


def test_describe_schema_nomeia_os_campos_e_marca_o_antigo_como_obsoleto(api):
    campos = {c["name"]: c for c in api.get("/api/v1/schema", params={"collection": "asns"}, headers=ALLOWED).json()["fields"]}
    assert "cadastro de participantes" in campos["ixps_membro"]["description"]
    assert "sessão BGP com o route server" in campos["ixps_sessao_rs"]["description"]
    assert campos["ixps_direct"]["description"].startswith("[obsoleto, use `ixps_membro`]")
    assert "ixps_sessao_rs" in campos["ixps_direct_count"]["description"]
