# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T2 — as tabelas de prepending e de upstreams da página /bgp ordenam o que o snapshot publica e mostram os N primeiros: o snapshot
precisa ter o topo (e o fim) de CADA coluna ordenável, não só o da coluna do corte."""
from products.routing_analysis.as_path import _top_prependers, _upstream_diversity


def test_prepending_tem_o_maior_excesso_medio_mesmo_fora_do_topo_por_rotas():
    rotas = []
    for asn in range(100, 130):                                 # 30 ASes com muitas rotas e prepend curto
        rotas += [{"a": [1, 2, asn, asn]} for _ in range(10)]
    rotas += [{"a": [1, 2, 999] + [999] * 9}]                  # o AS 999: uma rota só, excesso 9
    lista = _top_prependers(rotas, {}, "v4", top_n=5)
    asns = {r["asn"] for r in lista}
    assert 999 in asns, "maior excesso médio"
    assert max(lista, key=lambda r: r["avg_excess"])["asn"] == 999
    assert len(lista) < 30, "corte segue pequeno: união dos extremos de cada coluna"


def test_upstreams_tem_o_maior_numero_de_rotas_mesmo_fora_do_topo_por_upstreams():
    rotas = [{"a": [10 + i, 500]} for i in range(6)]          # AS 500: 6 upstreams, 6 rotas
    rotas += [{"a": [7, 600]} for _ in range(40)]              # AS 600: 1 upstream, 40 rotas
    rotas += [{"a": [8, 700 + i]} for i in range(20)]          # 20 ASes com 1 upstream e 1 rota
    lista = _upstream_diversity(rotas, {}, "v4", top_n=2)
    asns = [r["asn"] for r in lista]
    assert 500 in asns and 600 in asns
    assert asns[0] == 500, "na ordem do corte principal (número de upstreams)"
