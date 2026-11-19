# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Checksums dos artefatos publicados: o manifesto cobre tudo o que está em `published/<data>/`."""
from __future__ import annotations

import hashlib
from pathlib import Path

# Fora dos checksums: o próprio manifesto e o detalhe do snapshot, que carrega uma cópia dos metadados do manifesto (circular).
EXCLUIDOS = frozenset({"manifest.json", "snapshot_detail.json"})


def sha256_arquivo(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def calcular_checksums(pub_dir: Path, pular: frozenset[str] = EXCLUIDOS) -> dict[str, str]:
    """SHA-256 de todos os arquivos de `pub_dir` (chave = caminho relativo), menos os de `pular` e os temporários `.tmp`."""
    saida: dict[str, str] = {}
    for path in sorted(pub_dir.rglob("*")):
        if path.is_file() and path.name not in pular and not path.name.endswith(".tmp"):
            saida[str(path.relative_to(pub_dir))] = sha256_arquivo(path)
    return saida
