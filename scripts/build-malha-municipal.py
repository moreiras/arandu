#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Gera `frontend/public/malha-municipal.pmtiles`: malha municipal do IBGE simplificada, em tiles vetoriais, para mapas coropléticos.

Fonte: IBGE, Malhas Territoriais, Malha Municipal 2024 (`BR_Municipios_2024.zip`, shapefile em SIRGAS 2000). **Atribuição obrigatória: "Fonte: IBGE".**
Uso autorizado pelo mantenedor em 2026-11-11 (o texto de licença do IBGE não pôde ser lido por acesso automatizado; ver `pendencias` em
`catalog/sources/ibge_malha_municipal.yaml`).

O arquivo é do tipo PMTiles v3 (lido por `Range` no navegador, sem GeoJSON de dezenas de MB) com duas camadas, do zoom 0 ao 7:
  - `municipios`: `ibge` (7 dígitos), `nome`, `uf` (sigla);
  - `ufs`: `uf`, `nome` (união dos municípios já simplificados, então os limites coincidem).
A simplificação é topológica (`coverage_simplify`: limites compartilhados ficam iguais nos dois lados, sem frestas), com tolerância de 1 pixel do zoom.
As feições `4300001` e `4300002` (Lagoa dos Patos e Lagoa Mirim, que não são municípios) ficam de fora. Acima do zoom 7 o cliente repete o tile do zoom 7.

Dependências **só de build** (não rodam em produção): `pip install shapely pyshp mapbox-vector-tile pmtiles` (ver `requirements-build.txt`).

    python3 scripts/build-malha-municipal.py --zip BR_Municipios_2024.zip     # baixe o ZIP à mão do geoftp.ibge.gov.br (1 arquivo, ~200 MB)
    python3 scripts/build-malha-municipal.py --zip ... --out /tmp/malha.pmtiles --maxzoom 6
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import sys
import tempfile
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import structlog

log = structlog.get_logger(__name__)

ROOT = Path(__file__).resolve().parents[1]
SAIDA = ROOT / "frontend" / "public" / "malha-municipal.pmtiles"
META = ROOT / "frontend" / "public" / "malha-municipal.json"
URL_ORIGEM = "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2024/Brasil/BR_Municipios_2024.zip"
EXTENT = 4096
BUFFER_PX = 64                      # margem de recorte por tile, para a borda não aparecer
NAO_MUNICIPIOS = {"4300001", "4300002"}      # Lagoa dos Patos e Lagoa Mirim
R = 6378137.0                        # esfera do Web Mercator


