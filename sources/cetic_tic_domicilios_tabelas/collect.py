# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cetic.br: TIC Domicílios — tabelas oficiais.

Fonte:       https://cetic.br/pt/pesquisa/domicilios/microdados/ (a página lista o ZIP de tabelas XLSX da edição vigente; não há API)
Bruto:       data/raw/{date}/summary/<arquivo da edição>.zip (byte a byte)
Normalizado: data/normalized/{date}/summary/cetic_tic_domicilios.json.gz   {edicao, fonte, licenca, url, sha256, tabelas: {aba: {...}}, linhas: [...]} em formato longo
Detalhes do formato e da descoberta: core/cetic.py.

Uso:
    python -m sources.cetic_tic_domicilios_tabelas.collect --date 2026-11-01
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.cetic import run_pesquisa
from core.common import configure_logging, data_dir, today_str

PESQUISA, PREFIXO, SAIDA, ROTULO, MINIMO_TABELAS = "domicilios", "tic_domicilios", "cetic_tic_domicilios", "TIC Domicílios", 10


def run(date_str: str, base: Path, log, **kw) -> dict:
    return run_pesquisa(PESQUISA, PREFIXO, SAIDA, ROTULO, MINIMO_TABELAS, date_str, base, log, **kw)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="TIC Domicílios (Cetic.br)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log))
    except Exception:
        log.exception("falha na coleta de cetic_tic_domicilios_tabelas")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
