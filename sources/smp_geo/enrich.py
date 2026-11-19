# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`smp_geo` — Geolocalização de outorgas SMP via Nominatim.

Entrada:  normalized/{date}/summary/anatel_smp.json.gz   (`anatel_smp`)
Saída:    normalized/{date}/summary/anatel_smp_geo.json.gz

Cache:    data/normalized/geo_cache/smp.json.gz  (persiste entre snapshots)

Mesma lógica de sources/scm_geo/enrich.py (`scm_geo`), só troca a fonte/cache/saída para SMP.
Universo pequeno (~30 CNPJs) — o custo de geocodificação é desprezível frente ao
de SCM.

Estratégias de geocodificação (ordem decrescente de confiança):
  1. logradouro + número + município + UF  →  geo_confidence: exact_address
  2. CEP                                   →  geo_confidence: cep_centroid
  3. município + UF                        →  geo_confidence: city_centroid
  4. sem resultado                         →  geo_confidence: unknown

Uso (código comum em sources/anatel_outorgas/geo.py):
    python -m sources.smp_geo.enrich --date 2026-06-24
    python -m sources.smp_geo.enrich --date 2026-06-24 --force
"""

from __future__ import annotations

import sys
from pathlib import Path

from sources.anatel_smp.collect import SERVICO
from sources.anatel_outorgas import geo as _geo
from sources.anatel_outorgas.geo import main_geo


def run(date_str: str, base: Path, force: bool, log) -> dict:
    return _geo.rodar(SERVICO, date_str, base, force, log)


def main(argv: list[str] | None = None) -> int:
    return main_geo(SERVICO, "smp_geo", argv)


if __name__ == "__main__":
    sys.exit(main())
