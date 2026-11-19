# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Índice legado dos snapshots anteriores ao armazém: `data/catalog/snapshots/{date}.json`.

Não altera nada do que foi publicado: apenas registra, por fonte, a `as_of` inferida (a data do snapshot, ou o mês
de referência no SICI e no dump de sócios), a marca `legado: true` e onde os arquivos estão nos caminhos antigos.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
from pathlib import Path

from core.catalog.loader import Catalog
from core.store.fontes import arquivos_da_fonte, as_of_do_dado


def indice_legado(cat: Catalog, data_dir: Path, date: str) -> dict:
    fontes = []
    for s in sorted(cat.sources.values(), key=lambda x: x.id):
        if s.tipo == "curada":
            continue
        arqs = arquivos_da_fonte(cat, data_dir, s.id, date)
        if not arqs:
            continue
        fontes.append({"id": s.id, "as_of": as_of_do_dado(s.id, arqs, date), "legado": True,
                       "arquivos": sorted(arqs)})
    return {"snapshot": date, "legado": True, "gerado_em": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fontes": fontes}


def caminho_indice(data_dir: Path, date: str) -> Path:
    return Path(data_dir) / "catalog" / "snapshots" / f"{date}.json"


def escrever_indice_legado(cat: Catalog, data_dir: Path, date: str, *, sobrescrever: bool = False) -> Path:
    destino = caminho_indice(data_dir, date)
    if destino.exists() and not sobrescrever:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=destino.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(indice_legado(cat, data_dir, date), f, ensure_ascii=False, indent=1)
    os.chmod(tmp, 0o644)
    os.replace(tmp, destino)
    return destino


def ler_indice(data_dir: Path, date: str) -> dict | None:
    try:
        return json.loads(caminho_indice(data_dir, date).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
