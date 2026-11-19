# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — `GET /territorio/municipio/{ibge}/semelhantes`: município do mesmo porte e a posição entre eles."""


def _um_ibge(api):
    linhas = api.get("/api/v1/territorio/ranking", params={"campo": "domicilios_projetados", "limit": 50}).json()["items"]
    return next(r["ibge"] for r in linhas if r.get("domicilios_projetados"))


def test_semelhantes_sao_do_mesmo_porte_e_posicao_e_coerente(api):
    ibge = _um_ibge(api)
    r = api.get(f"/api/v1/territorio/municipio/{ibge}/semelhantes", params={"limit": 12})
    assert r.status_code == 200, r.text
    j = r.json()
    d0 = j["municipio"]["domicilios"]
    assert j["municipio"]["ibge"] == ibge and ibge not in [x["ibge"] for x in j["items"]]
    assert all(d0 / 2 <= x["domicilios"] <= d0 * 2 for x in j["items"])                       # a regra declarada em `criterio`
    assert j["criterio"] and j["limites"] and j["total_do_porte"] >= len(j["items"]) + 1
    p = j["posicao"]["penetracao"]
    if p:
        assert 1 <= p["posicao"] <= p["de"] <= j["total_do_porte"]


def test_semelhantes_municipio_desconhecido_e_404_e_opcional_vira_204(api):
    assert api.get("/api/v1/territorio/municipio/0000000/semelhantes").status_code == 404
    assert api.get("/api/v1/territorio/municipio/0000000/semelhantes", params={"opcional": 1}).status_code == 204


def test_ranking_aceita_fibra(api):
    r = api.get("/api/v1/territorio/ranking", params={"campo": "fibra_pct", "limit": 5})
    assert r.status_code == 200, r.text
    vals = [x["fibra_pct"] for x in r.json()["items"]]
    assert vals == sorted(vals, reverse=True)
