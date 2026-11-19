# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Qualidade e reclamações da Anatel: ligação marca → CNPJ, taxa por mil acessos e a tabela curada real."""
import pytest

from core import marcas as m
from products.qualidade.build import MAX_POR_MIL, calcular_reclamacoes


def test_normalizar_ignora_acento_caixa_e_pontuacao_mas_guarda_o_mais():
    assert m.normalizar("Giga+ Fibra") == "GIGA+FIBRA" and m.normalizar("Não localizei!") == "NAOLOCALIZEI" and m.normalizar(None) == ""


def test_tabela_curada_real_tem_raizes_validas_e_marcas_sem_duplicata():
    c = m.carregar_curada()
    assert c["versao"] >= 1 and len(c["marcas"]) >= 25
    assert all(len(r) == 8 and r.isdigit() for e in c["marcas"].values() for r in e["raizes"])
    assert c["marcas"]["VIVO"]["raizes"] == ["02558157"] and set(c["marcas"]["CLARO"]["raizes"]) == {"40432544", "66970229"}
    assert all(e["base"] for e in c["marcas"].values())              # todo vínculo diz o que o sustenta


def test_tabela_curada_rejeita_raiz_mal_formada(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text('versao: 1\ncurada_em: 2026-11-06\nfonte_da_curadoria: x\nmarcas:\n  - {marca: X, raizes: ["123"], base: b}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="raiz inválida"):
        m.carregar_curada(p)


def test_casar_curada_automatica_ambigua_e_generica():
    curada = {"marcas": {"VIVO": {"marca": "VIVO", "raizes": ["02558157"], "base": "x"}}}
    fantasia = m.indice_fantasia([{"cnpj": "11111111000111", "nome_fantasia": "Alfa Net"}, {"cnpj": "11111111000292", "nome_fantasia": "ALFA NET"},
                                  {"cnpj": "22222222000122", "nome_fantasia": "Xyz"}, {"cnpj": "33333333000133", "nome_fantasia": "Gama Fibra"}, {"cnpj": "44444444000144", "nome_fantasia": "Gama Fibra"},
                                  {"cnpj": "55555555000155", "nome_fantasia": "OI"}])
    assert m.casar("vivo", curada, fantasia)["metodo"] == "curada"
    assert m.casar("ALFA NET", curada, fantasia) == {"raizes": ["11111111"], "metodo": "automatico", "base": m.casar("ALFA NET", curada, fantasia)["base"]}      # matriz e filial: uma raiz só
    assert m.casar("Gama Fibra", curada, fantasia) is None                   # duas raízes com o mesmo nome fantasia: não casa
    assert m.casar("XYZ", curada, fantasia) is None                         # menos de 4 caracteres normalizados
    assert m.casar("OI", curada, fantasia) is None and m.casar("Outros", curada, fantasia) is None and m.casar("NÃO LOCALIZEI A MINHA EMPRESA", curada, fantasia) is None
    assert m.casar("ALFA NET", curada, fantasia, automatico=False) is None


def _rec(marcas_, marca_mensal, marca_uf, municipios=None):
    return {"resumo": {"arquivos": {"reclamacoes_contexto.csv": {"mes_final": "2026-09", "data_extracao": "2026-10-12"}}, "anos": [2025, 2026], "anos_municipio": 3}, "por_mes": [], "marcas": marcas_,
            "marca_mensal": marca_mensal, "marca_uf": marca_uf, "uf": [], "assuntos": [], "marca_assuntos": [], "municipios": municipios or {}}


def test_automatica_so_vale_se_as_reclamacoes_se_concentram_nas_ufs_da_outorga():
    curada = {"versao": 1, "curada_em": "x", "fonte_da_curadoria": "x", "marcas": {}}
    fantasia = {"STARLINK": {"25328677"}, "TELYNET": {"06346446"}}
    marcas_ = [{"marca": "STARLINK", "servico": "SCM", "ano": 2026, "reclamacoes": 100, "municipios": 50}, {"marca": "TELYNET", "servico": "SCM", "ano": 2026, "reclamacoes": 100, "municipios": 5}]
    mensal = [{"marca": "STARLINK", "servico": "SCM", "mes": "2026-01", "reclamacoes": 100}, {"marca": "TELYNET", "servico": "SCM", "mes": "2026-01", "reclamacoes": 100}]
    uf = [{"marca": "STARLINK", "uf": "SP", "ano": 2026, "reclamacoes": 15}, {"marca": "STARLINK", "uf": "RJ", "ano": 2026, "reclamacoes": 85},
          {"marca": "TELYNET", "uf": "MG", "ano": 2026, "reclamacoes": 90}, {"marca": "TELYNET", "uf": "SP", "ano": 2026, "reclamacoes": 10}]
    doc, _ = calcular_reclamacoes(_rec(marcas_, mensal, uf), curada, fantasia, {}, {}, None, ufs_raiz={"25328677": {"SP"}, "06346446": {"MG", "SP"}})
    por = {x["marca"]: x for x in doc["marcas"]}
    assert por["STARLINK"]["raizes"] == [] and por["STARLINK"]["casamento"] is None                  # só 15% em SP: é outra empresa de mesmo nome
    assert por["TELYNET"]["raizes"] == ["06346446"] and por["TELYNET"]["casamento"] == "automatico"
    assert doc["casamento"]["automaticas_descartadas_por_uf"] == ["STARLINK"]


def test_taxa_por_mil_so_curada_com_volume_e_razao_plausivel():
    curada = {"versao": 1, "curada_em": "x", "fonte_da_curadoria": "x", "marcas": {m.normalizar(n): {"marca": n, "raizes": [r], "base": "b"} for n, r in (("GRANDE", "10000000"), ("POUCA", "20000000"), ("PEQUENA", "30000000"), ("ESTRANHA", "40000000"))}}
    marcas_ = [{"marca": n, "servico": "SCM", "ano": 2026, "reclamacoes": 1, "municipios": 1} for n in ("GRANDE", "POUCA", "PEQUENA", "ESTRANHA")]
    mensal = [{"marca": "GRANDE", "servico": "SCM", "mes": "2026-01", "reclamacoes": 500}, {"marca": "POUCA", "servico": "SCM", "mes": "2026-01", "reclamacoes": 10},
              {"marca": "PEQUENA", "servico": "SCM", "mes": "2026-01", "reclamacoes": 50}, {"marca": "ESTRANHA", "servico": "SCM", "mes": "2026-01", "reclamacoes": 5000},
              {"marca": "GRANDE", "servico": "SCM", "mes": "2024-01", "reclamacoes": 999}]      # fora da janela de 12 meses
    acessos = {"SCM": {"10000000": 100_000, "20000000": 100_000, "30000000": 300, "40000000": 10_000}, "SMP": {}}
    doc, _ = calcular_reclamacoes(_rec(marcas_, mensal, []), curada, {}, acessos, {"SCM": "2026-08", "SMP": "2026-08"}, None)
    t = {x["marca"]: x for x in doc["taxas"]["itens"]}
    assert doc["taxas"]["janela"] == {"de": "2025-10", "ate": "2026-09"} and doc["taxas"]["sici_mes_referencia"]["SCM"] == "2026-08"
    assert t["GRANDE"]["reclamacoes"] == 500 and t["GRANDE"]["por_mil_acessos"] == 5.0
    assert t["POUCA"]["por_mil_acessos"] is None and "menos de 30" in t["POUCA"]["motivo_sem_taxa"]
    assert t["PEQUENA"]["por_mil_acessos"] is None and "sem acessos" in t["PEQUENA"]["motivo_sem_taxa"]
    assert t["ESTRANHA"]["por_mil_acessos"] is None and f"acima de {MAX_POR_MIL}" in t["ESTRANHA"]["motivo_sem_taxa"]
