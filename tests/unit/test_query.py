# SPDX-License-Identifier: AGPL-3.0-or-later
"""T0 — motor de consulta (`api/query.py`): filtros, agregação, ordenação, paginação, validação."""
import pytest

from api import query as q

ROWS = [
    {"asn": 1, "nome": "Alfa Telecom", "uf": "SP", "clientes": 100, "ixps": ["sp", "rj"], "v4": {"cov": 90.0}, "lat": -23.5, "lon": -46.6},
    {"asn": 2, "nome": "Beta Net", "uf": "RJ", "clientes": 50, "ixps": ["rj"], "v4": {"cov": 10.0}, "lat": -22.9, "lon": -43.2},
    {"asn": 3, "nome": "Gama Fibra", "uf": "SP", "clientes": None, "ixps": [], "v4": {"cov": 55.5}, "lat": -23.0, "lon": -46.0},
    {"asn": 4, "nome": "Delta", "uf": "MG", "clientes": 300, "ixps": ["mg", "sp"], "lat": None, "lon": None},
    {"asn": 5, "nome": "épsilon ltda", "uf": "SP", "clientes": 100, "ixps": ["sp"]},
]


def run(body):
    return q.execute(ROWS, body)


def asns(result):
    return [r["asn"] for r in result["items"]]


# ── Operadores de predicado ────────────────────────────────────────────────

@pytest.mark.parametrize("pred, expected", [
    ({"field": "uf", "op": "eq", "value": "SP"}, [1, 3, 5]),
    ({"field": "uf", "op": "ne", "value": "SP"}, [2, 4]),
    ({"field": "clientes", "op": "gt", "value": 100}, [4]),
    ({"field": "clientes", "op": "gte", "value": 100}, [1, 4, 5]),
    ({"field": "clientes", "op": "lt", "value": 100}, [2]),
    ({"field": "clientes", "op": "lte", "value": 100}, [1, 2, 5]),
    ({"field": "uf", "op": "in", "value": ["RJ", "MG"]}, [2, 4]),
    ({"field": "uf", "op": "nin", "value": ["RJ", "MG"]}, [1, 3, 5]),
    ({"field": "ixps", "op": "contains", "value": "rj"}, [1, 2]),
    ({"field": "ixps", "op": "ncontains", "value": "rj"}, [3, 4, 5]),
    ({"field": "nome", "op": "contains", "value": "telecom"}, [1]),
    ({"field": "clientes", "op": "exists", "value": True}, [1, 2, 4, 5]),
    ({"field": "clientes", "op": "exists", "value": False}, [3]),
    ({"field": "v4.cov", "op": "gt", "value": 50}, [1, 3]),
])
def test_operadores(pred, expected):
    assert asns(run({"filter": pred, "sort": [{"field": "asn"}]})) == expected


def test_comparacao_nunca_casa_none_ou_campo_ausente():
    assert asns(run({"filter": {"field": "clientes", "op": "lt", "value": 1000}, "sort": [{"field": "asn"}]})) == [1, 2, 4, 5]


def test_comparacao_com_tipos_incompativeis_nao_levanta():
    assert run({"filter": {"field": "nome", "op": "gt", "value": 5}})["total"] == 0


def test_eq_none_casa_campo_ausente():
    assert asns(run({"filter": {"field": "v4", "op": "eq", "value": None}, "sort": [{"field": "asn"}]})) == [4, 5]


# ── Combinadores ───────────────────────────────────────────────────────────

def test_and():
    f = {"and": [{"field": "uf", "op": "eq", "value": "SP"}, {"field": "ixps", "op": "contains", "value": "rj"}]}
    assert asns(run({"filter": f})) == [1]


def test_or():
    f = {"or": [{"field": "uf", "op": "eq", "value": "RJ"}, {"field": "uf", "op": "eq", "value": "MG"}]}
    assert sorted(asns(run({"filter": f}))) == [2, 4]


def test_not():
    f = {"not": {"field": "uf", "op": "eq", "value": "SP"}}
    assert sorted(asns(run({"filter": f}))) == [2, 4]


def test_diretos_em_sp_e_nao_no_rj():
    f = {"and": [{"field": "ixps", "op": "contains", "value": "sp"}, {"field": "ixps", "op": "ncontains", "value": "rj"}]}
    assert sorted(asns(run({"filter": f}))) == [4, 5]


def test_sem_filtro_devolve_tudo():
    assert run({})["total"] == len(ROWS)


# ── Predicados inválidos ───────────────────────────────────────────────────

@pytest.mark.parametrize("flt", [
    {"field": "uf", "op": "xyz", "value": 1},
    {"op": "eq", "value": 1},
    {"field": 3, "op": "eq", "value": 1},
    "isto não é um filtro",
])
def test_filtro_invalido_levanta(flt):
    with pytest.raises(q.QueryError):
        run({"filter": flt})


def test_in_exige_lista():
    with pytest.raises(q.QueryError):
        run({"filter": {"field": "uf", "op": "in", "value": "SP"}})


def test_corpo_nao_objeto():
    with pytest.raises(q.QueryError):
        q.execute(ROWS, [1, 2])


# ── Geo ────────────────────────────────────────────────────────────────────

def test_within_radius():
    f = {"op": "within_radius", "radius_km": 100, "centers": [[-23.55, -46.63]]}   # São Paulo
    assert sorted(asns(run({"filter": f}))) == [1, 3]


def test_within_radius_varios_centros():
    f = {"op": "within_radius", "radius_km": 100, "centers": [[-23.55, -46.63], [-22.9, -43.2]]}
    assert sorted(asns(run({"filter": f}))) == [1, 2, 3]


