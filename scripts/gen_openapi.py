#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Grava o OpenAPI da API em `frontend/src/types/openapi.json`.

É a entrada do `openapi-typescript` (`scripts/front-test.sh --gen-tipos` gera `frontend/src/types/openapi.gen.ts`). O teste
`tests/unit/test_openapi_snapshot.py` falha quando o arquivo está desatualizado em relação às rotas.

    python3 scripts/gen_openapi.py          # regrava
    python3 scripts/gen_openapi.py --check  # só confere (código 1 se diferente)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DESTINO = ROOT / "frontend" / "src" / "types" / "openapi.json"


def gerar() -> str:
    from api.main import app
    return json.dumps(app.openapi(), ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main(argv: list[str]) -> int:
    novo = gerar()
    if "--check" in argv:
        return 0 if DESTINO.exists() and DESTINO.read_text(encoding="utf-8") == novo else 1
    DESTINO.write_text(novo, encoding="utf-8")
    print(f"gravado {DESTINO.relative_to(ROOT)} ({len(novo) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
