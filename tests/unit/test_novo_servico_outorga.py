# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Simulação: um quinto serviço de outorga (fictício) com UMA entrada no registro + o scaffold.

Mede o esforço (nº de arquivos para acrescentar um serviço): à mão, só `core/outorgas.py`; o resto é gerado.
"""
import gzip
import importlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

from core import outorgas
from core.catalog.loader import load_catalog, validate

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def servico_xyz(monkeypatch):
    """Registra o serviço fictício 'xyz' (código 999) só durante o teste."""
    novo = outorgas.Servico("xyz", "xyzs", "999", lambda n: "servico xyz" in n)
    monkeypatch.setitem(outorgas.SERVICOS, "xyz", novo)
    return novo


def _scaffold(raiz, nome="Serviço XYZ"):
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        mod = importlib.import_module("novo_servico_outorga")
    finally:
        sys.path.pop(0)
    return mod


def test_scaffold_gera_os_arquivos_e_o_catalogo_continua_valido(tmp_path, servico_xyz):
    mod = _scaffold(tmp_path)
    novos = mod.arquivos("xyz", "Serviço XYZ")
    assert set(novos) == {
        "sources/anatel_xyz/__init__.py", "sources/anatel_xyz/collect.py", "sources/xyz_geo/__init__.py", "sources/xyz_geo/enrich.py",
        "catalog/sources/anatel_xyz.yaml", "catalog/sources/xyz_geo.yaml", "catalog/steps/anatel_xyz.yaml", "catalog/steps/xyz_geo.yaml",
    }
    shutil.copytree(ROOT / "catalog", tmp_path / "catalog")
    assert mod.main(["xyz", "--nome", "Serviço XYZ", "--raiz", str(tmp_path)]) == 0
    cat = load_catalog(tmp_path / "catalog")
    assert validate(cat) == [], validate(cat)
    assert {"anatel_xyz", "xyz_geo"} <= set(cat.sources) and {"anatel_xyz", "xyz_geo"} <= set(cat.steps)
    # a geocodificação roda depois da coleta (entradas herdadas do modelo)
    assert "anatel_xyz" in cat.steps and cat.sources["xyz_geo"].entradas[0] == "anatel_xyz"
    # não sobrescreve
    assert mod.main(["xyz", "--nome", "x", "--raiz", str(tmp_path)]) == 1


def test_scaffold_exige_a_entrada_no_registro(tmp_path):
    mod = _scaffold(tmp_path)
    with pytest.raises(SystemExit, match="core/outorgas.py"):
        mod.arquivos("naoexiste", "x")


def test_cadeia_completa_do_quinto_servico_sem_codigo_novo(tmp_path, servico_xyz, monkeypatch):
    """CSV → coleta → geocodificação → publicação → leitura na API, só com a entrada do registro (+ módulos gerados)."""
    from api.outorgas_store import OutorgasPublicadas
    from core.common import normalized_path, read_json_gz, write_json_gz
    from products.outorgas.build import publicar_outorgas
    from sources.anatel_outorgas import geo as ogeo
    from sources.anatel_outorgas.servicos import parse_csv

    csv_bytes = (
        "Código e Nome do Serviço da Notificação;CNPJ ou CPF;Nome Entidade Prestadora de Serviço;Logradouro do Endereço Sede;"
        "Município;UF;Telefone Principal\n"
        "999 - Servico XYZ;12345678000190;Empresa Xyz;Rua A;Brasília;DF;6130000000\n"
        "045 - Multimídia;99999999000199;Outra;Rua B;Recife;PE;8130000000\n"
    ).encode("utf-8")
    registros = parse_csv(csv_bytes, servico_xyz)
    assert [r["cnpj"] for r in registros] == ["12345678000190"]            # filtrou só o código 999

    date = "2026-10-23"
    write_json_gz(normalized_path(tmp_path, date, "summary", "anatel_xyz.json.gz"), {"xyzs": registros})
    monkeypatch.setattr(ogeo, "_geolocate", lambda rec, client: {"lat": -15.8, "lon": -47.9, "geo_confidence": "city_centroid", "geo_source": "nominatim"})
    monkeypatch.setattr(ogeo, "NOMINATIM_DELAY", 0.0)

    class Log:
        def info(self, *a, **k): pass
        warning = error = exception = info

    ogeo.rodar(servico_xyz, date, tmp_path, False, Log())
    r = publicar_outorgas(servico_xyz, tmp_path, date, Log())
    assert r["xyz_total"] == 1 and r["xyz_geo_features"] == 1
    pub = tmp_path / "published" / date
    assert json.loads(gzip.open(pub / "xyz.json.gz", "rt").read())["xyzs"][0]["geo_confidence"] == "city_centroid"
    assert (pub / "maps" / "xyzs.geojson").exists()
    # a API lê pelo mesmo caminho dos outros serviços (o registro da API vem do mesmo lugar)
    assert "xyz" in outorgas.SERVICOS
    o = OutorgasPublicadas(lambda d: tmp_path / "published" / d, "xyz")
    assert o.index(date)[0]["razao_social"] == "Empresa Xyz" and "telefone" not in o.index(date)[0]
    assert o.geo_map(date)["features"][0]["properties"]["cnpj"] == "12345678000190"
