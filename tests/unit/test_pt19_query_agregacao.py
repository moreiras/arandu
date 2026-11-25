# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PT-19 / TRANSV-E10: a agregação do `query` respeita `sort`, `limit` e `page`, e `count` com campo conta valores não nulos."""
import pytest

from api import query as q
from api import query_colunar
from core import colunar

ROWS = [
    {"ibge": "1", "empresa": "Alfa", "uf": "ES", "acessos": 10, "nota": 1},
    {"ibge": "2", "empresa": "Beta", "uf": "ES", "acessos": 70, "nota": None},
    {"ibge": "3", "empresa": "Alfa", "uf": "ES", "acessos": 30},
    {"ibge": "4", "empresa": "Gama", "uf": "ES", "acessos": 25, "nota": 2},
    {"ibge": "5", "empresa": "Delta", "uf": "ES", "acessos": 5, "nota": 3},
    {"ibge": "6", "empresa": "Beta", "uf": "ES", "acessos": 5},
]
POR_EMPRESA = {"group_by": ["empresa"], "aggregate": [{"fn": "sum", "field": "acessos"}]}


def run(**extra):
    return q.execute(ROWS, {**POR_EMPRESA, **extra})


def chaves(r):
    return [g["key"]["empresa"] for g in r["groups"]]


def test_sem_sort_nem_limit_a_ordem_de_aparicao_e_todos_os_grupos_ficam():
    r = run()
    assert chaves(r) == ["Alfa", "Beta", "Gama", "Delta"] and r["total_grupos"] == 4
    assert "limit" not in r and "page" not in r


def test_sort_por_alias_do_agregado_desc_e_asc():
    assert chaves(run(sort=[{"field": "sum_acessos", "dir": "desc"}])) == ["Beta", "Alfa", "Gama", "Delta"]
    assert chaves(run(sort=[{"field": "sum_acessos", "dir": "asc"}])) == ["Delta", "Gama", "Alfa", "Beta"]


def test_sort_por_as_explicito_e_por_count():
    r = q.execute(ROWS, {"group_by": ["empresa"], "aggregate": [{"fn": "count"}, {"fn": "max", "field": "acessos", "as": "maior"}],
                         "sort": [{"field": "count", "dir": "desc"}, {"field": "maior", "dir": "asc"}]})
    assert [(g["count"], g["maior"]) for g in r["groups"]] == [(2, 30), (2, 70), (1, 5), (1, 25)]


def test_sort_por_campo_de_group_by_texto_desc():
    assert chaves(run(sort=[{"field": "empresa", "dir": "desc"}])) == ["Gama", "Delta", "Beta", "Alfa"]


def test_sort_com_nulo_deixa_o_nulo_por_ultimo():
    r = q.execute(ROWS, {"group_by": ["empresa"], "aggregate": [{"fn": "sum", "field": "nota", "as": "n"}], "sort": [{"field": "n", "dir": "desc"}]})
    assert chaves(r) == ["Delta", "Gama", "Alfa", "Beta"] and r["groups"][-1]["n"] is None


def test_limit_corta_os_grupos_e_informa_o_total():
    r = run(sort=[{"field": "sum_acessos", "dir": "desc"}], limit=2)
    assert chaves(r) == ["Beta", "Alfa"] and r["total_grupos"] == 4 and r["limit"] == 2 and r["page"] == 1 and r["pages"] == 2
    assert r["matched"] == 6


def test_page_pagina_os_grupos_ordenados():
    p2 = run(sort=[{"field": "sum_acessos", "dir": "desc"}], limit=3, page=2)
    assert chaves(p2) == ["Delta"] and p2["page"] == 2 and p2["pages"] == 2
    assert run(limit=3, page=3)["groups"] == []


def test_sort_que_nao_e_grupo_nem_agregado_e_recusado_com_as_opcoes():
    with pytest.raises(q.QueryError, match="sum_acessos"):
        run(sort=[{"field": "acessos", "dir": "desc"}])


def test_validate_aceita_alias_no_sort_e_recusa_campo_inexistente():
    q.validate("acessos_municipio", {**POR_EMPRESA, "sort": [{"field": "sum_acessos", "dir": "desc"}], "limit": 5})
    with pytest.raises(q.QueryError, match="não existe"):
        q.validate("acessos_municipio", {"group_by": ["campo_que_nao_existe"]})


def test_count_sem_campo_conta_linhas_e_com_campo_conta_valores_nao_nulos():
    r = q.execute(ROWS, {"group_by": ["uf"], "aggregate": [{"fn": "count", "as": "linhas"}, {"fn": "count", "field": "nota", "as": "com_nota"}]})
    g = r["groups"][0]
    assert g["linhas"] == 6 and g["com_nota"] == 3          # nulo e ausente não contam


def test_count_com_campo_por_grupo():
    r = q.execute(ROWS, {"group_by": ["empresa"], "aggregate": [{"fn": "count", "field": "nota"}]})
    assert {g["key"]["empresa"]: g["count"] for g in r["groups"]} == {"Alfa": 1, "Beta": 0, "Gama": 1, "Delta": 1}


def test_motor_colunar_agrega_igual_ao_motor_por_linhas(tmp_path):
    colunas = ["ibge", "empresa", "uf", "acessos", "nota"]
    colunar.escrever(tmp_path / "t.col", {c: [r.get(c) for r in ROWS] for c in colunas})
    tab = colunar.TabelaColunar(tmp_path / "t.col")
    corpo = {"group_by": ["empresa"], "aggregate": [{"fn": "sum", "field": "acessos"}, {"fn": "count", "field": "nota"}],
             "sort": [{"field": "sum_acessos", "dir": "desc"}], "limit": 2, "page": 2}
    assert query_colunar.execute(tab, dict(corpo)) == q.execute(ROWS, dict(corpo))
