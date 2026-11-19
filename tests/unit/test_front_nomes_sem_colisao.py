# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Nenhum módulo do frontend difere de outro só por maiúsculas (`Destaques.tsx` × `destaques.ts`).

No macOS (sistema de arquivos sem distinção de caixa) `import … from './Destaques'` resolve para `destaques.ts`, que vem antes de
`.tsx` na ordem do TypeScript, e o build quebra; no Linux passa.
"""
from __future__ import annotations

import os
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
EXTS = (".ts", ".tsx", ".js", ".jsx")


def _modulo(nome: str) -> str:
    """`Destaques.test.tsx` → `destaques.test`; `destaques.ts` → `destaques`."""
    for e in EXTS:
        if nome.endswith(e):
            return nome[: -len(e)].lower()
    return ""


def test_modulos_do_frontend_nao_colidem_por_maiusculas():
    colisoes = []
    for raiz, _, arquivos in os.walk(SRC):
        vistos: dict[str, str] = {}
        for nome in sorted(arquivos):
            m = _modulo(nome)
            if not m:
                continue
            if m in vistos:
                colisoes.append(f"{Path(raiz).relative_to(SRC)}: {vistos[m]} × {nome}")
            else:
                vistos[m] = nome
    assert colisoes == [], "módulos que só diferem por maiúsculas (quebram o build no macOS): " + "; ".join(colisoes)
