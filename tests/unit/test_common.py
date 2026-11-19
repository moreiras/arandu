# SPDX-License-Identifier: AGPL-3.0-or-later
"""T0 — utilitários compartilhados dos coletores (`core/common.py`)."""
import gzip
import json
import re
from pathlib import Path

import pytest

from core import common as _common


def test_caminhos_por_data():
    b = Path("/dados")
    assert _common.raw_path(b, "2026-09-20", "sp", "x.txt") == Path("/dados/raw/2026-09-20/sp/x.txt")
    assert _common.normalized_path(b, "2026-09-20", "summary") == Path("/dados/normalized/2026-09-20/summary")
    assert _common.published_path(b, "2026-09-20", "asns", "1.json") == Path("/dados/published/2026-09-20/asns/1.json")


def test_json_gz_ida_e_volta_preserva_utf8_e_cria_pastas(tmp_path):
    p = tmp_path / "a" / "b" / "x.json.gz"
    dado = {"nome": "São João — Açaí", "n": [1, 2, 3]}
    _common.write_json_gz(p, dado)
    assert _common.read_json_gz(p) == dado
    with gzip.open(p, "rt", encoding="utf-8") as f:                    # sem escapes \uXXXX no arquivo
        assert "São João" in f.read()


def test_data_dir_prioriza_variavel_de_ambiente(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert _common.data_dir() == tmp_path


def test_data_dir_cai_para_settings_ou_padrao(monkeypatch):
    monkeypatch.delenv("DATA_DIR", raising=False)
    assert isinstance(_common.data_dir(), Path)


def test_today_e_now_iso():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", _common.today_str())
    assert _common.now_iso().endswith("+00:00")


def test_load_ixps_tem_os_campos_usados_pelo_lg():
    ixps = _common.load_ixps()
    assert len(ixps) >= 30
    for ix in ixps:
        assert {"code", "name", "uf", "telnet_host"} <= set(ix)
    assert len({ix["code"] for ix in ixps}) == len(ixps)             # códigos únicos


def test_load_peeringdb_ixps_config():
    c = _common.load_peeringdb_ixps_config()
    assert c["external"] and c["ixbr"]
    for ix in c["external"] + c["ixbr"]:
        assert isinstance(ix["pdb_ix_id"], int) and ix["code"]


def test_configure_logging_aceita_formato_texto(monkeypatch):
    monkeypatch.setenv("LOG_FORMAT", "text")
    assert _common.configure_logging() is not None
    monkeypatch.setenv("LOG_FORMAT", "json")
    assert _common.configure_logging() is not None
