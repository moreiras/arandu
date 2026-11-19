# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Gera o dataset sintético (Arandurápolis) JÁ PUBLICADO: raw → normalized → published (`bgp_ixp` → `saude_asn`).

    python -m tests.synth.publish --out DIR [--seed 1]

Serve para subir a API real sobre dados sintéticos fora do pytest (E2E no CI, desenvolvimento local):

    DATA_DIR=DIR uvicorn api.main:app --port 8000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tests.synth.generate import generate
from tests.synth.world import T0, T1


def publish(out: Path, seed: int = 1, extra_asns: int = 0) -> list[str]:
    import pytest

    from tests.products.conftest import run_pipeline

    generate(out, seed=seed, extra_asns=extra_asns)
    with pytest.MonkeyPatch.context() as mp:
        for d in (T0, T1):
            run_pipeline(out, d, mp)
    return [T0, T1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--extra-asns", type=int, default=0,
                    help="ASNs BR genéricos a mais (escala); o E2E precisa de > 100 para ter lista paginada")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        print(f"ERRO: {out} não está vazio", file=sys.stderr)
        return 1
    dates = publish(out, a.seed, a.extra_asns)
    print(f"publicado: {', '.join(dates)} em {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
