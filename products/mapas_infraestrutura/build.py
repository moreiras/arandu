# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Camadas de fundo de infraestrutura física: enlaces ITU, cabos submarinos, linhas de
transmissão e rodovias. Contexto geográfico puro, sem cruzamento com ASN/CNPJ."""
from __future__ import annotations

import json
from pathlib import Path

from core.common import normalized_path, published_path
from core.jsonio import carregar_json_gz


def _catmull_rom_smooth(points: list[list[float]], segments_per_span: int = 8) -> list[list[float]]:
    """Suaviza uma polilinha por spline Catmull-Rom, sem libs externas.

    Os cabos submarinos do TeleGeography vêm como segmentos retos entre poucos
    vértices — visualmente "quebrados" nas junções. A spline passa exatamente
    pelos vértices originais (não é uma aproximação, como Douglas-Peucker seria
    ao contrário) e insere pontos intermediários entre eles, produzindo uma
    curva contínua sem ângulo visível nas junções (pedido do usuário).
    Não é usada nos enlaces terrestres da ITU (que devem seguir traçado real,
    não uma curva estilizada).
    """
    if len(points) < 3:
        return points

    padded = [points[0], *points, points[-1]]
    result: list[list[float]] = [points[0]]
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
        for step in range(1, segments_per_span + 1):
            t = step / segments_per_span
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            result.append([x, y])
    return result


def _smooth_multiline(geometry: dict) -> dict:
    """Aplica _catmull_rom_smooth a cada linha de um MultiLineString/LineString."""
    if geometry.get("type") == "MultiLineString":
        return {
            "type": "MultiLineString",
            "coordinates": [_catmull_rom_smooth(line) for line in geometry["coordinates"]],
        }
    if geometry.get("type") == "LineString":
        return {"type": "LineString", "coordinates": _catmull_rom_smooth(geometry["coordinates"])}
    return geometry


def publicar_infra_maps(base: Path, date_str: str, log) -> dict:
    """
    Publica as camadas de fundo de infraestrutura física: enlaces
    terrestres da ITU (`itu_transmission`), cabos submarinos + pontos de aterrissagem da
    TeleGeography (`telegeography_cables`), linhas de transmissão de alta tensão do SIGEL/ANEEL
    (`aneel_sigel_transmission`) e a malha rodoviária nacional do IBGE/BC250 (`anatel_stfc`). Opcional; não
    falha se `itu_transmission`, `telegeography_cables`, `aneel_sigel_transmission` e `ibge_bc250_rodovias` não rodaram.

    Diferente de SCM/SMP/SICI, não há cruzamento com ASN/CNPJ — é dado de
    contexto geográfico puro. ITU/TeleGeography/SIGEL entram como fundo nos 7
    mapas e como camada interativa em /mapa; rodovias (124 mil feições, bem
    mais pesado) só entra como camada opcional em /mapa, nunca como fundo
    sempre-carregado.

    Saídas:
      published/{date}/maps/itu_transmission.geojson         — enlaces (LineString)
      published/{date}/maps/submarine_cables.geojson         — cabos (MultiLineString)
      published/{date}/maps/submarine_landing_points.geojson — pontos de aterrissagem
      published/{date}/maps/power_transmission_lines.geojson — linhas de alta tensão (LineString/MultiLineString)
      published/{date}/maps/ibge_rodovias.geojson             — malha rodoviária (LineString/MultiLineString)
    """
    norm_dir = normalized_path(base, date_str, "summary")
    maps_dir = published_path(base, date_str, "maps")

    counts = {
        "itu_links": 0,
        "submarine_cables": 0,
        "submarine_landing_points": 0,
        "power_transmission_lines": 0,
        "ibge_rodovias": 0,
    }

    itu_data = carregar_json_gz(norm_dir / "itu_transmission.json.gz")
    if itu_data and itu_data.get("features"):
        maps_dir.mkdir(parents=True, exist_ok=True)
        geojson = {
            "type": "FeatureCollection",
            "snapshot_date": date_str,
            "source": itu_data.get("source", ""),
            "features": itu_data["features"],
        }
        (maps_dir / "itu_transmission.geojson").write_text(
            json.dumps(geojson, ensure_ascii=False), encoding="utf-8"
        )
        counts["itu_links"] = len(itu_data["features"])
        log.info("itu_transmission.geojson written", features=counts["itu_links"])
    else:
        log.info("itu_transmission not found, skipping ITU background layer")

    tg_data = carregar_json_gz(norm_dir / "telegeography_cables.json.gz")
    if tg_data and tg_data.get("cables"):
        maps_dir.mkdir(parents=True, exist_ok=True)

        cable_features = [
            {
                "type": "Feature",
                "geometry": _smooth_multiline(c["geometry"]),
                "properties": {
                    "id": c.get("id", ""),
                    "name": c.get("name", ""),
                    "color": c.get("color", ""),
                    "length": c.get("length", ""),
                    "owners": c.get("owners", ""),
                    "rfs_year": c.get("rfs_year"),
                    "is_planned": c.get("is_planned"),
                    "url": c.get("url", ""),
                    # Usado no frontend para colorir diferente os cabos que tocam o
                    # Brasil (azul claro) dos demais (amarelo claro) — mapTheme.ts.
                    "touches_brazil": "Brazil" in (c.get("landing_countries") or []),
                },
            }
            for c in tg_data["cables"] if c.get("geometry")
        ]
        cables_geojson = {
            "type": "FeatureCollection",
            "snapshot_date": date_str,
            "source": tg_data.get("source", ""),
            "attribution": "© TeleGeography, submarinecablemap.com — CC BY-SA 4.0",
            "features": cable_features,
        }
        (maps_dir / "submarine_cables.geojson").write_text(
            json.dumps(cables_geojson, ensure_ascii=False), encoding="utf-8"
        )
        counts["submarine_cables"] = len(cable_features)
        log.info("submarine_cables.geojson written", features=counts["submarine_cables"])

        lp_features = [
            {
                "type": "Feature",
                "geometry": lp["geometry"],
                "properties": {
                    "id": lp.get("id", ""),
                    "name": lp.get("name", ""),
                    "is_tbd": lp.get("is_tbd", False),
                },
            }
            for lp in tg_data.get("landing_points", []) if lp.get("geometry")
        ]
        lp_geojson = {
            "type": "FeatureCollection",
            "snapshot_date": date_str,
            "source": tg_data.get("source", ""),
            "attribution": "© TeleGeography, submarinecablemap.com — CC BY-SA 4.0",
            "features": lp_features,
        }
        (maps_dir / "submarine_landing_points.geojson").write_text(
            json.dumps(lp_geojson, ensure_ascii=False), encoding="utf-8"
        )
        counts["submarine_landing_points"] = len(lp_features)
        log.info("submarine_landing_points.geojson written",
                  features=counts["submarine_landing_points"])
    else:
        log.info("telegeography_cables not found, skipping submarine background layer")

    aneel_data = carregar_json_gz(norm_dir / "aneel_transmission.json.gz")
    if aneel_data and aneel_data.get("features"):
        maps_dir.mkdir(parents=True, exist_ok=True)
        power_geojson = {
            "type": "FeatureCollection",
            "snapshot_date": date_str,
            "source": aneel_data.get("source", ""),
            "features": aneel_data["features"],
        }
        (maps_dir / "power_transmission_lines.geojson").write_text(
            json.dumps(power_geojson, ensure_ascii=False), encoding="utf-8"
        )
        counts["power_transmission_lines"] = len(aneel_data["features"])
        log.info("power_transmission_lines.geojson written",
                  features=counts["power_transmission_lines"])
    else:
        log.info("aneel_transmission not found, skipping power line background layer")

    rodovias_data = carregar_json_gz(norm_dir / "ibge_rodovias.json.gz")
    if rodovias_data and rodovias_data.get("features"):
        maps_dir.mkdir(parents=True, exist_ok=True)
        rodovias_geojson = {
            "type": "FeatureCollection",
            "snapshot_date": date_str,
            "source": rodovias_data.get("source", ""),
            "features": rodovias_data["features"],
        }
        (maps_dir / "ibge_rodovias.geojson").write_text(
            json.dumps(rodovias_geojson, ensure_ascii=False), encoding="utf-8"
        )
        counts["ibge_rodovias"] = len(rodovias_data["features"])
        log.info("ibge_rodovias.geojson written", features=counts["ibge_rodovias"])
    else:
        log.info("ibge_rodovias not found, skipping road network layer")

    return counts
