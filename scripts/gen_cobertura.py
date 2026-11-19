#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Matriz de cobertura API × MCP × interface: grava `docs/cobertura.md`.

    python3 scripts/gen_cobertura.py          # regrava
    python3 scripts/gen_cobertura.py --check  # só confere: código 1 se a matriz está desatualizada ou há lacuna sem justificativa
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DESTINO = ROOT / "docs" / "cobertura.md"


def levantar() -> tuple[list, list[str], str]:
    """(linhas da matriz, erros de consistência, markdown)."""
    import re

    from api import deprecation
    from api.main import app
    from api.query import COLLECTIONS
    from core import cobertura
    from core.capacidades import carregar_todas
    from mcp_server.app import mcp

    spec = app.openapi()
    ops = [(m.upper(), p[len("/api/v1"):], bool(deprecation.sucessor(re.sub(r"\{[^}]+\}", "1", p)))) for p, item in spec["paths"].items()
           if p.startswith("/api/v1") for m, op in item.items() if isinstance(op, dict)]
    visiveis = {t.name for t in asyncio.run(mcp.list_tools())}
    tools = visiveis | set(mcp.ocultas)               # alias oculto ainda atende a rota enquanto não for removido
    linhas, erros = cobertura.montar(ops, cobertura.codigo_do_frontend())
    erros += cobertura.validar_tools(linhas, tools, set(COLLECTIONS))
    geradas = sum(1 for c in carregar_todas() for o in c.operacoes if o.mcp)
    return linhas, erros, cobertura.para_markdown(linhas, geradas, len(visiveis))


def main(argv: list[str]) -> int:
    linhas, erros, md = levantar()
    lacunas = [f"{l.rota}: sem justificativa em {', '.join(l.lacunas)}" for l in linhas if l.lacunas]
    for e in erros + lacunas:
        print("erro:", e, file=sys.stderr)
    if "--check" in argv:
        atual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
        if atual != md:
            print("docs/cobertura.md desatualizado: rode python3 scripts/gen_cobertura.py", file=sys.stderr)
        return 0 if not (erros or lacunas) and atual == md else 1
    DESTINO.write_text(md, encoding="utf-8")
    print(f"gravado {DESTINO.relative_to(ROOT)} ({len(linhas)} rotas)")
    return 1 if erros or lacunas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
