# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Coleta diária do grupo `lacnic_listas`. O código comum está em `core/listas_numeracao.py`.

Uso:
    python -m sources.lacnic_listas.collect --date 2026-10-23
"""
from __future__ import annotations

import argparse
import sys

from core.common import configure_logging, data_dir, today_str
from core.listas_numeracao import run

GRUPO = "lacnic_listas"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Listas diárias de numeração: lacnic_listas")
    p.add_argument("--date", default=today_str())
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        run(GRUPO, a.date, data_dir(), log)
    except Exception:
        log.exception("falha na coleta das listas")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
