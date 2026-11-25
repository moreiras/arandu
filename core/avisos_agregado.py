# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Avisos dos agregados por UF, município e porte (prontidão, ROV, MANRS, HHI): nada é suprimido, o leitor vê quantos casos e o peso do maior.

Política editorial (D6): nenhum piso esconde linha. Cada recorte traz `n_asns_com_dado` (ou os acessos, no HHI) e `peso_top1` (parcela do maior integrante
no recorte, 0 a 1), e `avisos` diz só o que está à vista: `poucos_casos` (menos de `MIN_CASOS`) e `maior_integrante` (um integrante pesa `PESO_AVISO` ou mais).
O aviso é rótulo: não muda o valor, a ordem nem a presença do recorte.
"""
from __future__ import annotations

from typing import Iterable, Optional

MIN_CASOS = 5
PESO_AVISO = 0.30

TEXTO = {
    "poucos_casos": f"menos de {MIN_CASOS} casos no recorte",
    "maior_integrante": f"um integrante pesa {round(PESO_AVISO * 100)}% ou mais do recorte",
}


def peso_top1(pesos: Iterable[float]) -> Optional[float]:
    """Parcela do maior peso no total (0 a 1, 3 casas); `None` sem peso algum."""
    ps = [p for p in pesos if p]
    total = sum(ps)
    return round(max(ps) / total, 3) if total else None


def avisos(n: int, peso: Optional[float] = None, *, com_peso: bool = True) -> list[str]:
    """Códigos dos avisos do recorte. `com_peso=False` ignora o peso do maior (HHI: a parcela do líder é parte da própria medida e fica à vista)."""
    out = []
    if n < MIN_CASOS:
        out.append("poucos_casos")
    if com_peso and peso is not None and peso >= PESO_AVISO:
        out.append("maior_integrante")
    return out
