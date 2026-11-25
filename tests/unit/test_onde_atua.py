# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PT-23 (D6, D11): funções puras de "Onde atua": parcela local, declarantes, HHI local, filtro, ordem estável e resumo, com casos de borda."""
import pytest

from api.services import onde_atua as oa
from api.services.sici_indicadores import resumo_mercado_grupos

CAD = {
    "A": {"por_municipio": {"1": {"nome": "Alfa", "uf": "SP", "acessos": 600}, "2": {"nome": "Beta", "uf": "MG", "acessos": 10}}},
    "B": {"por_municipio": {"1": {"nome": "Alfa", "uf": "SP", "acessos": 100}}},
    "Z": {"por_municipio": {}},
}
MUNS = {"1": {"acessos": 1000, "operadores_count": 3, "hhi": 4600}, "2": {"acessos": 10, "operadores_count": 1, "hhi": 10000}}
MG = {"municipios": {"1": {"hhi_grupo": 5000, "faixa_grupo": "concentrado", "hhi_cnpj": 4600, "faixa_cnpj": "concentrado", "avisos_grupo": []},
                     "2": {"hhi_grupo": 10000, "faixa_grupo": "concentrado", "hhi_cnpj": 10000, "faixa_cnpj": "concentrado", "avisos_grupo": ["poucos_casos"]}}}


def test_operadora_ganha_parcela_declarantes_e_hhi_sem_alterar_o_original():
    base = [{"ibge": "1", "acessos": 250, "nome": "Alfa"}, {"ibge": "9", "acessos": 5, "nome": "Sem índice"}]
    out = oa.enriquecer_municipios_operadora(base, MUNS)
    assert out[0]["share"] == 25.0 and out[0]["municipio_acessos"] == 1000 and out[0]["municipio_operadores"] == 3 and out[0]["municipio_hhi"] == 4600
    assert out[0]["avisos_hhi"] == ["poucos_casos"]                              # 3 declarantes: menos de 5 casos, aviso só de rótulo
    assert out[1]["share"] is None and out[1]["municipio_hhi"] is None and out[1]["avisos_hhi"] is None          # sem índice: nulo, nunca zero
    assert "share" not in base[0]
    assert oa.enriquecer_municipios_operadora(base, None)[0]["share"] is None


def test_grupo_soma_os_cnpjs_e_calcula_parcela_do_conjunto():
    linhas = {l["ibge"]: l for l in oa.linhas_do_grupo(["A", "B", "Z", "X"], CAD, MUNS, MG)}
    assert set(linhas) == {"1", "2"}
    assert linhas["1"]["acessos"] == 700 and linhas["1"]["parcela"] == 70.0 and linhas["1"]["cnpjs_do_conjunto"] == 2
    assert linhas["1"]["declarantes"] == 3 and linhas["1"]["hhi_grupo"] == 5000 and linhas["1"]["hhi_cnpj"] == 4600
    assert linhas["2"]["parcela"] == 100.0 and linhas["2"]["declarantes"] == 1 and linhas["2"]["avisos_grupo"] == ["poucos_casos"]


def test_sem_cruzamento_por_grupo_o_hhi_do_grupo_fica_nulo_e_o_do_cnpj_vem_do_sici():
    por = {l["ibge"]: l for l in oa.linhas_do_grupo(["A"], CAD, MUNS, None)}
    assert por["1"]["hhi_grupo"] is None and por["1"]["faixa_grupo"] is None and por["1"]["hhi_cnpj"] == 4600


def test_resumo_conta_o_conjunto_inteiro():
    r = oa.resumo_do_grupo(oa.linhas_do_grupo(["A", "B"], CAD, MUNS, MG))
    assert r == {"municipios": 2, "com_mais_da_metade": 2, "com_um_so_declarante": 1, "acessos": 710, "ufs": 2}
    assert oa.resumo_do_grupo([])["municipios"] == 0


