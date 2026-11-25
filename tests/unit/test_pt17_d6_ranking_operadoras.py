# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PT-17 (D6, RANKINGS-E6): variação em 12 meses sem piso: base visível, "base pequena" só rótulo, ninguém some da lista."""
from api.services import sici_indicadores as s


def _op(empresa, acessos, abs_aa, pct_aa):
    return {"empresa": empresa, "uf": "SP", "acessos": acessos, "share_br": 1.0, "ufs": {"SP": acessos}, "meses_declinio": 0, "em_declinio": False,
            "var_aa": {"abs": abs_aa, "pct": pct_aa}, "var_mm": {"abs": 0, "pct": 0.0}}


IND = {"snapshot_date": "2026-11-22", "mes_referencia": "2026-08", "fonte": "Anatel", "ufs": {"SP": {"acessos": 100}},
       "operadoras": {
           "1": _op("MINI", 9334, 9333, 933300.0),                    # base 1: o percentual domina a ordem, mas a base está à vista
           "2": _op("GRANDE", 8_542_210, 736_000, 9.43),               # base 7.806.210
           "3": _op("ENTRANTE", 500, 500, None),                       # base 0: sem percentual
           "4": _op("NA FRONTEIRA", 2000, 1001, 101.1),                 # base 999: pequena
           "5": _op("NO LIMITE", 3000, 2000, 200.0),                    # base 1.000: não é pequena
       }}


def _linhas(ordem, asc=False):
    return s.ranking_operadoras(IND, None, ordem, asc, 50, 0)


def test_base_de_cada_linha_e_rotulo_de_base_pequena_so_abaixo_de_1000():
    r = _linhas("var_aa_pct")
    por = {x["empresa"]: x for x in r["items"]}
    assert por["MINI"]["base_aa"] == 1 and por["MINI"]["base_pequena"] is True
    assert por["GRANDE"]["base_aa"] == 7_806_210 and por["GRANDE"]["base_pequena"] is False
    assert por["ENTRANTE"]["base_aa"] == 0 and por["ENTRANTE"]["base_pequena"] is True
    assert por["NA FRONTEIRA"]["base_aa"] == 999 and por["NA FRONTEIRA"]["base_pequena"] is True
    assert por["NO LIMITE"]["base_aa"] == 1000 and por["NO LIMITE"]["base_pequena"] is False
    assert r["base_pequena_abaixo_de"] == 1000 == s.BASE_PEQUENA_ACESSOS


def test_nenhum_piso_a_base_pequena_nao_tira_a_linha_nem_muda_a_posicao():
    r = _linhas("var_aa_pct")
    assert [x["empresa"] for x in r["items"]][:2] == ["MINI", "NO LIMITE"]        # a ordem é só a do percentual
    assert r["total"] == len(IND["operadoras"]) == 5


def test_sem_percentual_vai_para_o_fim_nos_dois_sentidos_e_nao_some():
    for asc in (False, True):
        r = _linhas("var_aa_pct", asc)
        assert r["total"] == 5 and r["items"][-1]["empresa"] == "ENTRANTE"


def test_ordem_por_variacao_absoluta_existe_e_ordena_por_acessos():
    r = _linhas("var_aa_abs")
    assert r["items"][0]["empresa"] == "GRANDE"
    assert [x["var_aa_abs"] for x in r["items"]] == sorted((x["var_aa_abs"] for x in r["items"]), reverse=True)
    assert "acessos" in r["criterio"] and "absoluta" in r["criterio"]


def test_rotulo_da_variacao_em_12_meses_diz_acessos():
    assert "(acessos)" in s.ORDENS_OPERADORA["var_aa_pct"][0] and "(acessos)" in s.ORDENS_OPERADORA["var_aa_abs"][0]
