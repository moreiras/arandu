# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Funções geográficas utilitárias — usadas pela Store, pelo motor de query e pelas regras de alerta.
"""
from math import asin, cos, radians, sin, sqrt


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em km entre dois pontos."""
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(a))


def distancia_ao_geometria_km(geom: dict, lat: float, lon: float) -> float | None:
    """Menor distância (km) de um ponto a uma geometria GeoJSON (Point, LineString, MultiLineString, Polygon, MultiPolygon, MultiPoint).

    Projeção equirretangular local em torno do ponto: erro desprezível nas dezenas a poucas centenas de km que as consultas de proximidade
    usam. Polígono conta pelo contorno (não detecta o ponto dentro). Geometria vazia ou desconhecida → None.
    """
    import math

    kx = 111.32 * math.cos(math.radians(lat))      # km por grau de longitude nesta latitude
    ky = 110.57                                      # km por grau de latitude

    def xy(c) -> tuple[float, float]:
        return (c[0] - lon) * kx, (c[1] - lat) * ky

    def ponto_segmento(a, b) -> float:
        (ax, ay), (bx, by) = xy(a), xy(b)
        dx, dy = bx - ax, by - ay
        t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
        return math.hypot(ax + t * dx, ay + t * dy)

    def linha(cs) -> float | None:
        if not cs:
            return None
        if len(cs) == 1:
            return math.hypot(*xy(cs[0]))
        return min(ponto_segmento(cs[i], cs[i + 1]) for i in range(len(cs) - 1))

    tipo, cs = (geom or {}).get("type"), (geom or {}).get("coordinates")
    if not cs:
        return None
    if tipo == "Point":
        return math.hypot(*xy(cs))
    if tipo == "MultiPoint":
        return min(math.hypot(*xy(c)) for c in cs)
    if tipo == "LineString":
        return linha(cs)
    if tipo in ("MultiLineString", "Polygon"):
        d = [x for x in (linha(parte) for parte in cs) if x is not None]
        return min(d) if d else None
    if tipo == "MultiPolygon":
        d = [x for x in (linha(anel) for poligono in cs for anel in poligono) if x is not None]
        return min(d) if d else None
    return None
