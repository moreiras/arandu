# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Entregas entre produtos do build: o que um produto deixa para o seguinte em `build/<data>/intermediarios/`.

Com uma etapa do arandu por produto, os produtos do build não compartilham memória: cada entrega vira um arquivo de montagem (não publicado; o `arandu gc` guarda 2 datas de `build/`).
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from core.common import build_path

CONJUNTOS = "conjuntos_prefixos"
_CHAVES = ("global_br_v4", "global_br_v6", "ixp_all_v4", "ixp_all_v6")


def caminho(base: Path, date_str: str, nome: str) -> Path:
    return build_path(base, date_str, "intermediarios", f"{nome}.json.gz")


def gravar_conjuntos(base: Path, date_str: str, global_br_v4: set, global_br_v6: set, ixp_all_v4: set, ixp_all_v6: set) -> Path:
    """Os quatro conjuntos de prefixos que o índice de ASNs deixa para o Hilbert e para o resumo (listas ordenadas: bytes estáveis)."""
    destino = caminho(base, date_str, CONJUNTOS)
    destino.parent.mkdir(parents=True, exist_ok=True)
    corpo = {k: sorted(v) for k, v in zip(_CHAVES, (global_br_v4, global_br_v6, ixp_all_v4, ixp_all_v6))}
    tmp = destino.with_name(destino.name + ".tmp")
    with tmp.open("wb") as bruto, gzip.GzipFile(filename="", mode="wb", fileobj=bruto, compresslevel=6, mtime=0) as f:
        f.write(json.dumps(corpo, ensure_ascii=False).encode("utf-8"))
    tmp.replace(destino)
    return destino


def ler_conjuntos(base: Path, date_str: str) -> dict[str, set]:
    """{global_br_v4, global_br_v6, ixp_all_v4, ixp_all_v6} como conjuntos; FileNotFoundError se o índice de ASNs não rodou antes."""
    with gzip.open(caminho(base, date_str, CONJUNTOS), "rt", encoding="utf-8") as f:
        corpo = json.load(f)
    return {k: set(corpo[k]) for k in _CHAVES}
