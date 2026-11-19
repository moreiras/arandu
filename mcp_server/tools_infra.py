# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Infraestrutura física perto de um ponto: `infra_nearby`, um resumo das camadas estáticas do mapa, sem GeoJSON."""
from __future__ import annotations

from typing import Optional

from core.geo import distancia_ao_geometria_km
from mcp_server.contexto import _resolve, _store, mcp

# nome na tool → (camada em maps/<camada>.geojson, rótulo). As quatro primeiras são leves; rodovias (~135 MB) só quando pedida.
CAMADAS_INFRA = {
    "cabos": ("submarine_cables", "Cabos submarinos (TeleGeography)"),
    "pontos_aterrissagem": ("submarine_landing_points", "Pontos de aterrissagem de cabos submarinos"),
    "enlaces": ("itu_transmission", "Enlaces terrestres de transmissão (ITU)"),
    "linhas_transmissao": ("power_transmission_lines", "Linhas de transmissão de energia"),
    "rodovias": ("ibge_rodovias", "Rodovias (IBGE)"),
}
PADRAO = ("cabos", "pontos_aterrissagem", "enlaces", "linhas_transmissao")


def _resumo_props(props: dict) -> dict:
    """Propriedades escalares curtas da feição (nome, dono, ano…), sem listas nem textos longos."""
    return {k: v for k, v in (props or {}).items() if isinstance(v, (str, int, float, bool)) and not (isinstance(v, str) and len(v) > 80)}


@mcp.tool()
def infra_nearby(
    lat: float,
    lon: float,
    raio_km: float = 50.0,
    camadas: Optional[list[str]] = None,
    limit: int = 10,
    date: Optional[str] = None,
) -> dict:
    """Infraestrutura física num raio em torno de um ponto: cabos submarinos, pontos de aterrissagem, enlaces ITU, linhas de transmissão de energia e rodovias.

    Devolve, por camada, quantas feições passam a até `raio_km` e as `limit` mais próximas com a distância em km (menor distância do ponto
    à geometria; projeção local, adequada a dezenas ou poucas centenas de km) e propriedades curtas. SEM GeoJSON: para desenhar use
    `map_*`/a interface. Para coordenadas de uma cidade use `resolve_place`; de um PTT, `geo_coords`.
    Padrão: cabos, pontos_aterrissagem, enlaces e linhas_transmissao. `rodovias` (~135 MB) só se pedida em `camadas` — leva uns 15 s (lê o arquivo inteiro, um de cada vez).

    Args:
        lat: Latitude em graus decimais (-90..90).
        lon: Longitude em graus decimais (-180..180).
        raio_km: Raio de busca em km (1..500).
        camadas: Subconjunto de cabos | pontos_aterrissagem | enlaces | linhas_transmissao | rodovias. Omita para as quatro leves.
        limit: Quantas feições listar por camada (1..50).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("lat/lon fora do intervalo válido.")
    raio = max(1.0, min(raio_km, 500.0))
    limit = max(1, min(limit, 50))
    escolhidas = list(dict.fromkeys(camadas)) if camadas else list(PADRAO)
    invalidas = [c for c in escolhidas if c not in CAMADAS_INFRA]
    if invalidas:
        raise ValueError(f"camadas inválidas: {invalidas}; válidas: {', '.join(CAMADAS_INFRA)}")
    d = _resolve(date)

    def mede(f: dict) -> Optional[float]:
        dist = distancia_ao_geometria_km(f.get("geometry"), lat, lon)
        return dist if dist is not None and dist <= raio else None

    saida, indisponiveis = {}, []
    for nome in escolhidas:
        camada, rotulo = CAMADAS_INFRA[nome]
        achadas: list[tuple[float, dict]] = []
        if nome == "rodovias":
            gj = _store.geo_map_filtrado(d, camada, lambda f: mede(f) is not None)
            feicoes = (gj or {}).get("features") if gj is not None else None
        else:
            gj = _store.geo_map(d, camada)
            feicoes = (gj or {}).get("features") if gj is not None else None
        if feicoes is None:
            indisponiveis.append(nome)
            continue
        for f in feicoes:
            dist = mede(f)
            if dist is not None:
                achadas.append((dist, f))
        achadas.sort(key=lambda x: x[0])
        saida[nome] = {"camada": rotulo, "total": len(achadas),
                       "itens": [{"distancia_km": round(dist, 1), **_resumo_props(f.get("properties"))} for dist, f in achadas[:limit]]}
    return {"snapshot_date": d, "ponto": {"lat": lat, "lon": lon}, "raio_km": raio, "camadas": saida, "indisponiveis": indisponiveis}
