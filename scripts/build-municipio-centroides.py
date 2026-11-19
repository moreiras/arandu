#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
"""
Gera frontend/public/municipios-centroides.json a partir da malha municipal do IBGE.

Roda UMA VEZ (e de novo só quando a divisão territorial mudar — criação ou fusão de
municípios, raro). O arquivo é pequeno (~200 KB) e vai versionado no repositório,
então o frontend não depende do IBGE em tempo de execução.

Formato: {"3550308": [lon, lat], ...} — coordenadas em GeoJSON (lon primeiro), com
4 casas decimais (~11 m, mais do que suficiente para posicionar uma bolha).

Por que centróides e não a malha inteira: o mapa da página do AS usa bolhas
proporcionais ao número de acessos. Um coroplético exigiria os 5.570 polígonos
(dezenas de MB) e ainda teria viés de área — município grande e vazio dominaria o
campo visual.

Uso:
    python3 scripts/build-municipio-centroides.py
"""
from __future__ import annotations

import gzip
import json
import sys
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

# Malha municipal de todo o país numa requisição. `qualidade=minima` já vem
# simplificada — irrelevante para centróide, mas baixa muito mais rápido.
IBGE_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
    "?formato=application/vnd.geo+json&intrarregiao=municipio&qualidade=minima"
)
OUT = Path(__file__).parent.parent / "frontend" / "public" / "municipios-centroides.json"
# Cópia lida pela API (perfil do município): a imagem da API não leva o frontend/. Um teste confere que são iguais.
OUT_API = Path(__file__).parent.parent / "config" / "municipios-centroides.json"


def centroid(geometry: dict) -> Optional[Tuple[float, float]]:
    """Centróide simples: média dos vértices do anel externo de maior área aparente.

    Não é o centro de massa exato do polígono — para posicionar uma bolha num mapa
    nacional a diferença é invisível, e evita depender de shapely.
    """
    gtype = geometry.get("type")
    rings: list[list] = []
    if gtype == "Polygon":
        rings = [geometry["coordinates"][0]]
    elif gtype == "MultiPolygon":
        rings = [poly[0] for poly in geometry["coordinates"]]
    else:
        return None
    best, best_n = None, -1
    for ring in rings:
        if len(ring) > best_n:
            best, best_n = ring, len(ring)
    if not best:
        return None
    lon = sum(p[0] for p in best) / len(best)
    lat = sum(p[1] for p in best) / len(best)
    return round(lon, 4), round(lat, 4)


def main() -> int:
    print(f"baixando malha municipal do IBGE...\n  {IBGE_URL}")
    req = urllib.request.Request(IBGE_URL, headers={"Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
    print(f"  {len(raw) / 1_048_576:.1f} MB")
    fc = json.loads(raw)

    out: dict[str, list[float]] = {}
    for feat in fc.get("features", []):
        props = feat.get("properties") or {}
        code = str(props.get("codarea") or props.get("id") or "").strip()
        if not code.isdigit() or len(code) != 7:
            continue
        c = centroid(feat.get("geometry") or {})
        if c:
            out[code] = [c[0], c[1]]

    if len(out) < 5000:
        print(f"ERRO: só {len(out)} municípios extraídos — esperado ~5.570.",
              file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    OUT_API.write_text(OUT.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"escrito {OUT} — {len(out)} municípios, "
          f"{OUT.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
