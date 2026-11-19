# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — rede no território: rota-resumo, includes, indicadores do mapa e coerência com os artefatos de origem."""


def test_resumo_traz_limites_cobertura_e_a_suposicao(api):
    r = api.get("/api/v1/territorio/rede")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["natureza"] == "estimado" and "igual em todos os municípios" in j["limites"]
    assert 0 <= j["ipv6"]["brasil"]["cobertura"] <= 100 and j["rov"]["brasil"]["usuarios"] >= j["rov"]["brasil"]["usuarios_com_medida"]


def test_municipio_e_uf_trazem_o_bloco_e_o_mapa_responde(api):
    mun = api.get("/api/v1/acessos/municipios").json()["items"][0]
    p = api.get(f"/api/v1/municipios/{mun['ibge']}", params={"include": "rede_territorio"}).json()
    rt = p["rede_territorio"]
    assert rt and rt["ipv6"]["acessos"] == mun["acessos"] and rt["limites"]
    uf = api.get("/api/v1/ufs/SP", params={"include": "rede_territorio"}).json()["rede_territorio"]
    assert uf["ipv6"]["acessos"] > 0 and "rov" in uf
    for ind in ("ipv6_estimado_pct", "transito_unico_pct"):
        m = api.get("/api/v1/territorio/mapa", params={"indicador": ind})
        assert m.status_code == 200, m.text
        assert m.json()["normalizacao"] and all(0 <= v <= 100 for v in m.json()["valores"].values())