def mercator(lon: float, lat: float) -> tuple[float, float]:
    return (R * math.radians(lon), R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def resolucao(z: int) -> float:
    """Metros por pixel (tiles de 256) no zoom `z`."""
    return 2 * math.pi * R / (256 * 2 ** z)


def limites_do_tile(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    lado = 2 * math.pi * R / 2 ** z
    minx = -math.pi * R + x * lado
    maxy = math.pi * R - y * lado
    return (minx, maxy - lado, minx + lado, maxy)


def tiles_da_caixa(caixa: tuple[float, float, float, float], z: int) -> Iterable[tuple[int, int]]:
    lado = 2 * math.pi * R / 2 ** z
    n = 2 ** z
    x0 = max(0, int((caixa[0] + math.pi * R) // lado))
    x1 = min(n - 1, int((caixa[2] + math.pi * R) // lado))
    y0 = max(0, int((math.pi * R - caixa[3]) // lado))
    y1 = min(n - 1, int((math.pi * R - caixa[1]) // lado))
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            yield x, y


def ler_malha(zip_path: Path, pasta: Path) -> list[dict[str, Any]]:
    """Municípios do shapefile: `{ibge, nome, uf, nome_uf, geom}` com a geometria já em Web Mercator."""
    import shapefile
    import shapely
    from shapely.geometry import shape

    with zipfile.ZipFile(zip_path) as z:
        z.extractall(pasta)
    shp = next(pasta.glob("*.shp"))
    leitor = shapefile.Reader(str(shp), encoding="utf-8")
    campos = [c[0] for c in leitor.fields[1:]]
    saida = []
    for sr in leitor.iterShapeRecords():
        r = dict(zip(campos, sr.record))
        if str(r["CD_MUN"]) in NAO_MUNICIPIOS:
            continue
        g = shape(sr.shape.__geo_interface__)
        g = shapely.transform(g, lambda a: _para_mercator(a))
        saida.append({"ibge": str(r["CD_MUN"]), "nome": r["NM_MUN"], "uf": r["SIGLA_UF"], "nome_uf": r["NM_UF"], "geom": g})
    log.info("malha_lida", municipios=len(saida))
    return saida


def _para_mercator(a):
    import numpy as np
    lon, lat = a[:, 0], a[:, 1]
    return np.column_stack([R * np.radians(lon), R * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))])


def simplificar(feicoes: list[dict[str, Any]], z: int) -> list[dict[str, Any]]:
    """Cópia das feições com a geometria simplificada para o zoom `z` (topológica, tolerância de 1 pixel)."""
    import shapely

    geoms = shapely.coverage_simplify([f["geom"] for f in feicoes], resolucao(z))
    return [{**f, "geom": g} for f, g in zip(feicoes, geoms) if not g.is_empty]


def camada_ufs(feicoes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import shapely

    por_uf: dict[str, list[Any]] = defaultdict(list)
    nomes: dict[str, str] = {}
    for f in feicoes:
        por_uf[f["uf"]].append(f["geom"])
        nomes[f["uf"]] = f["nome_uf"]
    return [{"uf": uf, "nome": nomes[uf], "geom": shapely.union_all(g)} for uf, g in sorted(por_uf.items())]


def gerar_tiles(feicoes: list[dict[str, Any]], maxzoom: int) -> Iterable[tuple[int, int, int, bytes]]:
    """(z, x, y, MVT sem compressão) de cada tile não vazio, do zoom 0 ao `maxzoom`."""
    import mapbox_vector_tile
    import shapely

    for z in range(maxzoom + 1):
        mun = simplificar(feicoes, z)
        ufs = camada_ufs(mun)
        indice: dict[tuple[int, int], dict[str, list[dict[str, Any]]]] = defaultdict(lambda: {"municipios": [], "ufs": []})
        for nome, lista in (("municipios", mun), ("ufs", ufs)):
            for f in lista:
                for xy in tiles_da_caixa(f["geom"].bounds, z):
                    indice[xy][nome].append(f)
        folga = BUFFER_PX * resolucao(z) * 256 / EXTENT
        for (x, y), camadas in sorted(indice.items()):
            minx, miny, maxx, maxy = limites_do_tile(z, x, y)
            partes = []
            for nome, lista in camadas.items():
                itens = []
                for f in lista:
                    g = shapely.clip_by_rect(f["geom"], minx - folga, miny - folga, maxx + folga, maxy + folga)
                    if g.is_empty or g.geom_type in ("Point", "MultiPoint", "LineString", "MultiLineString", "GeometryCollection") and not g.area:
                        continue
                    props = {"ibge": f["ibge"], "nome": f["nome"], "uf": f["uf"]} if nome == "municipios" else {"uf": f["uf"], "nome": f["nome"]}
                    itens.append({"geometry": g, "properties": props})
                if itens:
                    partes.append({"name": nome, "features": itens})
            if not partes:
                continue
            mvt = mapbox_vector_tile.encode(partes, default_options={"quantize_bounds": (minx, miny, maxx, maxy), "extents": EXTENT, "y_coord_down": False})
            yield z, x, y, mvt
        log.info("zoom_gerado", z=z, tiles=len(indice))


def escrever_pmtiles(saida: Path, tiles: Iterable[tuple[int, int, int, bytes]], maxzoom: int, sha_origem: str) -> dict[str, Any]:
    from pmtiles.tile import Compression, TileType, zxy_to_tileid
    from pmtiles.writer import Writer

    ordenados = sorted(((zxy_to_tileid(z, x, y), z, x, y, mvt) for z, x, y, mvt in tiles), key=lambda t: t[0])
    saida.parent.mkdir(parents=True, exist_ok=True)
    caixa = {"w": 180.0, "s": 90.0, "e": -180.0, "n": -90.0}
    with saida.open("wb") as f:
        w = Writer(f)
        for tid, z, x, y, mvt in ordenados:
            w.write_tile(tid, gzip.compress(mvt, 9, mtime=0))
            if z == maxzoom:
                minx, miny, maxx, maxy = limites_do_tile(z, x, y)
                lo0, la0 = math.degrees(minx / R), math.degrees(2 * math.atan(math.exp(miny / R)) - math.pi / 2)
                lo1, la1 = math.degrees(maxx / R), math.degrees(2 * math.atan(math.exp(maxy / R)) - math.pi / 2)
                caixa = {"w": min(caixa["w"], lo0), "s": min(caixa["s"], la0), "e": max(caixa["e"], lo1), "n": max(caixa["n"], la1)}
        cabecalho = {
            "tile_type": TileType.MVT, "tile_compression": Compression.GZIP, "min_zoom": 0, "max_zoom": maxzoom,
            "min_lon_e7": int(caixa["w"] * 1e7), "min_lat_e7": int(caixa["s"] * 1e7), "max_lon_e7": int(caixa["e"] * 1e7), "max_lat_e7": int(caixa["n"] * 1e7),
            "center_zoom": 3, "center_lon_e7": int(-52 * 1e7), "center_lat_e7": int(-14 * 1e7),
        }
        metadata = {
            "name": "Malha municipal do IBGE (simplificada)", "format": "pbf", "version": "1",
            "attribution": "Fonte: IBGE (Malha Municipal 2024)", "description": "Municípios e UFs do Brasil, simplificados para mapas temáticos",
            "vector_layers": [
                {"id": "municipios", "fields": {"ibge": "String", "nome": "String", "uf": "String"}, "minzoom": 0, "maxzoom": maxzoom},
                {"id": "ufs", "fields": {"uf": "String", "nome": "String"}, "minzoom": 0, "maxzoom": maxzoom},
            ],
            "origem_sha256": sha_origem,
        }
        w.finalize(cabecalho, metadata)
    return {"tiles": len(ordenados), "bytes": saida.stat().st_size, "bounds": caixa}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--zip", type=Path, required=True, help="BR_Municipios_2024.zip do geoftp.ibge.gov.br")
    ap.add_argument("--out", type=Path, default=SAIDA)
    ap.add_argument("--maxzoom", type=int, default=7)
    a = ap.parse_args(argv)
    sha = hashlib.sha256(a.zip.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory() as tmp:
        feicoes = ler_malha(a.zip, Path(tmp))
        r = escrever_pmtiles(a.out, gerar_tiles(feicoes, a.maxzoom), a.maxzoom, sha)
    meta = {"fonte": "IBGE, Malha Municipal 2024", "atribuicao": "Fonte: IBGE", "url": URL_ORIGEM, "sha256_origem": sha, "municipios": len(feicoes),
            "zoom_maximo": a.maxzoom, "camadas": ["municipios", "ufs"], "gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%d"), **r}
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8") if a.out == SAIDA else None
    log.info("malha_pronta", **{k: v for k, v in meta.items() if k not in ("url", "sha256_origem")})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
