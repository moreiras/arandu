# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PT-25 (localizador 5.5, município 5.4): resumo da infraestrutura física e das instalações num raio, fonte única da rota REST e da tool do MCP."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import territorio
from api.services.infra import PADRAO, instalacoes_proximas, resumo_infra

LAT, LON = -7.2258, -39.3252                         # Juazeiro do Norte/CE


def _linha(coords, **props):
    return {"properties": props, "geometry": {"type": "LineString", "coordinates": coords}}


CAMADAS = {
    "itu_transmission": {"features": [
        _linha([[LON - 0.01, LAT], [LON + 0.01, LAT]], name="perto", status="Fibre Operational"),
        _linha([[LON, LAT + 0.5], [LON + 0.1, LAT + 0.5]], name="medio", status="Fibre Operational"),
        _linha([[LON, LAT + 0.6], [LON + 0.1, LAT + 0.6]], name="plan", status="Fibre Planned"),
        _linha([[10, 10], [11, 11]], name="longe", status="Fibre Operational"),
    ]},
    "power_transmission_lines": {"features": [_linha([[LON, LAT + 0.2], [LON + 0.1, LAT + 0.2]], name="LT 1")]},
    "submarine_cables": {"features": []},
    "submarine_landing_points": {"features": []},
}


class Loja:
    def resolve_date(self, d):
        return d or "2026-11-22"

    def geo_map(self, d, camada):
        return CAMADAS.get(camada)

    def query_table(self, d, colecao):
        assert colecao == "facilities"
        return [{"id": 1, "nome": "Perto", "cidade": "Fortaleza", "uf": "CE", "lat": LAT + 0.3, "lon": LON},
                {"id": 2, "nome": "Sem coordenada", "lat": None, "lon": None},
                {"id": 3, "nome": "Longe", "cidade": "São Paulo", "uf": "SP", "lat": -23.5, "lon": -46.6}]


def test_resumo_conta_no_raio_ordena_por_distancia_e_agrupa_por_status():
    r = resumo_infra(Loja(), "2026-11-22", LAT, LON, 80.0, list(PADRAO), 2)
    enl = r["camadas"]["enlaces"]
    assert enl["total"] == 3 and [i["name"] for i in enl["itens"]] == ["perto", "medio"]        # limite 2; 'longe' fora do raio
    assert enl["itens"][0]["distancia_km"] < 1.5
    assert enl["por_status"] == {"Fibre Operational": 2, "Fibre Planned": 1}
    assert r["camadas"]["linhas_transmissao"]["total"] == 1 and "por_status" not in r["camadas"]["linhas_transmissao"]
    assert r["camadas"]["cabos"]["total"] == 0 and r["camadas"]["cabos"]["itens"] == []         # zero é zero, não ausência
    assert r["indisponiveis"] == []


def test_camada_sem_arquivo_fica_indisponivel_e_nao_vira_zero():
    class Sem(Loja):
        def geo_map(self, d, camada):
            return None if camada == "submarine_cables" else super().geo_map(d, camada)
    r = resumo_infra(Sem(), "2026-11-22", LAT, LON, 80.0, list(PADRAO), 3)
    assert r["indisponiveis"] == ["cabos"] and "cabos" not in r["camadas"]


def test_instalacoes_so_com_coordenada_dentro_do_raio():
    r = instalacoes_proximas(Loja().query_table("d", "facilities"), LAT, LON, 150.0, 5)
    assert r["total"] == 1 and r["itens"][0]["nome"] == "Perto" and 30 < r["itens"][0]["distancia_km"] < 40
    assert instalacoes_proximas(Loja().query_table("d", "facilities"), LAT, LON, 10.0, 5) == {"raio_km": 10.0, "total": 0, "itens": []}


@pytest.fixture()
def cliente():
    app = FastAPI()
    app.state.store = Loja()
    app.include_router(territorio.router)
    return TestClient(app)


def test_rota_devolve_fonte_instalacoes_e_valida_parametros(cliente):
    r = cliente.get("/territorio/infra-proximos", params={"lat": LAT, "lon": LON, "raio_km": 80})
    assert r.status_code == 200
    j = r.json()
    assert j["snapshot_date"] == "2026-11-22" and j["raio_km"] == 80
    assert j["camadas"]["enlaces"]["fonte"].startswith("UIT") and j["camadas"]["enlaces"]["total"] == 3
    assert j["instalacoes"]["total"] == 1 and j["instalacoes"]["fonte"].startswith("PeeringDB")
    assert "rodovias" not in j["camadas"] and "coordinates" not in r.text                    # rodovias (arquivo grande) e geometria não saem
    assert cliente.get("/territorio/infra-proximos", params={"lat": 95, "lon": 0}).status_code == 422
    assert cliente.get("/territorio/infra-proximos", params={"lat": 0, "lon": 0, "raio_km": 900}).status_code == 422
    assert cliente.get("/territorio/infra-proximos").status_code == 422
