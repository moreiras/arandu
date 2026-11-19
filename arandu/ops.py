# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`arandu doctor`: saúde do ambiente. A retenção (`arandu gc`) está em `arandu/retencao.py`."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from arandu import lockfile
from arandu.executor import ler_relatorio, idade_dias
from core.catalog.loader import Catalog, validate

AVISO_DISCO_PCT = 70
BLOQUEIO_DISCO_PCT = 85


def diagnostico(cat: Catalog, data_dir: Path, repo: Path, em: str) -> list[dict]:
    r: list[dict] = []

    def add(nome, estado, detalhe=""):
        r.append({"nome": nome, "estado": estado, "detalhe": detalhe})

    if not data_dir.is_dir():
        add("data_dir", "erro", f"{data_dir} não existe")
        return r
    du = shutil.disk_usage(data_dir)
    pct = round(100 * du.used / du.total, 1)
    est = "erro" if pct >= BLOQUEIO_DISCO_PCT else ("aviso" if pct >= AVISO_DISCO_PCT else "ok")
    add("disco", est, f"{pct}% usado ({du.free >> 30} GiB livres); aviso {AVISO_DISCO_PCT}%, bloqueio de coleta pesada {BLOQUEIO_DISCO_PCT}%")
    if est != "ok":
        r[-1]["detalhe"] += "; veja o que o gc liberaria: arandu gc --dry-run"
    tiles = data_dir / "tiles"
    if (tiles / "current.json").is_file():
        try:
            data_atual = json.loads((tiles / "current.json").read_text(encoding="utf-8"))["date"]
            tam = sum(f.stat().st_size for f in (tiles / data_atual).rglob("*") if f.is_file())
            livre = du.free
            add("basemap", "ok" if livre >= 2 * tam else "aviso",
                f"versão {data_atual} ocupa {tam >> 20} MiB; reconstruir exige ~2× ({(2 * tam) >> 20} MiB) e há {livre >> 20} MiB livres")
        except (OSError, ValueError, KeyError):
            add("basemap", "aviso", "current.json ilegível")
    try:
        sv = os.statvfs(data_dir)
        if sv.f_files:
            ipct = round(100 * (sv.f_files - sv.f_ffree) / sv.f_files, 1)
            add("inodes", "erro" if ipct >= BLOQUEIO_DISCO_PCT else ("aviso" if ipct >= AVISO_DISCO_PCT else "ok"), f"{ipct}% usados")
    except OSError:
        add("inodes", "aviso", "statvfs indisponível")
    info = lockfile.ocupado(data_dir / "ops" / "arandu.lock")
    if info is not None:
        add("lock", "aviso", f"execução em andamento (pid {info.get('pid', '?')}, início {info.get('inicio', '?')})")
    else:
        add("lock", "ok", "livre")
    erros = validate(cat)
    add("catalogo", "erro" if erros else "ok", f"{len(cat.sources)} fontes, {len(cat.products)} produtos, {len(cat.steps)} etapas; {len(erros)} erro(s)")
    try:
        v = (repo / "VERSION").read_text(encoding="utf-8").strip()
        add("versao", "ok", v)
    except OSError:
        add("versao", "aviso", "arquivo VERSION ausente")
    runs = sorted((p.stem for p in (data_dir / "ops" / "runs").glob("*.json")), reverse=True) if (data_dir / "ops" / "runs").is_dir() else []
    if runs:
        rel = ler_relatorio(data_dir, runs[0]) or {}
        import datetime as dt
        dias = (dt.date.fromisoformat(em) - dt.date.fromisoformat(runs[0])).days
        crit = rel.get("falhas_criticas", [])
        est = "erro" if crit else ("aviso" if dias > 8 or rel.get("avisos") else "ok")
        add("ultima_execucao", est, f"{runs[0]} (há {dias} d): ok={rel.get('ok')}, críticas={crit}, avisos={rel.get('avisos', [])}")
    else:
        add("ultima_execucao", "aviso", "nenhum relatório do arandu em data/ops/runs ainda")
    return r
