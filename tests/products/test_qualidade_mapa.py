# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — `GET /qualidade/mapa`: média das prestadoras por município e faixa em relação às referências da Anatel, sem nomear empresa."""
from api.services.qualidade import mapa_municipios

DOC = {"snapshot_date": "2026-11-05", "indicadores": [
    {"servico": "Banda Larga Fixa", "codigo": "IND4", "descricao": "x", "tipo": "Indicador IQS", "unidade": "%", "referencia_superior": "90%", "referencia_inferior": "60%"},
    {"servico": "Banda Larga Fixa", "codigo": "INF4-DL", "descricao": "y", "tipo": "Informativo", "unidade": "Mbps", "referencia_superior": None, "referencia_inferior": None}]}


def _it(prest, ind, res, med):
    return {"servico": "Banda Larga Fixa", "prestadora": prest, "indicador": ind, "mes": "2026-08", "resultado": res, "medidas": med}


def test_media_ponderada_faixas_e_sem_referencia():
    uf = {"SP": {"municipios": {
        "1": {"itens": [_it("A", "IND4", 95.0, 100), _it("B", "IND4", 55.0, 300)]},     # (95*100+55*300)/400 = 65 → entre
        "2": {"itens": [_it("A", "IND4", 95.0, 10)]},                                    # acima
        "3": {"itens": [_it("A", "IND4", 40.0, None)]},                                  # abaixo; sem medidas: média simples
        "4": {"itens": [_it("A", "INF4-DL", 100.0, 5)]}}}}                               # outro indicador: fora
    r = mapa_municipios(DOC, uf, "Banda Larga Fixa", "IND4")
    assert r["valores"] == {"1": 65.0, "2": 95.0, "3": 40.0} and r["prestadoras"]["1"] == 2
    assert r["faixas"] == {"1": 1, "2": 2, "3": 0}
    sem = mapa_municipios(DOC, uf, "Banda Larga Fixa", "INF4-DL")
    assert sem["faixas"] is None and sem["valores"] == {"4": 100.0}                       # sem as duas referências, não há faixa


def test_rota_mapa(api):
    resumo = api.get("/api/v1/qualidade/resumo").json()
    ind = next(i for i in resumo["indicadores"] if i["servico"] == "Banda Larga Fixa")
    r = api.get("/api/v1/qualidade/mapa", params={"servico": ind["servico"], "indicador": ind["codigo"]})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["limites"] and j["normalizacao"] and j["total"] == len(j["valores"])
    assert "prestadora" not in str(j["valores"]).lower()                                  # só números por município, sem empresa
    assert api.get("/api/v1/qualidade/mapa", params={"servico": "Banda Larga Fixa", "indicador": "XXX"}).status_code == 400
