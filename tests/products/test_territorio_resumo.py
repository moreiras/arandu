# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — `GET /territorio/resumo` (PT-22, municipios 5.2): os agregados batem com a lista de municípios do mesmo snapshot."""


def test_resumo_bate_com_a_lista_de_municipios(api):
    r = api.get("/api/v1/territorio/resumo")
    assert r.status_code == 200, r.text
    j = r.json()
    todos = api.get("/api/v1/territorio/ranking", params={"campo": "acessos", "limit": 1}).json()
    longe = api.get("/api/v1/territorio/ranking", params={"campo": "acessos", "sem_ptt_proximo": "true", "limit": 1}).json()
    assert j["a_mais_de_100km"]["municipios"] == longe["total"]
    assert j["total"]["municipios"] >= todos["total"]
    for campo in ("municipios", "populacao_estimada", "domicilios_projetados", "acessos"):
        assert j["a_mais_de_100km"][campo] + j["ate_100km"][campo] + j["sem_distancia"][campo] == j["total"][campo], campo
    assert j["limites"] and j["formulas"] is not None and j["mes_referencia_sici"]


def test_resumo_por_uf_e_uf_desconhecida(api):
    uf = api.get("/api/v1/territorio/ranking", params={"campo": "acessos", "limit": 1}).json()["items"][0]["uf"]
    r = api.get("/api/v1/territorio/resumo", params={"uf": uf})
    assert r.status_code == 200 and r.json()["escopo"] == {"uf": uf}
    assert api.get("/api/v1/territorio/resumo", params={"uf": "ZZ"}).status_code == 404
