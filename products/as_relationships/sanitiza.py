# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""E0 — sanitização de AS_PATH (Luckie et al., IMC 2013, §4.3): prepend comprimido, ASN de IXP removido, e o caminho é descartado
se tiver laço (ASN repetido sem ser adjacente: *poisoning* ou erro), ASN reservado/privado/AS_TRANS ou menos de 2 saltos."""
from __future__ import annotations

from typing import Iterable, Optional

from products.as_relationships.config import Config


def invalido(asn: int, cfg: Config) -> bool:
    return any(lo <= asn <= hi for lo, hi in cfg.descartar_asn)


def sanitizar(caminho: Iterable[int], cfg: Config) -> Optional[tuple[int, ...]]:
    """Caminho limpo ou None (descartado)."""
    out: list[int] = []
    for a in caminho:
        if a in cfg.asns_ixp:
            continue
        if invalido(a, cfg):
            return None
        if out and out[-1] == a:
            continue
        out.append(a)
    if len(out) < 2 or len(set(out)) != len(out):
        return None
    return tuple(out)
