# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Download único do CSV nacional de outorgas da Anatel (fonte `anatel_outorgas`).

Grava `raw/{date}/summary/anatel-outorgas-{date}.csv.gz`. SCM, SMP, STFC e SeAC (fontes derivadas) leem este arquivo; se
ele não existir, o primeiro deles o baixa.

Uso:
    python -m sources.anatel_outorgas.collect --date 2026-10-24
"""
from __future__ import annotations

import argparse
import sys

from core.common import configure_logging, data_dir, today_str
from sources.anatel_outorgas.download import ANATEL_URL, obter_csv


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Download único do CSV de outorgas da Anatel")
    p.add_argument("--date", default=today_str())
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        obter_csv(a.date, data_dir(), log, ANATEL_URL)
    except Exception:
        log.exception("falha no download das outorgas da Anatel")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
