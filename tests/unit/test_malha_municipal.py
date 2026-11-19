# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Malha municipal: o artefato commitado (T3) e o script que o gera (T1, com uma malha sintética de três quadrados).

O artefato é conferido sem bibliotecas de geometria (cabeçalho PMTiles, tamanho, atribuição ao IBGE); o build só roda onde há `shapely`, `pyshp`,
`mapbox-vector-tile` e `pmtiles` (dependências de build, `requirements-build.txt`), e é pulado onde não há."""
import gzip
import importlib.util
import json
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PMTILES = ROOT / "frontend" / "public" / "malha-municipal.pmtiles"
META = ROOT / "frontend" / "public" / "malha-municipal.json"


def test_artefato_e_um_pmtiles_v3_de_mvt_com_gzip_e_tamanho_contido():
    b = PMTILES.read_bytes()
    assert b[:7] == b"PMTiles" and b[7] == 3
    tile_compression, tile_type, min_zoom, max_zoom = b[98], b[99], b[100], b[101]
    assert (tile_compression, tile_type, min_zoom, max_zoom) == (2, 1, 0, 7)          # gzip, MVT, zoom 0..7
    assert len(b) <= 4 * 1024 * 1024, f"{len(b) / 1e6:.1f} MB: acima do teto de 4 MB (revise a simplificação)"


def test_metadados_citam_o_ibge_e_a_origem():
    m = json.loads(META.read_text(encoding="utf-8"))
    assert m["atribuicao"] == "Fonte: IBGE" and m["municipios"] == 5571 and m["camadas"] == ["municipios", "ufs"]
    assert len(m["sha256_origem"]) == 64 and m["url"].startswith("https://geoftp.ibge.gov.br/")
    assert m["bytes"] == PMTILES.stat().st_size
    cab = PMTILES.read_bytes()
    offset, length = struct.unpack("<QQ", cab[24:40])                    # metadata JSON do PMTiles (gzip)
    meta = json.loads(gzip.decompress(cab[offset:offset + length]))
    assert "IBGE" in meta["attribution"] and {c["id"] for c in meta["vector_layers"]} == {"municipios", "ufs"}


def test_fonte_do_catalogo_aponta_para_o_arquivo_e_cita_o_ibge():
    import yaml
    s = yaml.safe_load((ROOT / "catalog" / "sources" / "ibge_malha_municipal.yaml").read_text(encoding="utf-8"))
    assert (ROOT / s["arquivo"]).is_file()
    assert "Fonte: IBGE" in s["origem"]["licenca"] and s["pendencias"]
    assert s["origem"]["uso_comercial"] == "nao_verificado"      # honesto: o texto da licença não foi lido


@pytest.fixture(scope="module")
def build():
    pytest.importorskip("shapely"); pytest.importorskip("shapefile"); pytest.importorskip("mapbox_vector_tile"); pytest.importorskip("pmtiles")
    spec = importlib.util.spec_from_file_location("build_malha", ROOT / "scripts" / "build-malha-municipal.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_malha"] = mod
    spec.loader.exec_module(mod)
    return mod


def _zip_sintetico(tmp_path: Path) -> Path:
    import shapefile
    import zipfile
    base = tmp_path / "BR_Municipios_2024"
    w = shapefile.Writer(str(base), shapeType=shapefile.POLYGON)
    for c, t in (("CD_MUN", "C"), ("NM_MUN", "C"), ("SIGLA_UF", "C"), ("NM_UF", "C")):
        w.field(c, t, size=60)
    quadrados = [("3205309", "Vitória", "ES", "Espírito Santo", -40.4, -20.4), ("3200136", "Vizinho", "ES", "Espírito Santo", -40.3, -20.4), ("1100015", "Longe", "RO", "Rondônia", -62.0, -12.0),
                 ("4300001", "Lagoa dos Patos", "RS", "Rio Grande do Sul", -51.5, -31.0)]
    for cod, nome, uf, nome_uf, x, y in quadrados:
        w.poly([[[x, y], [x, y + 0.1], [x + 0.1, y + 0.1], [x + 0.1, y], [x, y]]])
        w.record(cod, nome, uf, nome_uf)
    w.close()
    z = tmp_path / "BR_Municipios_2024.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for ext in ("shp", "shx", "dbf"):
            zf.write(f"{base}.{ext}", f"BR_Municipios_2024.{ext}")
    return z


def test_build_gera_tiles_com_as_duas_camadas_e_sem_as_lagoas(build, tmp_path):
    import mapbox_vector_tile
    from pmtiles.reader import MmapSource, Reader

    feicoes = build.ler_malha(_zip_sintetico(tmp_path), tmp_path / "x")
    assert sorted(f["ibge"] for f in feicoes) == ["1100015", "3200136", "3205309"]        # a lagoa saiu
    saida = tmp_path / "m.pmtiles"
    r = build.escrever_pmtiles(saida, build.gerar_tiles(feicoes, 4), 4, "0" * 64)
    assert r["tiles"] > 0 and r["bytes"] == saida.stat().st_size
    with saida.open("rb") as f:
        leitor = Reader(MmapSource(f))
        assert leitor.header()["max_zoom"] == 4
        achados = {}
        for x in range(0, 16):
            for y in range(0, 16):
                t = leitor.get(4, x, y)
                if t:
                    d = mapbox_vector_tile.decode(gzip.decompress(t))
                    for ft in d.get("municipios", {}).get("features", []):
                        achados[ft["properties"]["ibge"]] = ft["properties"]
                    assert "ufs" in d
        assert set(achados) == {"1100015", "3200136", "3205309"}
        assert achados["3205309"] == {"ibge": "3205309", "nome": "Vitória", "uf": "ES"}


def test_geometria_do_tile_e_o_municipio_certo_no_lugar_certo(build):
    """Web Mercator: Vitória (-40,3; -20,3) cai no tile x=6, y=8 do zoom 4, e só nele."""
    px, py = build.mercator(-40.3, -20.3)
    esq, baixo, dir_, cima = build.limites_do_tile(4, 6, 8)
    assert esq < px < dir_ and baixo < py < cima
    assert list(build.tiles_da_caixa((px, py, px, py), 4)) == [(6, 8)]
