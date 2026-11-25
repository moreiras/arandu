# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""MANRS agregado: sem supressão (D6), com n, peso do maior e avisos; comparação de prontidão."""
from products.manrs.build import MINIMO_ASNS, calcular


def _asns(n=12):
    return {str(i): {"usuarios": 100 * i, "uf": "SP" if i < 9 else "RJ", "faixa_porte": "ate_1000" if i < 7 else "de_1000_a_10000", "total": 40.0 + i, "classe": "atrasado", "pilares": {}} for i in range(1, n + 1)}


def test_totais_pct_e_organizacoes_so_com_asn_do_brasil():
    doc = {"participantes": [{"asns": [1, 2, 3, 4, 5, 6, 15169]}, {"asns": [9]}, {"asns": [3356]}]}          # a 3ª não tem ASN brasileiro: não conta
    r = calcular({"asns": _asns()}, doc)["brasil"]
    assert r["asns"] == 12 and r["asns_participantes"] == 7 and r["pct_asns"] == 58.3 and r["organizacoes_com_asn_br"] == 2
    assert r["usuarios_participantes"] == 100 * (1 + 2 + 3 + 4 + 5 + 6 + 9) and r["pct_usuarios"] == round(100 * 3000 / 7800, 1)


def test_nenhum_recorte_e_suprimido_e_o_pequeno_sai_com_aviso_e_numeros():
    """D6 (SEG-E11): o recorte com menos de 5 participantes aparece com os números e o aviso `poucos_casos`; nada de `suprimido`."""
    r = calcular({"asns": _asns()}, {"participantes": [{"asns": [1, 2, 3, 4, 5, 6, 9]}]})
    rj, sp = r["por_uf"]["RJ"], r["por_uf"]["SP"]
    assert rj["asns"] == 4 and rj["asns_participantes"] == 1 and rj["n_asns_com_dado"] == 1 and rj["pct_asns"] == 25.0
    assert "poucos_casos" in rj["avisos"] and "poucos_casos" not in sp["avisos"]            # SP tem 6 participantes
    assert not any(c.get("suprimido") for c in r["por_uf"].values()) and not r["brasil"].get("suprimido")
    assert all("comparacao_prontidao" not in c for c in r["por_uf"].values())                   # comparação nunca por UF
    assert set(r["por_uf"]) == {"SP", "RJ"} and set(r["por_faixa_porte"]) == {"ate_1000", "de_1000_a_10000"}


def test_peso_do_maior_participante_e_aviso_quando_chega_a_30_por_cento():
    asns = {str(i): {"usuarios": 1000 if i == 1 else 10, "uf": "SP", "faixa_porte": "ate_1000", "total": 50.0, "classe": "atrasado", "pilares": {}} for i in range(1, 8)}
    r = calcular({"asns": asns}, {"participantes": [{"asns": [1, 2, 3, 4, 5, 6]}]})["por_uf"]["SP"]
    assert r["n_asns_com_dado"] == 6 and r["peso_top1"] == round(1000 / 1050, 3)
    assert r["avisos"] == ["maior_integrante"]
    iguais = {str(i): {"usuarios": 100, "uf": "SP", "faixa_porte": "ate_1000", "total": 50.0, "classe": "atrasado", "pilares": {}} for i in range(1, 11)}
    assert calcular({"asns": iguais}, {"participantes": [{"asns": list(range(1, 11))}]})["por_uf"]["SP"]["avisos"] == []      # 10 de peso igual: 10% cada


def test_comparacao_de_prontidao_sai_com_n_e_aviso_mesmo_com_poucos_de_um_lado():
    r = calcular({"asns": _asns()}, {"participantes": [{"asns": [1, 2, 3, 4, 5, 6]}]})
    c = r["brasil"]["comparacao_prontidao"]
    assert c["participantes"]["asns_com_indice"] == 6 and c["nao_participantes"]["asns_com_indice"] == 6 and c["participantes"]["mediana"] == 43.5
    assert c["participantes"]["n_asns_com_dado"] == 6 and "avisos" in c["nao_participantes"]
    r2 = calcular({"asns": _asns()}, {"participantes": [{"asns": [1, 2, 3, 4]}]})
    assert r2["brasil"]["asns_participantes"] == 4 and "poucos_casos" in r2["brasil"]["avisos"] and not r2["brasil"].get("suprimido")
    assert "poucos_casos" in r2["brasil"]["comparacao_prontidao"]["participantes"]["avisos"]
    assert MINIMO_ASNS == 5
