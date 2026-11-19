# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""infra_nearby: distância ponto–geometria e a tool sobre camadas fictícias."""
import asyncio
import json

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from core.geo import distancia_ao_geometria_km as dist

LAT, LON = -23.5, -46.6


def test_distancias_por_tipo_de_geometria():
    assert dist({"type": "Point", "coordinates": [LON, LAT]}, LAT, LON) == 0
    assert dist({"type": "LineString", "coordinates": [[-46.7, -23.6], [-46.5, -23.6]]}, LAT, LON) == pytest.approx(11.06, abs=0.05)
    assert dist({"type": "LineString", "coordinates": [[-46.0, -23.6], [-45.0, -23.6]]}, LAT, LON) == pytest.approx(
        ((0.6 * 111.32 * 0.9171) ** 2 + (0.1 * 110.57) ** 2) ** 0.5, abs=0.5)              # vai ao extremo mais próximo do segmento
    assert dist({"type": "MultiLineString", "coordinates": [[[0, 0], [1, 1]], [[-46.6, -23.4], [-46.6, -23.3]]]}, LAT, LON) == pytest.approx(11.06, abs=0.05)
    assert dist({"type": "MultiPoint", "coordinates": [[0, 0], [-46.6, -23.49]]}, LAT, LON) == pytest.approx(1.1, abs=0.05)
    assert dist({"type": "Polygon", "coordinates": [[[-46.7, -23.6], [-46.5, -23.6], [-46.5, -23.4], [-46.7, -23.4], [-46.7, -23.6]]]}, LAT, LON) == pytest.approx(10.21, abs=0.05)      # a borda oeste (0,1° de longitude) é a mais próxima
    assert dist({"type": "LineString", "coordinates": []}, LAT, LON) is None and dist(None, LAT, LON) is None and dist({"type": "X", "coordinates": [1]}, LAT, LON) is None


CAMADAS = {
    "submarine_cables": {"features": [
        {"properties": {"name": "Perto", "owners": "A", "lista": [1, 2]}, "geometry": {"type": "LineString", "coordinates": [[-46.7, -23.6], [-46.5, -23.6]]}},
        {"properties": {"name": "Longe"}, "geometry": {"type": "LineString", "coordinates": [[10, 10], [11, 11]]}}]},
    "submarine_landing_points": {"features": [{"properties": {"name": "Ponto"}, "geometry": {"type": "Point", "coordinates": [-46.6, -23.49]}}]},
    "itu_transmission": {"features": []},
}


class Loja:
    def resolve_date(self, d):
        return d or "2026-10-30"

    def geo_map(self, d, camada):
        return CAMADAS.get(camada)

    def geo_map_filtrado(self, d, camada, aceita):
        gj = {"features": [{"properties": {"ref": "BR-116"}, "geometry": {"type": "LineString", "coordinates": [[-46.6, -23.4], [-46.6, -23.3]]}}]}
        return {"features": [f for f in gj["features"] if aceita(f)]}


@pytest.fixture()
def srv(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import mcp_server.app as m
    monkeypatch.setattr(m, "_store", Loja())
    return m


def chamar(srv, args):
    out = asyncio.run(srv.mcp.call_tool("infra_proximos", args))
    return json.loads("".join(b.text for b in (out[0] if isinstance(out, tuple) else out)))


def test_resumo_por_camada_com_distancia_e_sem_geojson(srv):
    r = chamar(srv, {"lat": LAT, "lon": LON, "raio_km": 50})
    assert set(r["camadas"]) == {"cabos", "pontos_aterrissagem", "enlaces"} and r["indisponiveis"] == ["linhas_transmissao"]
    assert r["camadas"]["cabos"]["total"] == 1 and r["camadas"]["cabos"]["itens"] == [{"distancia_km": 11.1, "name": "Perto", "owners": "A"}]
    assert r["camadas"]["pontos_aterrissagem"]["itens"][0]["distancia_km"] == 1.1 and r["camadas"]["enlaces"]["total"] == 0
    assert "geometry" not in json.dumps(r) and "coordinates" not in json.dumps(r)


def test_raio_limite_e_rodovias_so_quando_pedida(srv):
    assert chamar(srv, {"lat": LAT, "lon": LON, "raio_km": 5, "camadas": ["cabos"]})["camadas"]["cabos"]["total"] == 0
    rod = chamar(srv, {"lat": LAT, "lon": LON, "raio_km": 50, "camadas": ["rodovias"]})["camadas"]["rodovias"]
    assert rod["total"] == 1 and rod["itens"][0]["ref"] == "BR-116" and rod["itens"][0]["distancia_km"] == 11.1
    assert "rodovias" not in chamar(srv, {"lat": LAT, "lon": LON})["camadas"]


def test_argumentos_invalidos(srv):
    for args, erro in (({"lat": 91, "lon": 0}, "fora do intervalo"), ({"lat": 0, "lon": 181}, "fora do intervalo"),
                       ({"lat": 0, "lon": 0, "camadas": ["esgotos"]}, "camadas inválidas")):
        with pytest.raises(ToolError, match=erro):
            chamar(srv, args)
