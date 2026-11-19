#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Amostrador de memória: o pico da API e do worker DURANTE o pipeline semanal.

    python3 scripts/mem_sample.py --out data/ops/mem/AAAA-MM-DD.jsonl [--interval 30] [--parent PID] [--once]

A cada `--interval` s grava uma linha JSON com a memória do host (MemTotal/MemAvailable) e de cada container
(`docker stats --no-stream`: uso, limite e CPU). Termina sozinho quando o processo `--parent` deixa de existir
(o `arandu-weekly.sh` passa o próprio PID) ou depois de `--max-hours`. Somente leitura; qualquer falha é engolida:
medir nunca pode derrubar o pipeline.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_UNITS = {"b": 1, "kb": 1000, "mb": 1000**2, "gb": 1000**3, "tb": 1000**4,
          "kib": 1024, "mib": 1024**2, "gib": 1024**3, "tib": 1024**4}


def parse_size(text: str) -> int | None:
    """'5.742GiB' → bytes; '0B' → 0; '--' → None."""
    m = re.fullmatch(r"\s*([0-9]*\.?[0-9]+)\s*([A-Za-z]+)\s*", text or "")
    if not m or m.group(2).lower() not in _UNITS:
        return None
    return int(float(m.group(1)) * _UNITS[m.group(2).lower()])


def parse_docker_stats(output: str) -> list[dict]:
    """Linhas 'nome<TAB>5.7GiB / 7GiB<TAB>0.38%' → [{nome, bytes, limite_bytes, pct_limite, cpu_pct}]."""
    rows = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        name, mem, cpu = parts[0].strip(), parts[1], parts[2]
        used, _, limit = mem.partition("/")
        u, lim = parse_size(used), parse_size(limit)
        rows.append({"nome": name, "bytes": u, "limite_bytes": lim,
                     "pct_limite": round(u / lim * 100, 1) if u is not None and lim else None,
                     "cpu_pct": float(cpu.strip().rstrip("%")) if re.fullmatch(r"\s*[0-9.]+%\s*", cpu) else None})
    return rows


def host_memory(meminfo: str | None = None) -> dict | None:
    try:
        text = meminfo if meminfo is not None else Path("/proc/meminfo").read_text()
    except OSError:
        return None
    vals = {m.group(1): int(m.group(2)) * 1024 for m in re.finditer(r"^(\w+):\s+(\d+) kB", text, re.M)}
    if "MemTotal" not in vals:
        return None
    return {"total_bytes": vals["MemTotal"], "disponivel_bytes": vals.get("MemAvailable"),
            "livre_bytes": vals.get("MemFree"), "cache_bytes": vals.get("Cached"),
            "swap_usado_bytes": vals.get("SwapTotal", 0) - vals.get("SwapFree", 0)}


_DIAG_SNIPPET = ("import urllib.request,json;d=json.load(urllib.request.urlopen("
                 "'http://127.0.0.1:8000/api/v1/internal/diag',timeout=20));"
                 "p=d['processo'];m=d.get('pymalloc') or {};s=d['store'];"
                 "print(json.dumps({'rss':p.get('rss_bytes'),'pico':p.get('rss_pico_bytes'),'threads':p.get('threads'),"
                 "'cgroup':p.get('cgroup_bytes'),'py_vivos':m.get('bytes_em_blocos_vivos'),"
                 "'py_arenas':m.get('bytes_arenas_reservadas'),'frag_pct':m.get('fragmentacao_pct'),"
                 "'datas':s['datas_residentes'],'caches':len(s['caches']),"
                 "'byte_cache':(d.get('byte_cache_latest') or {}).get('size_bytes')}))")


def api_diag(container: str) -> dict | None:
    """Diagnóstico LEVE da API (sem `deep`, milissegundos) para ver a fragmentação evoluir durante o run."""
    try:
        r = subprocess.run(["docker", "exec", container, "python3", "-c", _DIAG_SNIPPET],
                           capture_output=True, text=True, timeout=45)
        return json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def sample(diag_container: str | None = None) -> dict:
    out = {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "host": host_memory()}
    if diag_container:
        out["api_diag"] = api_diag(diag_container)
    try:
        r = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}"],
                           capture_output=True, text=True, timeout=60)
        out["containers"] = parse_docker_stats(r.stdout)
    except (OSError, subprocess.SubprocessError):
        out["containers"] = None
    return out


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--interval", type=float, default=30)
    ap.add_argument("--parent", type=int, help="PID a acompanhar; encerra quando ele terminar")
    ap.add_argument("--max-hours", type=float, default=14)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--diag-container", help="container da API (ex.: arandurape-api): inclui o diag leve em cada amostra")
    a = ap.parse_args(argv)
    out = Path(a.out)
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return 0
    deadline = time.time() + a.max_hours * 3600
    while True:
        try:
            with open(out, "a", encoding="utf-8") as f:
                f.write(json.dumps(sample(a.diag_container), ensure_ascii=False, separators=(",", ":")) + "\n")
        except Exception:  # noqa: BLE001 — medir nunca derruba o pipeline
            pass
        if a.once or (a.parent and not _alive(a.parent)) or time.time() > deadline:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
