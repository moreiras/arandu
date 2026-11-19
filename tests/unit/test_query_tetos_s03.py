# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""consulta larga demais é recusada na validação, antes de ocupar a CPU."""
import time

import pytest

from api import query as q


def _ou(n):
    return {"or": [{"field": "name", "op": "contains", "value": f"x{i}"} for i in range(n)]}


def test_mil_predicados_e_recusado_em_milissegundos():
    t = time.perf_counter()
    with pytest.raises(q.QueryError, match="predicados"):
        q.validate("asns", {"filter": _ou(1000)})
    assert time.perf_counter() - t < 0.5


def test_no_teto_passa():
    q.limitar({"filter": _ou(q.MAX_PREDICADOS)})


@pytest.mark.parametrize("corpo,trecho", [
    ({"filter": {"field": "asn", "op": "in", "value": list(range(q.MAX_VALORES_LISTA + 1))}}, "lista de valores"),
    ({"filter": {"field": "x", "op": "within_radius", "radius_km": 10, "centers": [[0, 0]] * (q.MAX_CENTROS + 1)}}, "centros"),
    ({"select": ["a"] * (q.MAX_SELECT + 1)}, "select"),
    ({"sort": [{"field": "a"}] * (q.MAX_SORT + 1)}, "sort"),
    ({"group_by": ["a"] * (q.MAX_GROUP_BY + 1)}, "group_by"),
    ({"aggregate": [{"fn": "count"}] * (q.MAX_AGREGACOES + 1)}, "aggregate"),
    ({"limit": "1000"}, "inteiro"), ({"limit": 1.5}, "inteiro"), ({"limit": True}, "inteiro"), ({"page": [2]}, "inteiro"),
    ({"limit": 0}, "intervalo"), ({"limit": 5000}, "intervalo"), ({"page": 10**9}, "intervalo"),
    ({"select": "name"}, "lista"),
])
def test_corpo_largo_ou_malformado_da_400_com_mensagem(corpo, trecho):
    with pytest.raises(q.QueryError, match=trecho):
        q.limitar(corpo)


def test_agregacao_com_grupos_demais_e_recusada():
    linhas = [{"k": i} for i in range(q.MAX_GRUPOS + 1)]
    with pytest.raises(q.QueryError, match="grupos"):
        q._aggregate(linhas, ["k"], [{"fn": "count"}])
