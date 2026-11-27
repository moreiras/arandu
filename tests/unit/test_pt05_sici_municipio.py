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


# ── PT-26 / MUN 5.1 (c, d) ──

def test_mudanca_de_cnpj_provavel_soma_a_marca_no_ganho_e_na_perda():
    # a e b têm o mesmo nome fantasia: b perde 120 e a ganha 125; c ganha 10 por conta própria
    atual = _mes(a=("LIGGA TELECOMUNICACOES S.A.", 130, "1"), c=("OUTRA", 20, "1"))
    ano = _mes(b=("LIGGA TELECOM", 120, "1"), a=("LIGGA TELECOMUNICACOES S.A.", 5, "1"), c=("OUTRA", 10, "1"))
    fant = {"a": "Ligga", "b": "LIGGA ", "c": "Outra"}
    m = calcular_indicadores("2026-09", {"2026-09": atual, "2025-09": ano}, {}, {}, None, fant)["municipios"]["1"]
    assert m["mudancas_cnpj"] == [{"marca": "Ligga", "de_cnpj": "b", "para_cnpj": "a", "acessos_de": -120, "acessos_para": 125}]
    assert m["ganho_aa"] == {"cnpj": "c", "empresa": "OUTRA", "acessos": 10}      # a marca somada (+5) não é mais o maior ganho
    assert "perda_aa" not in m
    # sem nome fantasia nada é somado: o comportamento anterior
    m2 = calcular_indicadores("2026-09", {"2026-09": atual, "2025-09": ano}, {}, {})["municipios"]["1"]
    assert "mudancas_cnpj" not in m2 and m2["perda_aa"]["cnpj"] == "b" and m2["ganho_aa"]["cnpj"] == "a"


def test_mesmo_nome_fantasia_sem_compensacao_nao_junta():
    atual = _mes(a=("A", 300, "1"))
    ano = _mes(b=("B", 100, "1"), a=("A", 5, "1"))
    m = calcular_indicadores("2026-09", {"2026-09": atual, "2025-09": ano}, {}, {}, None, {"a": "Marca", "b": "Marca"})["municipios"]["1"]
    assert "mudancas_cnpj" not in m and m["ganho_aa"]["acessos"] == 295 and m["perda_aa"]["acessos"] == -100


def test_serie_inclui_quem_foi_lider_em_algum_mes_da_janela():
    meses = ["2026-07", "2026-08", "2026-09"]
    cache = {"2026-07": _mes(x=("XZOON", 970, "1"), a=("A", 10, "1")),
             "2026-08": _mes(a=("A", 12, "1")),
             "2026-09": _mes(a=("A", 13, "1"))}
    out = serie_municipios("2026-09", meses, cache.get)
    assert [l["cnpj"] for l in out["1"]["lideres"]] == ["x", "a"]          # a XZOON só liderava antes do mês de referência
    assert next(l for l in out["1"]["lideres"] if l["cnpj"] == "x")["share"][1:] == [None, None]
    cache2 = {"2026-09": _mes(**{f"c{i}": (f"E{i}", 100 - i, "1") for i in range(9)})}
    assert len(serie_municipios("2026-09", ["2026-09"], cache2.get)["1"]["lideres"]) == 4
    cache3 = {m: _mes(**{f"{m[-1]}{i}": (f"E{i}", 100 - i, "1") for i in range(4)}) for m in meses}
    assert len(serie_municipios("2026-09", meses, cache3.get)["1"]["lideres"]) == 6   # união de 12, limitada a 6
