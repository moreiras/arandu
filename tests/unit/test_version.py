# SPDX-License-Identifier: AGPL-3.0-or-later
"""T0 — VERSION como fonte única da versão do sistema."""
import re
from pathlib import Path

from core import common as _common

ROOT = Path(__file__).resolve().parents[2]


def test_arquivo_version_existe_e_e_semver():
    # X.Y.Z, com 4º componente opcional para revisão de hotfix após o merge (v1.F.N.1)
    v = (ROOT / "VERSION").read_text().strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+(\.\d+)?", v), v


def test_app_version_le_o_arquivo():
    assert _common.app_version() == (ROOT / "VERSION").read_text().strip()


def test_app_version_fallback_sem_arquivo(monkeypatch, tmp_path):
    _common.app_version.cache_clear()
    monkeypatch.setattr(_common, "__file__", str(tmp_path / "collector" / "_common.py"))
    monkeypatch.setenv("ARANDU_VERSION", "9.9.9")
    try:
        assert _common.app_version() == "9.9.9"
        _common.app_version.cache_clear()
        monkeypatch.delenv("ARANDU_VERSION")
        assert _common.app_version() == "desconhecida"
    finally:
        _common.app_version.cache_clear()


def test_health_expoe_a_versao(app_client):
    client, app, _ = app_client

    class _Store:
        def latest(self):
            return "2026-10-04"

        def list_snapshots(self):
            return ["2026-09-27", "2026-10-04"]

    app.state.store = _Store()
    try:
        body = client.get("/health").json()
    finally:
        del app.state.store
    assert body["version"] == (ROOT / "VERSION").read_text().strip()
    assert body["status"] == "ok"


def test_snapshot_builder_usa_a_mesma_versao():
    from publish.snapshot_builder import PIPELINE_VERSION

    assert PIPELINE_VERSION == (ROOT / "VERSION").read_text().strip()
