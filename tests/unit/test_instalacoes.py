# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Instalações do PeeringDB: indicador de cadastro, vínculos, cobertura, portas por velocidade e os blocos da API, sem rede."""
from datetime import date

from api.services import instalacoes as svc
from products.instalacoes.build import (calcular_cobertura, calcular_instalacoes, calcular_portas, classe_cadastro, _ptts)

HOJE = date(2026, 11, 5)


def test_classe_cadastro_pelos_limiares_e_rotulada_como_inferida():
    r = classe_cadastro(["2026-11-01T00:00:00Z", "2020-01-01T00:00:00Z"], HOJE)
    assert r["classe"] == "recente" and r["dias"] == 4 and r["ultima_atualizacao"] == "2026-11-01" and r["inferido"] is True
    assert classe_cadastro(["2025-11-05T00:00:00Z"], HOJE)["classe"] == "recente"            # exatamente 365 dias
    assert classe_cadastro(["2025-11-04T00:00:00Z"], HOJE)["classe"] == "parado"
    assert classe_cadastro(["2023-11-06T00:00:00Z"], HOJE)["classe"] == "parado"             # 1095 dias
    assert classe_cadastro(["2023-11-05T00:00:00Z"], HOJE)["classe"] == "antigo"
    assert classe_cadastro([None, "", "lixo"], HOJE) is None                                  # sem data não há veredito
    assert classe_cadastro(["2026-12-01T00:00:00Z"], HOJE)["dias"] == 0                      # data de coleta posterior ao snapshot não dá dias negativos


DOC = {
    "facilities": {"1": {"id": 1, "nome": "A", "pais": "BR", "uf": "SP", "atualizado": "2026-10-01T00:00:00Z", "lat": -23.0, "lon": -46.0, "campus_id": 5},
                   "2": {"id": 2, "nome": "B", "pais": "BR", "uf": "RJ", "atualizado": "2019-01-01T00:00:00Z"},
                   "3": {"id": 3, "nome": "C", "pais": "UY", "atualizado": "2026-01-01T00:00:00Z"}},
    "netfac": [[1, 64496, "2020-01-01T00:00:00Z", "2020-01-02T00:00:00Z"], [1, 15169, "2021-01-01T00:00:00Z", "2021-01-02T00:00:00Z"], [2, 64496, "2018-01-01T00:00:00Z", "2019-01-01T00:00:00Z"]],
    "ixfac": [[1, 10], [1, 20], [3, 30], [2, 99]], "carriers": {"7": {"id": 7, "nome": "K"}}, "carrierfac": [[7, 1]], "campus": {"5": {"id": 5, "nome": "Campus"}},
    "redes": {"64496": {"escopo": "Regional"}}, "ixps": {"99": {"id": 99, "nome": "Outro PTT"}},
}
PTTS = {10: {"code": "sp", "nome": None, "tipo": "ixbr"}, 20: {"code": "ext", "nome": "Ext", "tipo": "externo"}, 30: {"code": "uy", "nome": "UY", "tipo": "externo"}, 99: {"code": None, "nome": "Outro PTT", "tipo": "outro"}}
NOMES = {"64496": {"nome": "Rede BR", "is_br": True}, "15169": {"nome": "Estrangeira", "is_br": False}}


def test_instalacoes_ligam_redes_ptts_carriers_e_so_o_brasil_conta_redes():
    inst, vinc = calcular_instalacoes(DOC, PTTS, HOJE, NOMES)
    assert inst["1"]["n_redes"] == 2 and inst["1"]["n_redes_br"] == 1 and inst["1"]["carriers"] == [7] and [x["code"] for x in inst["1"]["ixps"]] == ["ext", "sp"]
    assert inst["2"]["cadastro"]["classe"] == "antigo" and inst["1"]["cadastro"]["classe"] == "recente"
    assert inst["3"]["escopo"] == "ptt_externo" and "n_redes" not in inst["3"]                # fora do Brasil não tem vínculo de rede coletado
    assert inst["2"]["ixps"] == [{"ix_id": 99, "nome": "Outro PTT", "tipo": "outro"}]
    assert vinc["por_asn"]["64496"] == [[1, "2020-01-01T00:00:00Z", "2020-01-02T00:00:00Z"], [2, "2018-01-01T00:00:00Z", "2019-01-01T00:00:00Z"]]
    assert vinc["por_instalacao"]["1"][0][0] == 15169 and vinc["redes"]["15169"]["is_br"] is False
    cob = calcular_cobertura(inst, vinc, PTTS, DOC, 10, {64496, 64500})
    assert cob["instalacoes_br"] == 2 and cob["instalacoes_ptt_externo"] == 1 and cob["com_ptt"] == 2 and cob["com_carrier"] == 1 and cob["em_campus"] == 1 and cob["com_coordenadas"] == 1
    assert cob["ptts_ixbr"] == 1 and cob["ptts_ixbr_com_instalacao"] == 1 and cob["ptts_externos"] == 2 and cob["ptts_externos_com_instalacao"] == 2
    assert cob["ptts_ixbr_sem_instalacao"] == []
    sem = calcular_cobertura(inst, vinc, {**PTTS, 11: {"code": "ac", "nome": None, "tipo": "ixbr"}}, DOC, 10, set())
    assert (sem["ptts_ixbr"], sem["ptts_ixbr_com_instalacao"], sem["ptts_ixbr_sem_instalacao"]) == (2, 1, ["ac"])      # INST-E2: quem falta, pelo código
    assert cob["asns_br_no_peeringdb"] == 2 and cob["asns_br_com_instalacao"] == 1 and cob["cadastro_br"] == {"recente": 1, "antigo": 1}


