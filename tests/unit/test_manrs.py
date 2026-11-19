# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""MANRS agregado: supressão de recortes pequenos e comparação de prontidão."""
from products.manrs.build import MINIMO_ASNS, calcular


def _asns(n=12):
    return {str(i): {"usuarios": 100 * i, "uf": "SP" if i < 9 else "RJ", "faixa_porte": "ate_1000" if i < 7 else "de_1000_a_10000", "total": 40.0 + i, "classe": "atrasado", "pilares": {}} for i in range(1, n + 1)}


def test_totais_pct_e_organizacoes_so_com_asn_do_brasil():
    doc = {"participantes": [{"asns": [1, 2, 3, 4, 5, 6, 15169]}, {"asns": [9]}, {"asns": [3356]}]}          # a 3ª não tem ASN brasileiro: não conta
    r = calcular({"asns": _asns()}, doc)["brasil"]
    assert r["asns"] == 12 and r["asns_participantes"] == 7 and r["pct_asns"] == 58.3 and r["organizacoes_com_asn_br"] == 2
    assert r["usuarios_participantes"] == 100 * (1 + 2 + 3 + 4 + 5 + 6 + 9) and r["pct_usuarios"] == round(100 * 3000 / 7800, 1)


def test_recorte_com_poucos_participantes_e_suprimido_sem_revelar_a_contagem():
    r = calcular({"asns": _asns()}, {"participantes": [{"asns": [1, 2, 3, 4, 5, 6, 9]}]})
    assert r["por_uf"]["RJ"] == {"asns": 4, "usuarios": 900 + 1000 + 1100 + 1200, "suprimido": True, "motivo": f"menos de {MINIMO_ASNS} ASNs participantes"}      # só 1 participante em RJ
    assert r["por_uf"]["SP"].get("suprimido") is True                      # SP (6) também sai: com o total público, RJ sairia por diferença
    assert "asns_participantes" not in r["por_uf"]["RJ"] and "asns_participantes" not in r["por_uf"]["SP"]
    assert all("comparacao_prontidao" not in c for c in r["por_uf"].values())                   # comparação nunca por UF


def test_comparacao_de_prontidao_exige_cinco_com_indice_dos_dois_lados():
    r = calcular({"asns": _asns()}, {"participantes": [{"asns": [1, 2, 3, 4, 5, 6]}]})
    c = r["brasil"]["comparacao_prontidao"]
    assert c["participantes"]["asns_com_indice"] == 6 and c["nao_participantes"]["asns_com_indice"] == 6 and c["participantes"]["mediana"] == 43.5
    assert r["por_faixa_porte"]["de_1000_a_10000"]["suprimido"] and r["por_faixa_porte"]["ate_1000"]["suprimido"]      # nenhum participante num porte: ele e o outro porte saem (senão sairia por diferença)
    r2 = calcular({"asns": _asns()}, {"participantes": [{"asns": [1, 2, 3, 4]}]})
    assert r2["brasil"]["suprimido"] is True and "comparacao_prontidao" not in r2["brasil"]


def test_supressao_complementar_nao_deixa_o_recorte_pequeno_sair_por_diferenca():
    asns = {str(i): {"usuarios": 10, "uf": "SP" if i <= 20 else ("RJ" if i <= 30 else "MG"), "faixa_porte": "ate_1000", "total": 50.0, "classe": "atrasado", "pilares": {}} for i in range(1, 41)}
    doc = {"participantes": [{"asns": list(range(1, 11)) + list(range(21, 26)) + [31, 32]}]}       # SP 10, RJ 5, MG 2
    uf = calcular({"asns": asns}, doc)["por_uf"]
    assert uf["MG"]["suprimido"] and uf["RJ"].get("suprimido") and not uf["SP"].get("suprimido")  # MG (2) + o menor dos demais (RJ, 5): a soma 7 não revela MG
    ok = {g: c for g, c in uf.items() if not c.get("suprimido")}
    assert 17 - sum(c["asns_participantes"] for c in ok.values()) >= MINIMO_ASNS                  # o que se deduz do total é a soma dos ocultos
