# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Faixas do ROV medido pelo APNIC por ASN: regra única do produto `seguranca` (agregados) e do Mapa Explorer (`color_by="rov"`)."""
from typing import Optional

MIN_AMOSTRAS = 100                       # abaixo disso o percentual do APNIC é instável e não entra nos agregados
FAIXAS_ROV = ((10.0, "ate_10"), (90.0, "de_10_a_90"))      # percentual até 10, de 10 a 90 e acima de 90 (valida)


def faixa_pct(v: float) -> str:
    return "ate_10" if v <= FAIXAS_ROV[0][0] else "de_10_a_90" if v <= FAIXAS_ROV[1][0] else "acima_de_90"


def faixa_rov(rov: Optional[dict]) -> str:
    """Faixa do ROV de um ASN: `sem_dado` sem medição, `amostra_insuficiente` abaixo de `MIN_AMOSTRAS`, senão a faixa do percentual."""
    if not rov or rov.get("validates_pct") is None:
        return "sem_dado"
    if (rov.get("amostras") or 0) < MIN_AMOSTRAS:
        return "amostra_insuficiente"
    return faixa_pct(rov["validates_pct"])
