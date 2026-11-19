# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — o bloco `route_server` do DE-CIX estende `GET /external-ixps/{code}`, a lista e o `/query`, sem alterar o que já existia.

O dataset sintético não tem DE-CIX; o teste grava um `decix_rs/ixps.json.gz` sintético sob o código do IXP externo fictício (`zx`) no snapshot T1, confere as respostas e
remove o arquivo no fim (o `pipeline` é da sessão inteira). Os testes com coleta usam parâmetros diferentes dos do teste sem coleta para não cair no cache de resposta (GET) nem no de `/query`."""
import pytest

from core.common import write_json_gz
from tests.products.api_contract import ALLOWED
from tests.synth.world import T1

BLOCO = {"nome": "IX Externo Fictício", "cidade": "Cidade Exemplo", "criterio": {"asn_direct": "sessão up"}, "rs": [],
         "resumo": {"rs": 2, "sessoes": 5, "sessoes_up": 4, "sessoes_down": 1, "membros": 4, "membros_up": 3, "asn_direct_count": 3, "br_asn_direct_count": 2, "asn_origin_count": 7, "br_asn_origin_count": 5},
         "asn_direct": [64496, 64497, 64499], "asn_origin": [64496], "rotas": {"parcial": True, "vizinhos_lidos": 2}, "membros": [], "peeringdb": None, "comparacao_cidade": {"cidade": "Cidade Exemplo"}}


@pytest.fixture()
def com_decix(pipeline, api):
    base, _ = pipeline
    destino = base / "published" / T1 / "decix_rs"
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "ixps.json.gz", {"snapshot_date": T1, "coletado_em": "2026-11-10T12:00:00Z", "fonte": "https://lg.de-cix.net (Alice-LG)", "versao_alice": "6.2.0",
                                              "aviso": "origem é piso", "ixps": {"zx": BLOCO}})
    store = api.app.state.store

    def esquecer():                                       # o repositório, a tabela do /query e os resultados guardados são por data e valem a vida do processo
        store._decix_rs.invalidar(T1)
        store._query_tables.pop(f"{T1}/external_ixps", None)
        store._consultas._resultados.clear()
    esquecer()
    yield
    (destino / "ixps.json.gz").unlink()
    destino.rmdir()
    esquecer()


def test_sem_coleta_o_documento_do_ixp_externo_sai_como_antes(api):
    doc = api.get("/api/v1/external-ixps/zx", params={"date": T1}, headers=ALLOWED).json()
    assert "route_server" not in doc
    assert all("route_server" not in e for e in api.get("/api/v1/external-ixps", params={"date": T1}, headers=ALLOWED).json()["ixps"])
    linhas = api.post("/api/v1/query/external_ixps", params={"date": T1}, json={"limit": 10}, headers=ALLOWED).json()["items"]
    assert linhas and all(x["rs_asn_direct_count"] is None and x["rs_sessoes_up"] is None for x in linhas)


def test_com_coleta_o_bloco_route_server_vem_no_documento_na_lista_e_no_query(api, com_decix):
    doc = api.get("/api/v1/external-ixps/zx", params={"date": T1, "br_only": "false"}, headers=ALLOWED).json()
    assert doc["code"] == "zx" and doc["members"]                                           # o que já havia continua
    rs = doc["route_server"]
    assert rs["asn_direct"] == [64496, 64497, 64499] and rs["rotas"]["parcial"] is True and rs["aviso"] == "origem é piso" and rs["versao_alice"] == "6.2.0"
    br = api.get("/api/v1/external-ixps/zx", params={"date": T1, "br_only": "true"}, headers=ALLOWED).json()
    assert all(m["is_br"] for m in br["members"]) and br["route_server"]["asn_direct"] == rs["asn_direct"]
    lista = api.get("/api/v1/external-ixps", params={"date": T1, "country": "UY"}, headers=ALLOWED).json()["ixps"]
    assert next(e for e in lista if e["code"] == "zx")["route_server"] == {"sessoes_up": 4, "asn_direct_count": 3, "asn_origin_count": 7, "origem_parcial": True}
    linhas = api.post("/api/v1/query/external_ixps", params={"date": T1}, json={"limit": 11}, headers=ALLOWED).json()["items"]
    zx = next(x for x in linhas if x["code"] == "zx")
    assert (zx["rs_sessoes_up"], zx["rs_asn_direct_count"], zx["rs_asn_origin_count"]) == (4, 3, 7)
    filtradas = api.post("/api/v1/query/external_ixps", params={"date": T1}, json={"limit": 12, "filter": {"field": "rs_asn_direct_count", "op": "gte", "value": 3}}, headers=ALLOWED).json()["items"]
    assert [x["code"] for x in filtradas] == ["zx"]
