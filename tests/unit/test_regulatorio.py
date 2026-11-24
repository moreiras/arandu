# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Regulatório complementar: FUST por município, UF, programa e edital."""
import pytest

from products.regulatorio.build import calcular_fust

IBGE = {"1": {"nome": "Alfa", "uf": "AA", "populacao_estimada": 20000}, "2": {"nome": "Beta", "uf": "AA", "populacao": 5000}, "3": {"nome": "Gama", "uf": "BB", "populacao": 1000}}


def _c(ibge, status, valor, programa="1.1 - Escolas", origem="Ed 1", base="IBGE_2022", tipo="Infra. Rede - Escolas"):
    return {"id": "x", "origem": origem, "tipo": tipo, "programa": programa, "nivel": "Município", "base_ibge": base, "ibge": ibge, "uf": "AA", "municipio": "m", "status": status, "prazo": None, "investimento": valor}


ITENS = [_c("1", "Atendido", 100.0), _c("1", "A vencer", 50.5), _c("1", "Em apuração", None, programa="2.6 - UBS", origem="Ed 2"), _c("2", "Atendido", 10.0, base="IBGE_2010"), _c("9", "Atendido", 1.0)]


def test_agrega_por_municipio_e_situacao():
    r = calcular_fust(ITENS, IBGE)
    m = r["municipios"]["1"]
    assert (m["compromissos"], m["atendidos"], m["a_vencer"], m["em_apuracao"]) == (3, 1, 1, 1)
    assert m["investimento"] == pytest.approx(150.5) and m["programas"] == {"1.1": 2, "2.6": 1} and m["por_10mil_hab"] == 1.5
    assert "3" not in r["municipios"] and "9" not in r["municipios"]


def test_uf_brasil_programas_editais_e_casamento():
    r = calcular_fust(ITENS, IBGE)
    assert r["ufs"]["AA"]["compromissos"] == 4 and r["ufs"]["AA"]["municipios_com_compromisso"] == 2 and r["ufs"]["BB"]["compromissos"] == 0
    assert r["brasil"]["compromissos"] == 4 and r["brasil"]["municipios"] == 3 and r["brasil"]["municipios_com_compromisso"] == 2
    assert {p["codigo"]: p["compromissos"] for p in r["programas"]} == {"1.1": 3, "2.6": 1}
    assert [e["origem"] for e in r["editais"]] == ["Ed 1", "Ed 2"]
    c = r["casamento"]
    assert (c["compromissos"], c["com_municipio_no_ibge"], c["sem_municipio_no_ibge"], c["base_2010"], c["base_2022"], c["sem_investimento"]) == (5, 4, 1, 1, 3, 1)


# ── multas, faixas e satélites ──────────────────────────────────────────────

from products.regulatorio.build import calcular_faixas, calcular_multas, calcular_satelites  # noqa: E402


def _emp(raiz, grupo, saldo, multas=1, anos=None, cnpjs=None, situacoes=None):
    return {"raiz": raiz, "grupo": grupo, "entidade": f"E{raiz}", "cnpjs": cnpjs or [f"{raiz}000199"], "uf": "SP", "multas": multas, "original": saldo / 2, "pago": 10.0, "saldo": saldo,
            "situacoes": situacoes or {"Devedor": multas}, "anos": anos or {"2020": multas}}


def test_multas_ordena_por_saldo_soma_por_grupo_e_ano():
    emp = [_emp("1", "SCM", 100.0, 2, {"2020": 1, "2021": 1}), _emp("2", "SMP", 900.0, 1), _emp("1", "SMP", 50.0, 1, {"2021": 1}, cnpjs=["10000000000299", "10000000000100"])]
    r = calcular_multas(emp)
    assert [(e["raiz"], e["grupo"]) for e in r["empresas"]] == [("2", "SMP"), ("1", "SCM"), ("1", "SMP")]
    assert r["brasil"]["empresas"] == 3 and r["brasil"]["multas"] == 4 and r["brasil"]["saldo"] == 1050.0
    assert r["por_grupo"]["SMP"]["saldo"] == 950.0 and r["por_grupo"]["SCM"]["multas"] == 2
    assert r["por_ano"] == [{"ano": 2020, "SCM": 1, "SMP": 1, "total": 2}, {"ano": 2021, "SCM": 1, "SMP": 1, "total": 2}]
    assert r["empresas"][2]["cnpj_matriz"] == "10000000000100" and r["empresas"][0]["cnpj_matriz"] is None


def _f(ini, fim, dest=(), atr=()):
    return {"ini_mhz": ini, "fim_mhz": fim, "destinacao": [{"servico": s, "carater": c} for s, c in dest], "atribuicao": [{"servico": s, "carater": c} for s, c in atr]}


def test_faixas_de_interesse_pelas_que_se_sobrepoem():
    faixas = [_f(3300.0, 3400.0, [("MÓVEL PESSOAL", "Primário"), ("Radioamador", "Secundário")]), _f(3400.0, 3500.0, [("MÓVEL PESSOAL", "Primário")]), _f(100.0, 110.0, [("RADIODIFUSÃO", "Primário")])]
    r = calcular_faixas(faixas)
    ref = {x["nome"]: x for x in r["referencias"]}
    assert ref["3,5 GHz"]["faixas"] == 2 and ref["3,5 GHz"]["destinacao"][0] == {"servico": "MÓVEL PESSOAL", "carater": "Primário"} and ref["3,5 GHz"]["destinacao"][-1]["servico"] == "Radioamador"
    assert ref["700 MHz"]["faixas"] == 0 and ref["700 MHz"]["destinacao"] == []
    assert r["resumo"]["faixas"] == 3 and r["resumo"]["de_interesse"] == 12


def test_satelites_resumo_conta_vencidos_na_data_do_snapshot():
    d = lambda op, sat, tipo, status, val: {"operadora": op, "satelite": sat, "tipo": tipo, "status": status, "validade": val}      # noqa: E731
    t = {"direitos": [d("A", "S1", "Estrangeiro", "operação comercial", "2030-01-01"), d("A", "S1", "Estrangeiro", "operação comercial", "2030-01-01"), d("B", "S2", "Brasileiro", "operação comercial", "2026-01-31"),
                      d("C", "S3", "Estrangeiro", "pendente", None)], "ngeo": [{"objeto": "L1", "orbita": "BAIXA (LEO)"}, {"objeto": "L2", "orbita": "BAIXA (LEO)"}, {"objeto": "M1", "orbita": "MÉDIA (MEO)"},
                                                       {"objeto": "M1", "orbita": "MÉDIA (MEO)"}], "operando": [{}, {}]}        # a última é cópia exata: sai
    r = calcular_satelites(t, "2026-11-02")["resumo"]
    assert (r["direitos"], r["operadoras"], r["satelites"], r["vencidos_na_data"], r["ngeo"], r["operando"]) == (4, 3, 3, 1, 3, 2)
    assert r["por_tipo"] == {"Estrangeiro": 3, "Brasileiro": 1} and r["ngeo_por_orbita"] == {"BAIXA (LEO)": 2, "MÉDIA (MEO)": 1}
    assert r["ngeo_sistemas"] == 3
