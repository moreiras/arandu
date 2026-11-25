# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Consumidor.gov.br: bases mínimas, casamento da cidade ao IBGE e meses sem dado."""
from core import marcas as m
from products.consumidor.build import MIN_BASE, ResolvedorMunicipios, calcular, metricas

IBGE = {"municipios": {"3170206": {"nome": "Uberaba", "uf": "MG", "populacao": 1}, "3167202": {"nome": "Ubá", "uf": "MG", "populacao": 1}, "3550308": {"nome": "São Paulo", "uf": "SP", "populacao": 1},
                       "3100001": {"nome": "Igual", "uf": "SP", "populacao": 1}, "3100002": {"nome": "Igual", "uf": "SP", "populacao": 1}, "3200003": {"nome": "Sao Paulo Dois", "uf": "RJ", "populacao": 1}}}


def test_media_indice_e_nota_so_com_base_minima():
    v = [100, 90, MIN_BASE, 20, MIN_BASE - 1, 200, MIN_BASE, 90]
    r = metricas(v)
    assert r["indice_solucao"] == round(100 * 20 / MIN_BASE, 1) and r["tempo_medio_dias"] is None and r["nota_media"] == 3.0 and r["pct_respondidas"] == 90.0
    assert metricas([10, 10, 5, 2, 10, 50, 5, 20])["pct_respondidas"] is None            # 10 reclamações: nem a % entra
    assert metricas([0] * 8)["indice_solucao"] is None                                    # nulo, nunca zero nem divisão por zero


def test_cidade_casa_por_nome_e_uf_sem_acento_e_repetida_nao_casa():
    r = ResolvedorMunicipios(IBGE)
    assert r.resolver("SP", "SAO PAULO") == "3550308" and r.resolver("SP", "sao paulo ") == "3550308" and r.resolver("RJ", "São Paulo") is None
    assert r.resolver("SP", "Igual") is None                                              # dois municípios com o mesmo nome na UF: não se adivinha
    assert r.resolver("MG", "Cidade que não existe") is None


def test_interrogacao_no_lugar_de_acento_so_casa_se_for_unico():
    r = ResolvedorMunicipios(IBGE)
    assert r.resolver("MG", "Ub?") == "3167202" and r.com_interrogacao == 1                # Ubá, não Uberaba (outro tamanho)
    assert r.resolver("MG", "Ub?????") == "3170206"                                       # cinco letras a mais: Uberaba
    assert r.resolver("SP", "?ao Paulo") == "3550308"


def _norm(meses: dict) -> dict:
    return {"fonte": "t", "url": "u", "resumo": {}, "meses": meses}


def _mes(codigo: str, n: int) -> dict:
    celula = {"marca": "Alfa", "uf": "SP", "cidade": "São Paulo", "n": n, "respondidas": n, "avaliadas": n, "resolvidas": n // 2, "tempo_n": n, "tempo_soma": 5 * n, "nota_n": n, "nota_soma": 3 * n}
    return {"codigo": codigo, "tamanho": 1, "cidades": [celula], "assuntos": [{"marca": "Alfa", "assunto": "Internet", "n": n}], "grupos": [{"marca": "Alfa", "grupo": "Cobrança", "n": n}], "resumo": {"telecom": n}}


def test_mes_ilegivel_fica_na_janela_como_ausente_e_nao_entra_na_soma():
    meses = {f"2026-0{i}": _mes(str(i), 40) for i in (1, 2, 4)}
    meses["2026-03"] = {"codigo": "3", "tamanho": 1, "indisponivel": "zip ilegível"}
    doc, por_uf = calcular(_norm(meses), m.carregar_curada(), {}, {}, {}, IBGE)
    assert doc["janela"]["meses_ausentes"] == ["2026-03"] and doc["janela"]["meses_com_dado"] == 3 and "3 de 4" in doc["janela"]["aviso"]
    assert doc["marcas"][0]["janela"]["n"] == 120 and [x["mes"] for x in doc["marcas"][0]["por_mes"]] == ["2026-01", "2026-02", "2026-04"]
    assert [x["mes"] for x in doc["setor_por_mes"]] == ["2026-01", "2026-02", "2026-04"]
    assert por_uf["SP"]["3550308"]["total"]["n"] == 120 and doc["cidades"]["pct_com_codigo_ibge"] == 100.0


def test_celula_pequena_nao_vai_para_o_municipio_mas_entra_no_total():
    meses = {"2026-01": {**_mes("1", 4), "cidades": [{"marca": "Alfa", "uf": "SP", "cidade": "São Paulo", "n": 4, "respondidas": 4, "avaliadas": 0, "resolvidas": 0, "tempo_n": 4, "tempo_soma": 20, "nota_n": 0, "nota_soma": 0}]}}
    doc, por_uf = calcular(_norm(meses), m.carregar_curada(), {}, {}, {}, IBGE)
    assert por_uf["SP"]["3550308"]["total"]["n"] == 4 and por_uf["SP"]["3550308"]["itens"] == [] and doc["uf"] == [] and doc["assuntos"] == []      # 4 < 5: nem empresa × município, nem × UF, nem × assunto


def test_marca_sky_inclui_zaaz_pela_declaracao_ao_sici():
    """P2 (decisão do mantenedor em 2026-11-25): a raiz 65476221 (Zaaz no Ne) entra na marca SKY pelo grupo "SKY/ZAAZ" declarado ao SICI."""
    sky = m.carregar_curada()["marcas"][m.normalizar("SKY")]
    assert sky["raizes"] == ["00497373", "65476221"]
    assert "SICI" in sky["base"] and sky["data"] == "2026-11-25"
