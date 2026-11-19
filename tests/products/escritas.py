# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Conta quantas vezes cada arquivo de `published/` é escrito durante o pipeline (medição "escritas por arquivo").

Intercepta `Path.write_text/write_bytes` e `open(..., "w*")` (o `gzip.open` chama o `open`, então não é contado à parte); chaves relativas a `published/<data>/`.
"""
from __future__ import annotations

import builtins
import pathlib
from collections import Counter
from contextlib import contextmanager


@contextmanager
def contar_escritas(base):
    base = pathlib.Path(base).resolve()
    contagem: Counter = Counter()

    def anota(alvo):
        try:
            rel = pathlib.Path(alvo).resolve().relative_to(base / "published")
        except (ValueError, OSError, TypeError):
            return
        contagem[str(rel)] += 1

    wt, wb, op = pathlib.Path.write_text, pathlib.Path.write_bytes, builtins.open

    def _wt(self, *a, **k):
        anota(self)
        return wt(self, *a, **k)

    def _wb(self, *a, **k):
        anota(self)
        return wb(self, *a, **k)

    def _open(file, mode="r", *a, **k):
        if isinstance(mode, str) and any(c in mode for c in "wax"):
            anota(file)
        return op(file, mode, *a, **k)

    pathlib.Path.write_text, pathlib.Path.write_bytes, builtins.open = _wt, _wb, _open
    try:
        yield contagem
    finally:
        pathlib.Path.write_text, pathlib.Path.write_bytes, builtins.open = wt, wb, op
