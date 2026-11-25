# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — api/snapshot_detail.py: sidecar do detalhe de snapshot (memória da API)."""
import json

from api import snapshot_detail as sd


def test_manifest_meta_so_leva_os_campos_publicos():
    m = {"pipeline_version": "1", "generated_at": "x", "ixps_configured": ["a"], "ixps_collected": ["a"],
         "ixps_failed": [], "coleta": "completa", "coleta_ok": True, "checks": {"a": 1}, "checksums": {"x": "y"} }
    meta = sd.manifest_meta(m)
    assert "checksums" not in meta and meta["coleta_ok"] is True and meta["ixps_collected"] == ["a"]
    assert sd.manifest_meta(None) is None and sd.manifest_meta({}) is None


def test_sidecar_ida_e_volta_e_versao_incompativel_e_ignorada(tmp_path):
    (tmp_path / "published" / "2026-10-11").mkdir(parents=True)
    path = sd.write_sidecar(tmp_path, "2026-10-11", {"date": "2026-10-11", "summary": {"a": 1}, "manifest": None})
    assert path.name == "snapshot_detail.json" and not list(path.parent.glob("*.tmp"))
    got = sd.read_sidecar(tmp_path, "2026-10-11")
    assert got["summary"] == {"a": 1} and got["versao"] == sd.SIDECAR_VERSION
    path.write_text(json.dumps({"versao": 99, "summary": {}}))
    assert sd.read_sidecar(tmp_path, "2026-10-11") is None
    path.write_text("{ quebrado")
    assert sd.read_sidecar(tmp_path, "2026-10-11") is None
    assert sd.read_sidecar(tmp_path, "2000-01-01") is None


def test_refresh_atualiza_so_o_bloco_do_manifesto(tmp_path):
    d = tmp_path / "published" / "2026-10-11"
    d.mkdir(parents=True)
    sd.write_sidecar(tmp_path, "2026-10-11", {"date": "2026-10-11", "summary": {"k": 7}, "manifest": {"coleta": "pendente"}})
    (d / "manifest.json").write_text(json.dumps({"pipeline_version": "2", "coleta": "completa", "coleta_ok": True,
                                                 "checksums": {"a": "b"}}))
    assert sd.refresh_manifest_meta(tmp_path, "2026-10-11") is True
    got = sd.read_sidecar(tmp_path, "2026-10-11")
    assert got["summary"] == {"k": 7} and got["manifest"]["coleta"] == "completa" and "checksums" not in got["manifest"]
    assert sd.refresh_manifest_meta(tmp_path, "2000-01-01") is False


def test_manifest_meta_repassa_comparado_com():
    """A home calcula a variação contra `manifest.comparado_com`; sem o campo, os KPIs de rede nunca mostravam variação (HOME-E1)."""
    assert sd.manifest_meta({"coleta": "completa", "comparado_com": "2026-11-15"})["comparado_com"] == "2026-11-15"
    assert sd.manifest_meta({"coleta": "completa"})["comparado_com"] is None


def test_sidecar_gravado_sem_comparado_com_le_o_campo_do_manifesto(tmp_path):
    d = tmp_path / "published" / "2026-11-22"
    d.mkdir(parents=True)
    sd.write_sidecar(tmp_path, "2026-11-22", {"date": "2026-11-22", "summary": {}, "manifest": {"coleta": "completa"}})
    (d / "manifest.json").write_text(json.dumps({"coleta": "completa", "comparado_com": "2026-11-15"}))
    before = (d / sd.SIDECAR).read_bytes()
    assert sd.read_sidecar(tmp_path, "2026-11-22")["manifest"]["comparado_com"] == "2026-11-15"
    assert (d / sd.SIDECAR).read_bytes() == before                     # leitura: o publicado não é regravado
    (d / "manifest.json").write_text(json.dumps({"coleta": "completa"}))
    assert sd.read_sidecar(tmp_path, "2026-11-22")["manifest"]["comparado_com"] is None