def test_ptts_vem_do_proprio_snapshot_e_a_config_so_completa_o_nome():
    ixps = {"ixbr_ixps": {"sp": {"pdb_ix_id": 10}, "xx": {}}, "external_ixps": {"ext": {"pdb_ix_id": 20, "name": "Ext"}}}
    cfg = {"ixbr": [{"code": "sp", "name": "IX.br São Paulo"}], "external": []}
    p = _ptts(ixps, cfg, {"99": {"nome": "Outro"}, "20": {"nome": "ignorado"}})
    assert p[10] == {"code": "sp", "nome": "IX.br São Paulo", "tipo": "ixbr"} and p[20]["tipo"] == "externo" and p[99] == {"code": None, "nome": "Outro", "tipo": "outro"} and 0 not in p


def test_portas_por_velocidade_so_externos_e_asn_do_brasil():
    docs = {"external_ixps": {"ext": {"name": "Ext", "city": "X", "country": "UY", "pdb_ix_id": 20, "members": [
        {"asn": 64496, "speed": 10000}, {"asn": 64496, "speed": 100000}, {"asn": 15169, "speed": 10000}, {"asn": 64497, "speed": 0}]}}}
    r = calcular_portas(docs, {64496})
    x = r["ixps"]["ext"]
    assert x["portas"] == 4 and x["portas_com_velocidade"] == 3 and x["membros"] == 3 and x["capacidade_mbps"] == 120000 and x["mediana_mbps"] == 10000 and x["maior_mbps"] == 100000
    assert x["por_velocidade"] == {"10000": 2, "100000": 1}
    assert r["por_asn"] == {"64496": {"ext": [10000, 100000]}}


def test_blocos_da_api_cobrem_ausencia_e_nao_inventam():
    inst, vinc = calcular_instalacoes(DOC, PTTS, HOJE, NOMES)
    pub = {"snapshot_date": "2026-11-05", "coletado_em": "2026-11-06T00:00:00+00:00", "fonte": {"nome": "PeeringDB"}, "limites": "x", "cobertura": {}, "instalacoes": inst, "carriers": DOC["carriers"], "campus": DOC["campus"]}
    assert svc.bloco_ixp(pub, "sp")["total"] == 1 and svc.bloco_ixp(pub, "nao-existe") is None and svc.bloco_ixp(None, "sp") is None
    assert svc.bloco_asn(pub, vinc, 64496)["total"] == 2 and svc.bloco_asn(pub, vinc, 1) is None and svc.bloco_asn(pub, None, 64496) is None
    d = svc.detalhe(pub, vinc, 1)
    assert d["redes_total"] == 2 and d["campus"]["nome"] == "Campus" and d["carriers"] == [{"id": 7, "nome": "K"}] and svc.detalhe(pub, vinc, 123) is None
    assert "não foram coletados" in svc.detalhe(pub, vinc, 3)["redes_nota"]
    assert svc.lista(pub, None, None, None, None, None, False, False, "redes", 10, 0)["total"] == 2
    assert svc.lista(pub, "todos", None, None, None, None, False, False, "redes", 10, 0)["total"] == 3
    assert svc.lista(pub, None, None, "b", None, None, False, False, "nome", 10, 0)["items"][0]["id"] == 2
    assert svc.lista(pub, None, None, None, None, None, False, False, "redes", 1, 1)["items"][0]["id"] == 2                  # offset
    atrib = {"snapshot_date": "2026-11-05", "fonte": {}, "limites": "l", "asns": {"64496": {"escopo": "Regional", "looking_glass": "https://lg.example.org"}}}
    p = svc.bloco_peering(atrib, {"por_asn": {"64496": {"ext": [10000]}}, "fonte": {}, "limites": ""}, vinc, 64496)
    assert p["instalacoes_br_observadas"] == 2 and p["portas_externas"]["ptts"][0]["capacidade_mbps"] == 10000 and svc.bloco_peering(atrib, None, vinc, 1) is None
    linhas = svc.linhas_redes_peering(atrib, vinc, {"por_asn": {"64496": {"ext": [10000]}}})
    assert linhas[0]["tem_looking_glass"] is True and linhas[0]["capacidade_externa_mbps"] == 10000 and "looking_glass" not in linhas[0]
    assert svc.linhas_facilities(None) == [] and svc.linhas_facilidades_rede(None, None) == [] and svc.linhas_redes_peering(None, None, None) == []
