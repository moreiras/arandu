# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Organização por ASN e abuso agregado: cálculo dos irmãos, cobertura, abuso só do Brasil e blocos da API."""
from api.services import as2org as svc
from products.as2org.build import calcular_abuso, calcular_as2org

ORGS = {"64497": {"org_id": "a", "org_nome": "Exemplo", "org_pais": "BR", "membros_total": 3},
        "64499": {"org_id": "a", "org_nome": "Exemplo", "org_pais": "BR", "membros_total": 3},
        "64500": {"org_id": "b", "org_nome": "Outra", "org_pais": "BR", "membros_total": 1}}


def test_irmaos_sao_os_outros_asns_do_brasil_da_mesma_organizacao_e_cobertura_conta_o_snapshot():
    asns, cob = calcular_as2org(ORGS, {64497, 64499, 64500, 64502})
    assert asns["64497"]["irmaos_br"] == [64499] and asns["64499"]["irmaos_br"] == [64497] and "irmaos_br" not in asns["64500"]
    assert cob["asns_br"] == 4 and cob["com_organizacao"] == 3 and cob["sem_organizacao"] == 1 and cob["pct"] == 75.0
    assert cob["organizacoes"] == 2 and cob["organizacoes_com_irmaos"] == 1


def test_cobertura_sem_asn_do_brasil_nao_divide_por_zero():
    _, cob = calcular_as2org(ORGS, set())
    assert cob["pct"] is None and cob["asns_no_caida_fora_do_snapshot"] == 3


def test_abuso_so_conta_asn_do_brasil_e_ausencia_nao_vira_limpo():
    doc = {"feodo": {"total": 2, "online": 1, "asns": {"64497": {"c2_total": 2, "c2_online": 1, "malware": {"Emotet": 2}}, "64510": {"c2_total": 1, "c2_online": 0, "malware": {}}}}}
    r = calcular_abuso(doc, {64497, 64500})
    assert set(r["asns"]) == {"64497"} and r["feodo_c2_br"] == 2 and r["feodo_total_mundo"] == 2
    pub = {"snapshot_date": "2026-11-05", "fonte": {}, "limites": "x", **r}
    assert svc.bloco_abuso(pub, 64500)["registrado"] is False and svc.bloco_abuso(pub, 64500)["feodo_c2"] == 0
    assert svc.bloco_abuso(pub, 64497)["feodo_c2"] == 2 and svc.bloco_abuso(None, 64497) is None
    assert calcular_abuso(None, {64497})["asns"] == {}


def test_blocos_e_linhas_da_api():
    asns, cob = calcular_as2org(ORGS, {64497, 64499, 64500})
    org = {"snapshot_date": "2026-11-05", "fonte": {"nome": "x"}, "limites": "y", "cobertura": cob, "asns": asns}
    assert svc.bloco_organizacao(org, 64497)["irmaos_br"] == [64499] and svc.bloco_organizacao(org, 1) is None and svc.bloco_organizacao(None, 64497) is None
    ab = {"asns": {"64497": {"feodo_c2": 1}}}
    linhas = svc.linhas(org, ab)
    assert [x["asn"] for x in linhas] == [64497, 64499, 64500] and linhas[0]["feodo_c2"] == 1 and linhas[1]["feodo_c2"] == 0 and linhas[0]["n_irmaos_br"] == 1
    assert "feodo_c2" not in svc.linhas(org, None)[0] and svc.linhas(None, None) == []
