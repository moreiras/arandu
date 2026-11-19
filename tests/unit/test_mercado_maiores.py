# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`maiores`: posição mês a mês entre todos os CNPJs e treemap por empresa-ou-grupo."""
from api.services.sici_indicadores import maiores

DADOS = {
    "serie_por_cnpj": {
        "A": [["2026-01", 100, 0, 0], ["2026-02", 100, 0, 0]],
        "B": [["2026-01", 90, 0, 0], ["2026-02", 120, 0, 0]],        # B ultrapassa A
        "C": [["2026-01", 50, 0, 0], ["2026-02", 60, 0, 0]],
        "D": [["2026-01", 10, 0, 0], ["2026-02", 70, 0, 0]],         # D sobe para 3º
    },
    "cnpjs": {"A": {"empresa": "Alfa", "acessos": 100}, "B": {"empresa": "Beta", "acessos": 120}, "C": {"empresa": "Gama", "acessos": 60}, "D": {"empresa": "Delta", "acessos": 70}},
}
GRUPOS = [{"grupo_id": "grp_1", "tamanho": 2, "cnpjs": [{"cnpj": "C"}, {"cnpj": "D"}]}, {"grupo_id": "grp_x", "tamanho": 1, "cnpjs": [{"cnpj": "A"}]}]


def test_posicao_mes_a_mes_entre_todos_os_cnpjs():
    r = maiores(DADOS, GRUPOS, n_ops=2, meses=12)
    assert r["meses"] == ["2026-01", "2026-02"] and r["mes_referencia"] == "2026-02"
    por = {o["cnpj"]: o for o in r["operadoras"]}
    assert list(por) == ["B", "A"]                                   # as 2 maiores de hoje
    assert por["B"]["posicao"] == [2, 1] and por["A"]["posicao"] == [1, 2]


def test_treemap_junta_o_grupo_e_nao_o_individual():
    r = maiores(DADOS, GRUPOS, n_unidades=2)
    u = {x["id"]: x for x in r["unidades"]}
    assert u["grp_1"]["acessos"] == 130 and u["grp_1"]["grupo"] and u["grp_1"]["cnpjs"] == 2 and u["grp_1"]["nome"] == "Delta"   # nome = a maior do grupo
    assert r["total_acessos"] == 350 and r["demais"]["unidades"] == 1 and r["demais"]["acessos"] == 100
    assert "inferido" in r["natureza"]
