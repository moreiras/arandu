#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Valida o catálogo (o mesmo que `arandu catalog validate`).

Uso: python3 scripts/catalog_validate.py [--root DIR] [--json]
Código de saída 1 se houver erro. `nao_verificado` não é erro: é contado como tarefa aberta.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.catalog.loader import load_catalog, nao_verificados, validate  # noqa: E402


def medir(cat) -> dict:
    campos = [c for s in cat.sources.values() for c in s.campos] + \
             [c for p in cat.products.values() for c in p.campos]
    return {
        "fontes": len(cat.sources),
        "produtos": len(cat.products),
        "campos": len(campos),
        "campos_com_significado": sum(1 for c in campos if c.significado.strip()
                                      and c.significado.strip() != "nao_verificado"),
        "nao_verificado": sum(nao_verificados(x) for x in [*cat.sources.values(), *cat.products.values()]),
        "publicavel_false": sorted(s.id for s in cat.sources.values() if not s.publicavel),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=None, help="diretório catalog/ (padrão: o do repositório)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    cat = load_catalog(args.root)
    erros = validate(cat)
    m = medir(cat)
    if args.json:
        print(json.dumps({"erros": erros, **m}, ensure_ascii=False, indent=2))
    else:
        for e in erros:
            print(f"ERRO: {e}", file=sys.stderr)
        print(f"catálogo: {m['fontes']} fontes, {m['produtos']} produtos, {m['campos']} campos "
              f"({m['campos_com_significado']} com significado), {m['nao_verificado']} nao_verificado, "
              f"{len(erros)} erro(s)")
    return 1 if erros else 0


if __name__ == "__main__":
    raise SystemExit(main())
