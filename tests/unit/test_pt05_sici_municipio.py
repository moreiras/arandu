# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Indicadores do SICI por município: nome de quem não declarou e série sem zero falso (MUN-E1, MUN-E2)."""

from products.sici_indicadores.build import calcular_indicadores, serie_municipios

# ── MUN-E1 e MUN-E2 ──

def _mes(**ops):
    return {c: {"empresa": n, "acessos": a, "por_municipio": {ib: {"uf": "PA", "nome": "Pedro Régis", "acessos": a}}}
            for c, (n, a, ib) in ops.items()}


def test_ganho_e_perda_em_12_meses_tem_nome_de_quem_nao_declarou_no_mes():
    atual = _mes(a=("LIGGA TELECOM", 300, "1"))
    ano = {**_mes(b=("XZOON", 251, "1")), **_mes(a=("LIGGA TELECOM", 50, "1"))}
    ind = calcular_indicadores("2026-09", {"2026-09": atual, "2025-09": ano}, {}, {})
    m = ind["municipios"]["1"]
    assert m["perda_aa"] == {"cnpj": "b", "empresa": "XZOON", "acessos": -251}
    assert m["ganho_aa"]["empresa"] == "LIGGA TELECOM"
    # sem nome no mês de um ano antes: o do cadastro SCM
    ano2 = {"b": {"empresa": "", "acessos": 251, "por_municipio": {"1": {"uf": "PA", "nome": "P", "acessos": 251}}}}
    ind2 = calcular_indicadores("2026-09", {"2026-09": atual, "2025-09": ano2}, {}, {"b": "AFJ INFORMATICA LTDA"})
    assert ind2["municipios"]["1"]["perda_aa"]["empresa"] == "AFJ INFORMATICA LTDA"
    # CNPJ que some sem nome em fonte nenhuma: vazio (o front mostra o CNPJ)
    ind3 = calcular_indicadores("2026-09", {"2026-09": atual, "2025-09": ano2}, {}, {})
    assert ind3["municipios"]["1"]["perda_aa"]["empresa"] == ""


def test_serie_sem_ponto_no_mes_em_que_o_cnpj_nao_declarou():
    meses = ["2026-07", "2026-08", "2026-09"]
    cache = {
        "2026-07": {**_mes(x=("XZOON", 40, "1")), **_mes(a=("A", 60, "1"))},
        "2026-08": {**_mes(a=("A", 60, "1")), "c": {"empresa": "C", "acessos": 9, "por_municipio": {"2": {"uf": "PA", "nome": "Outro", "acessos": 9}}}},
        "2026-09": {**_mes(x=("XZOON", 50, "1")), **_mes(a=("A", 50, "1")), **_mes(c=("C", 0 + 10, "1"))},
    }
    out = serie_municipios("2026-09", meses, cache.get)
    share = {l["cnpj"]: l["share"] for l in out["1"]["lideres"]}
    assert share["x"] == [40.0, None, 45.45]       # não declarou em 2026-08: sem ponto, nunca zero (MUN-E2)
    assert share["c"] == [None, 0.0, 9.09]         # declarou em 2026-08 só em outro município: zero de verdade aqui
