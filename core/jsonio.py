# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Leitura tolerante de JSON dos artefatos de build: arquivo ausente ou ilegível devolve `default`, não levanta."""
from __future__ import annotations

import gzip
import json
from pathlib import Path


def carregar_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_bytes())
    except Exception:
        return default


def carregar_json_gz(path: Path, default=None):
    if not path.exists():
        return default
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def gravar_json_gz(path: Path, payload) -> None:
    """JSON comprimido, UTF-8 (`ensure_ascii=False`), como os artefatos publicados."""
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
