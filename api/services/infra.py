# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Infraestrutura física num raio em torno de um ponto: resumo das camadas estáticas do mapa (sem GeoJSON) e instalações do PeeringDB.

Fonte única da tool `infra_proximos` do MCP e da rota `GET /territorio/infra-proximos` (blocos "Infraestrutura física no raio" do Localizador e do município)."""
from __future__ import annotations

from typing import Optional

from core.geo import distancia_ao_geometria_km, haversine_km

# nome na consulta → (camada em maps/<camada>.geojson, rótulo). As quatro primeiras são leves; rodovias (~135 MB) só quando pedida (MCP).
CAMADAS_INFRA = {
    "cabos": ("submarine_cables", "Cabos submarinos (TeleGeography)"),
    "pontos_aterrissagem": ("submarine_landing_points", "Pontos de aterrissagem de cabos submarinos"),
    "enlaces": ("itu_transmission", "Enlaces terrestres de transmissão (ITU)"),
    "linhas_transmissao": ("power_transmission_lines", "Linhas de transmissão de energia"),
    "rodovias": ("ibge_rodovias", "Rodovias (IBGE)"),
}
PADRAO = ("cabos", "pontos_aterrissagem", "enlaces", "linhas_transmissao")
LEVES = frozenset(PADRAO)
# Fonte e ressalva de cada camada, para a tela citar sem repetir o texto de memória.
FONTES = {
    "cabos": "TeleGeography (Submarine Cable Map)",
    "pontos_aterrissagem": "TeleGeography (Submarine Cable Map)",
    "enlaces": "UIT (Transmission Maps)",
    "linhas_transmissao": "ONS/Aneel (SIGEL), rede básica",
}


def resumo_props(props: dict) -> dict:
    """Propriedades escalares curtas da feição (nome, dono, ano…), sem listas nem textos longos."""
    return {k: v for k, v in (props or {}).items() if isinstance(v, (str, int, float, bool)) and not (isinstance(v, str) and len(v) > 80)}


def resumo_infra(store, d: str, lat: float, lon: float, raio: float, escolhidas: list[str], limit: int) -> dict:
    """`{"camadas": {nome: {camada, total, itens[, por_status]}}, "indisponiveis": [...]}`. `itens`: as `limit` feições mais próximas, com
    `distancia_km` (menor distância do ponto à geometria; projeção local). `por_status`: contagem por `status` quando a camada o traz (ITU)."""

    def mede(f: dict) -> Optional[float]:
        dist = distancia_ao_geometria_km(f.get("geometry"), lat, lon)
        return dist if dist is not None and dist <= raio else None

    saida, indisponiveis = {}, []
    for nome in escolhidas:
        camada, rotulo = CAMADAS_INFRA[nome]
        achadas: list[tuple[float, dict]] = []
        if nome == "rodovias":
            gj = store.geo_map_filtrado(d, camada, lambda f: mede(f) is not None)
        else:
            gj = store.geo_map(d, camada)
        feicoes = (gj or {}).get("features") if gj is not None else None
        if feicoes is None:
            indisponiveis.append(nome)
            continue
        for f in feicoes:
            dist = mede(f)
            if dist is not None:
                achadas.append((dist, f))
        achadas.sort(key=lambda x: x[0])
        item = {"camada": rotulo, "total": len(achadas),
                "itens": [{"distancia_km": round(dist, 1), **resumo_props(f.get("properties"))} for dist, f in achadas[:limit]]}
        status: dict[str, int] = {}
        for _, f in achadas:
            s = (f.get("properties") or {}).get("status")
            if isinstance(s, str) and s:
                status[s] = status.get(s, 0) + 1
        if status:
            item["por_status"] = dict(sorted(status.items(), key=lambda kv: (-kv[1], kv[0])))
        saida[nome] = item
    return {"camadas": saida, "indisponiveis": indisponiveis}


def instalacoes_proximas(linhas: list[dict], lat: float, lon: float, raio: float, limit: int) -> dict:
    """Instalações do PeeringDB (collection `facilities`, só as com coordenada) a até `raio` km do ponto, em linha reta: contagem e as `limit` mais próximas."""
    achadas = []
    for r in linhas:
        if r.get("lat") is None or r.get("lon") is None:
            continue
        km = haversine_km(lat, lon, r["lat"], r["lon"])
        if km <= raio:
            achadas.append((km, r))
    achadas.sort(key=lambda x: x[0])
    return {"raio_km": raio, "total": len(achadas),
            "itens": [{"distancia_km": round(km, 1), "id": r.get("id"), "nome": r.get("nome"), "cidade": r.get("cidade"), "uf": r.get("uf")} for km, r in achadas[:limit]]}
