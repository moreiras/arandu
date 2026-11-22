# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`scripts/espelhar-dados.sh` com destino local: o que vai, o que fica, SQLite consistente e só quando há snapshot novo."""
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "espelhar-dados.sh"
pytestmark = pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync ausente")


def _arquivo(p: Path, texto: str = "x") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto)


def _origem(base: Path) -> Path:
    d = base / "origem"
    _arquivo(d / "published/2026-11-15/manifest.json", "{}")
    _arquivo(d / "published/2026-11-15/asns.json", "[]")
    _arquivo(d / "normalized/2026-11-15/summary/geo_orgs.json.gz")
    _arquivo(d / "raw/2026-11-15/sp/ixbr_members.json", "{}")
    _arquivo(d / "raw/2026-11-15/sp/lg_bgp.json.gz", "bruto")
    _arquivo(d / "raw/dbip/base.mmdb", "bruto")
    _arquivo(d / "tiles/basemap.pmtiles")
    _arquivo(d / "ops/usage/2026-11-22.jsonl", "{}\n")
    _arquivo(d / "ops/usage/.salt-2026-11-22", "segredo")
    (d / "auth").mkdir()
    con = sqlite3.connect(d / "auth/contas.db")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("create table contas (id integer)")
    con.execute("insert into contas values (7)")
    con.commit()                                   # aberto de propósito: o dado pode estar só no -wal
    _arquivo(d / "auth/emails.csv", "a")
    return d, con


def _rodar(origem: Path, destino: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, DATA_DIR_HOST=str(origem), ESPELHO_DESTINO=str(destino) + "/",
               ESPELHO_ESTADO=str(origem.parent / "estado.txt"))
    return subprocess.run(["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=60)


def test_espelha_sem_o_bruto_e_com_sqlite_consistente(tmp_path):
    origem, con = _origem(tmp_path)
    destino = tmp_path / "destino"
    _arquivo(destino / "auth/contas.db-wal", "wal de outro banco")   # sobra do banco antigo do destino
    r = _rodar(origem, destino)
    con.close()
    assert r.returncode == 0, r.stdout + r.stderr
    assert (destino / "published/2026-11-15/manifest.json").exists()
    assert (destino / "published/2026-11-15/asns.json").exists()
    assert (destino / "normalized/2026-11-15/summary/geo_orgs.json.gz").exists()
    assert (destino / "raw/2026-11-15/sp/ixbr_members.json").exists()
    assert not (destino / "raw/2026-11-15/sp/lg_bgp.json.gz").exists()
    assert not (destino / "raw/dbip").exists()
    assert (destino / "tiles/basemap.pmtiles").exists()
    assert (destino / "ops/usage/2026-11-22.jsonl").exists()
    assert not (destino / "ops/usage/.salt-2026-11-22").exists()
    assert (destino / "auth/emails.csv").exists()
    assert not (destino / "auth/contas.db-wal").exists()
    assert sqlite3.connect(destino / "auth/contas.db").execute("select id from contas").fetchall() == [(7,)]


def test_sem_snapshot_novo_nao_copia(tmp_path):
    origem, con = _origem(tmp_path)
    con.close()
    destino = tmp_path / "destino"
    assert _rodar(origem, destino).returncode == 0
    _arquivo(origem / "tiles/novo.pmtiles")
    r = _rodar(origem, destino)
    assert r.returncode == 0 and "nada novo" in r.stdout
    assert not (destino / "tiles/novo.pmtiles").exists()
    assert _rodar(origem, destino, "--forcar").returncode == 0
    assert (destino / "tiles/novo.pmtiles").exists()


def test_origem_sem_snapshot_aborta_sem_apagar_o_destino(tmp_path):
    origem = tmp_path / "origem"
    (origem / "published").mkdir(parents=True)
    destino = tmp_path / "destino"
    _arquivo(destino / "published/2026-11-15/manifest.json", "{}")
    r = _rodar(origem, destino, "--forcar")
    assert r.returncode == 1
    assert (destino / "published/2026-11-15/manifest.json").exists()
