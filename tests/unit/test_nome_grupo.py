# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Nome do grupo societário por regra visível (D5): marca curada, senão o CNPJ com mais acessos no SICI; nunca o nome mais longo (MUN-E4)."""
from core.nome_grupo import nome_do_grupo
from products.sici_indicadores.build import calcular_mercado_grupos

NOMES = {"11111111000101": "DESKTOP", "22222222000102": "CLARO S.A.", "33333333000103": "EMBRATEL TV SAT TELECOMUNICACOES LTDA"}
CURADA = {"marcas": {"CLARO": {"marca": "CLARO", "raizes": ["22222222", "44444444"], "base": "b1"},
                     "NET": {"marca": "NET", "raizes": ["22222222", "44444444"], "base": "b2"},
                     "EMBRATEL": {"marca": "EMBRATEL", "raizes": ["33333333"], "base": "b3"}}}


def _nome(cnpjs, acessos, curada=None):
    return nome_do_grupo(cnpjs, acessos, lambda c: NOMES.get(c, c), curada)


def test_marca_curada_que_cobre_o_grupo_vence_o_acesso():
    r = _nome(list(NOMES) + ["44444444000104"], {"11111111000101": 9_000_000}, CURADA)
    assert (r["nome"], r["nome_regra"], r["nome_base"]) == ("CLARO", "marca_curada", "b1")          # mais raízes cobertas; empate com NET pela ordem da tabela


def test_marca_que_cobre_so_parte_do_conjunto_menor_nao_nomeia():
    r = _nome(["22222222000102", "11111111000101"], {"22222222000102": 5, "11111111000101": 9}, CURADA)
    assert r["nome_regra"] == "maior_acesso_sici" and r["nome"] == "DESKTOP"                          # CLARO exige também a raiz 44444444


def test_sem_marca_vale_o_cnpj_com_mais_acessos_e_nao_o_nome_mais_longo():
    r = _nome(list(NOMES), {"11111111000101": 100, "22222222000102": 300, "33333333000103": 200})
    assert (r["nome"], r["nome_regra"], r["nome_base"]) == ("CLARO S.A.", "maior_acesso_sici", "22222222000102")
    assert r["nome_regra_texto"]


def test_empate_de_acessos_vai_para_o_menor_cnpj_e_sem_acesso_algum_tambem():
    assert _nome(["22222222000102", "11111111000101"], {"22222222000102": 5, "11111111000101": 5})["nome"] == "DESKTOP"
    r = _nome(["22222222000102", "11111111000101"], {})
    assert (r["nome"], r["nome_regra"]) == ("DESKTOP", "menor_cnpj")


def test_lider_do_mercado_municipal_usa_a_mesma_regra():
    muns = {"1": {"uf": "PR", "nome": "Curitiba", "operadores": [
        {"cnpj": "11111111000101", "empresa": "DESKTOP", "acessos": 10}, {"cnpj": "22222222000102", "empresa": "CLARO S.A.", "acessos": 70},
        {"cnpj": "33333333000103", "empresa": "EMBRATEL TV SAT TELECOMUNICACOES LTDA", "acessos": 5}]}}
    grupos = [{"grupo_id": "grp_11111111", "cnpjs": list(NOMES), "classificacao": "parcial"}]
    sem = calcular_mercado_grupos(muns, grupos)["municipios"]["1"]["lider_grupo"]
    assert sem["empresa"] == "CLARO S.A." and sem["nome_regra"] == "maior_acesso_sici"                # não "EMBRATEL TV SAT ...", o nome mais longo
    com = calcular_mercado_grupos(muns, [{**grupos[0], "cnpjs": list(NOMES) + ["44444444000104"]}], CURADA)["municipios"]["1"]["lider_grupo"]
    assert com["empresa"] == "CLARO" and com["nome_regra"] == "marca_curada"