def test_parcela_exatamente_metade_nao_conta_como_mais_da_metade():
    muns = {"1": {"acessos": 200, "operadores_count": 2, "hhi": 5000}}
    cad = {"A": {"por_municipio": {"1": {"nome": "X", "uf": "SP", "acessos": 100}}}}
    assert oa.resumo_do_grupo(oa.linhas_do_grupo(["A"], cad, muns, None))["com_mais_da_metade"] == 0


def test_pagina_filtra_ordena_e_desempata_pelo_ibge():
    muns = {str(i): {"acessos": 100, "operadores_count": 2, "hhi": 5000} for i in (3, 1, 2)}
    cad = {"A": {"por_municipio": {str(i): {"nome": n, "uf": "SP" if i != 2 else "MG", "acessos": 50} for i, n in ((3, "Árvore"), (1, "arvoredo"), (2, "Zeta"))}}}
    linhas = oa.linhas_do_grupo(["A"], cad, muns, None)
    assert [l["ibge"] for l in oa.pagina(linhas, None, None, "acessos", True, 10, 0)["items"]] == ["3", "2", "1"]      # empate de acessos: IBGE (desc)
    assert [l["ibge"] for l in oa.pagina(linhas, None, None, "acessos", False, 10, 0)["items"]] == ["1", "2", "3"]
    assert oa.pagina(linhas, "mg", None, "nome", False, 10, 0)["total"] == 1
    assert sorted(l["ibge"] for l in oa.pagina(linhas, None, "ARVORE", "nome", False, 10, 0)["items"]) == ["1", "3"]   # sem acento nem caixa
    p = oa.pagina(linhas, None, None, "nome", False, 1, 1)
    assert p["total"] == 3 and len(p["items"]) == 1
    with pytest.raises(oa.OndeAtuaErro):
        oa.pagina(linhas, None, None, "ranking", True, 10, 0)


def test_parcela_nula_vai_para_o_fim_na_ordem_decrescente():
    linhas = [{"ibge": "1", "nome": "A", "uf": "SP", "acessos": 5, "parcela": None, "hhi_grupo": None},
              {"ibge": "2", "nome": "B", "uf": "SP", "acessos": 5, "parcela": 10.0, "hhi_grupo": 3000}]
    assert [l["ibge"] for l in oa.pagina(linhas, None, None, "parcela", True, 10, 0)["items"]] == ["2", "1"]


def test_panorama_conta_municipios_por_faixa_e_a_soma_fecha():
    doc = {"snapshot_date": "d", "mes_referencia": "2026-09", "natureza": "inferido", "fonte": "f", "limites": "l", "faixas": {},
           "resumo": {"municipios": 4, "mudam_de_faixa": 1, "transicoes": {}, "grupos_com_mais_de_um_cnpj_no_mercado": 0},
           "ufs": {"SP": {"hhi_cnpj": 1}, "MG": {"hhi_cnpj": 2}},
           "municipios": {"1": {"uf": "SP", "faixa_cnpj": "competitivo", "faixa_grupo": "moderado"}, "2": {"uf": "SP", "faixa_cnpj": "concentrado", "faixa_grupo": "concentrado"},
                          "3": {"uf": "MG", "faixa_cnpj": None, "faixa_grupo": None}, "4": {"uf": "MG", "faixa_cnpj": "moderado", "faixa_grupo": "moderado"}}}
    r = resumo_mercado_grupos(doc, {"hhi": 624, "acessos": 10, "n_operadoras": 2})
    assert r["resumo"]["por_faixa_cnpj"] == {"competitivo": 1, "moderado": 1, "concentrado": 1, "sem_dado": 1}
    assert sum(r["resumo"]["por_faixa_grupo"].values()) == 4 == r["resumo"]["municipios"]
    assert r["ufs"]["SP"]["municipios"] == 2 and r["ufs"]["SP"]["municipios_por_faixa_grupo"]["moderado"] == 1 and r["ufs"]["MG"]["municipios_por_faixa_cnpj"]["sem_dado"] == 1
    assert r["ufs"]["SP"]["hhi_cnpj"] == 1                                                    # o que já existia continua
    assert r["brasil"]["hhi_cnpj"] == 624
    assert "brasil" not in resumo_mercado_grupos(doc)