def test_within_radius_ignora_linha_sem_coordenada():
    f = {"op": "within_radius", "radius_km": 99999, "centers": [[0, 0]]}
    assert sorted(asns(run({"filter": f}))) == [1, 2, 3]


def test_within_radius_exige_parametros():
    with pytest.raises(q.QueryError):
        run({"filter": {"op": "within_radius", "centers": [[0, 0]]}})


# ── Ordenação ──────────────────────────────────────────────────────────────

def test_sort_asc_nulos_por_ultimo():
    assert asns(run({"sort": [{"field": "clientes"}, {"field": "asn"}]})) == [2, 1, 5, 4, 3]


def test_sort_desc_nulos_por_ultimo():
    assert asns(run({"sort": [{"field": "clientes", "dir": "desc"}, {"field": "asn"}]})) == [4, 1, 5, 2, 3]


def test_sort_multiplas_chaves_e_estavel():
    assert asns(run({"sort": [{"field": "uf"}, {"field": "clientes", "dir": "desc"}]})) == [4, 2, 1, 5, 3]


def test_sort_invalido():
    with pytest.raises(q.QueryError):
        run({"sort": [{"dir": "asc"}]})


# ── Paginação e projeção ───────────────────────────────────────────────────

def test_paginacao():
    r = run({"sort": [{"field": "asn"}], "limit": 2, "page": 2})
    assert asns(r) == [3, 4]
    assert (r["total"], r["page"], r["limit"], r["pages"]) == (5, 2, 2, 3)


def test_pagina_alem_do_fim():
    r = run({"sort": [{"field": "asn"}], "limit": 2, "page": 9})
    assert r["items"] == [] and r["total"] == 5


def test_limite_maximo_e_minimo():
    assert run({"limit": 99999})["limit"] == 1000
    assert run({"limit": 0})["limit"] == 1


def test_lista_vazia_tem_zero_paginas():
    assert run({"filter": {"field": "uf", "op": "eq", "value": "ZZ"}})["pages"] == 0


def test_select_projeta_e_preenche_none():
    r = run({"filter": {"field": "asn", "op": "eq", "value": 5}, "select": ["asn", "v4.cov", "nome"]})
    assert r["items"] == [{"asn": 5, "v4.cov": None, "nome": "épsilon ltda"}]


# ── Agregação ──────────────────────────────────────────────────────────────

def _groups(result):
    return {tuple(g["key"].values()): g for g in result["groups"]}


def test_group_by_count_padrao():
    r = run({"group_by": ["uf"]})
    assert r["mode"] == "aggregate"
    g = _groups(r)
    assert g[("SP",)]["count"] == 3 and g[("RJ",)]["count"] == 1 and g[("MG",)]["count"] == 1


def test_sum_avg_min_max_ignoram_nulos():
    r = run({"group_by": ["uf"], "aggregate": [
        {"fn": "sum", "field": "clientes", "as": "s"},
        {"fn": "avg", "field": "clientes", "as": "a"},
        {"fn": "min", "field": "clientes", "as": "mn"},
        {"fn": "max", "field": "clientes", "as": "mx"},
    ]})
    sp = _groups(r)[("SP",)]
    assert (sp["s"], sp["a"], sp["mn"], sp["mx"]) == (200, 100.0, 100, 100)


def test_agregacao_sem_valores_devolve_none():
    r = run({"filter": {"field": "asn", "op": "eq", "value": 3}, "group_by": ["uf"],
             "aggregate": [{"fn": "sum", "field": "clientes", "as": "s"}]})
    assert r["groups"][0]["s"] is None


def test_distinct():
    r = run({"group_by": [], "aggregate": [{"fn": "distinct", "field": "uf", "as": "n"}]})
    assert r["groups"][0]["n"] == 3


def test_agregacao_sem_group_by_e_um_grupo_so():
    r = run({"aggregate": [{"fn": "count"}]})
    assert len(r["groups"]) == 1 and r["groups"][0]["count"] == 5


@pytest.mark.parametrize("body", [
    {"group_by": ["uf"], "aggregate": [{"fn": "median", "field": "clientes"}]},
    {"group_by": ["uf"], "aggregate": [{"fn": "sum"}]},
    {"group_by": "uf"},
    {"group_by": ["uf"], "aggregate": "count"},
])
def test_agregacao_invalida(body):
    with pytest.raises(q.QueryError):
        run(body)


# ── Validação contra o schema ──────────────────────────────────────────────

def test_validate_campo_inexistente_lista_opcoes():
    with pytest.raises(q.QueryError) as e:
        q.validate("asns", {"filter": {"field": "campo_que_nao_existe", "op": "eq", "value": 1}})
    assert "Campos válidos" in str(e.value)


def test_validate_collection_invalida():
    with pytest.raises(q.QueryError):
        q.validate("nao_existe", {})


def test_validate_filtro_profundo_demais():
    flt = {"field": "asn", "op": "eq", "value": 1}
    for _ in range(q.MAX_FILTER_DEPTH + 1):
        flt = {"not": flt}
    with pytest.raises(q.QueryError):
        q.validate("asns", {"filter": flt})


def test_validate_aceita_corpo_simples():
    q.validate("asns", {"filter": {"field": "asn", "op": "eq", "value": 1}, "limit": 10})


def test_schema_lista_operadores_e_collections():
    s = q.schema()
    assert "eq" in s["operators"] and "asns" in s["collections"]
    with pytest.raises(q.QueryError):
        q.schema("nao_existe")
