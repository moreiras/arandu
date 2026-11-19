# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — scripts/mem_sample.py: parsing do `docker stats`, memória do host e encerramento junto com o pai."""
import json
import os
import subprocess
from pathlib import Path

from scripts import mem_sample as ms

ROOT = Path(__file__).resolve().parents[2]


def test_parse_size_unidades_binarias_e_decimais():
    assert ms.parse_size("5.742GiB") == int(5.742 * 1024**3)
    assert ms.parse_size("64MiB") == 64 * 1024**2
    assert ms.parse_size("7.367MiB") == int(7.367 * 1024**2)
    assert ms.parse_size("1.5GB") == 1_500_000_000
    assert ms.parse_size("0B") == 0
    assert ms.parse_size("--") is None and ms.parse_size("") is None


def test_parse_docker_stats():
    out = "arandurape-api\t5.742GiB / 7GiB\t0.38%\npostgres\t60.18MiB / 15.62GiB\t0.86%\nruim\tlinha incompleta\n"
    rows = ms.parse_docker_stats(out)
    assert [r["nome"] for r in rows] == ["arandurape-api", "postgres"]
    assert rows[0]["pct_limite"] == 82.0 and rows[0]["limite_bytes"] == 7 * 1024**3 and rows[0]["cpu_pct"] == 0.38


def test_host_memory_a_partir_do_proc_meminfo():
    txt = "MemTotal:       16384000 kB\nMemFree:          771000 kB\nMemAvailable:    6430000 kB\nCached:          7779000 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\n"
    h = ms.host_memory(txt)
    assert h["total_bytes"] == 16384000 * 1024 and h["disponivel_bytes"] == 6430000 * 1024 and h["swap_usado_bytes"] == 0
    assert ms.host_memory("nada") is None


def test_once_grava_uma_linha_json_mesmo_sem_docker(tmp_path, monkeypatch):
    monkeypatch.setattr(ms.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(OSError("sem docker")))
    out = tmp_path / "ops" / "mem" / "2026-10-18.jsonl"
    assert ms.main(["--out", str(out), "--once"]) == 0
    row = json.loads(out.read_text().splitlines()[0])
    assert row["containers"] is None and "ts" in row


def test_termina_quando_o_processo_pai_acaba(tmp_path):
    pai = subprocess.Popen(["sleep", "1.5"])
    out = tmp_path / "m.jsonl"
    amostrador = subprocess.Popen(["python3", "scripts/mem_sample.py", "--out", str(out), "--parent", str(pai.pid),
                                   "--interval", "0.3"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pai.wait()                                   # reaproveita o zumbi: `kill -0` num zumbi ainda "existe"
    assert amostrador.wait(timeout=30) == 0
    assert len(out.read_text().splitlines()) >= 1          # uma amostra por ciclo; o `docker stats` leva ~2 s


def test_pipeline_inicia_o_amostrador_de_forma_opcional_e_nao_bloqueante():
    text = (ROOT / "scripts" / "arandu-weekly.sh").read_text()
    assert "mem_sample.py" in text and 'MEM_SAMPLE:-on' in text and "--parent $$" in text
    assert subprocess.run(["bash", "-n", "scripts/arandu-weekly.sh"], cwd=ROOT).returncode == 0


def test_diag_da_api_entra_na_amostra_e_falha_sem_derrubar(monkeypatch):
    monkeypatch.setattr(ms.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(OSError("sem docker")))
    assert ms.api_diag("arandurape-api") is None
    row = ms.sample("arandurape-api")
    assert row["api_diag"] is None and row["containers"] is None


def test_pipeline_passa_o_container_da_api_ao_amostrador():
    assert "--diag-container" in (ROOT / "scripts" / "arandu-weekly.sh").read_text()
