# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Textos que afirmavam o que o dado não mede não voltam ao código.

Cada entrada é um texto que já esteve na interface, na API ou na documentação e descrevia outra coisa que o dado (data fixa de
início do histórico, persistência que não vale para todos os tipos, rótulo de contagem com outra origem…). A busca é textual nos
fontes, fora dos arquivos de teste, que podem citar o texto antigo para provar que ele sumiu.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
EXTS = {".ts", ".tsx", ".py", ".md", ".yaml", ".yml"}

# (expressão, onde procurar, motivo)
PROIBIDOS: list[tuple[str, tuple[str, ...], str]] = [
    (r"outubro de 2026|começou a ser guardado em 2026-10",
     ("frontend/src",), "TRANSV-E7: a data inicial vem da lista de snapshots"),
    (r"persistiu por mais de um",
     ("frontend/src",), "MUD-E1: tipos de janela 1 nascem confirmados"),
]


def _fontes(pastas: tuple[str, ...]):
    for pasta in pastas:
        base = RAIZ / pasta
        arquivos = [base] if base.is_file() else base.rglob("*")
        for p in arquivos:
            if p.suffix not in EXTS or not p.is_file() or "node_modules" in p.parts:
                continue
            if ".test." in p.name or p.name.startswith("test_"):
                continue
            yield p


@pytest.mark.parametrize("expr,pastas,motivo", PROIBIDOS, ids=[m.split(":")[0] for _, _, m in PROIBIDOS])
def test_texto_antigo_nao_volta(expr, pastas, motivo):
    rx = re.compile(expr, re.IGNORECASE)
    achados = []
    for p in _fontes(pastas):
        for n, linha in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if rx.search(linha):
                achados.append(f"{p.relative_to(RAIZ)}:{n}: {linha.strip()[:120]}")
    assert not achados, f"{motivo}\n" + "\n".join(achados)


def test_janelas_de_confirmacao_conferem_com_o_texto_de_mudancas():
    """O "Como ler" de /mudancas enumera os tipos confirmados no snapshot em que aparecem; mudou a janela, revise o texto."""
    from products.history.eventos import TIPOS
    janela_1 = {t for t, (janela, _) in TIPOS.items() if janela == 1}
    assert janela_1 == {"ixp_entrada", "ixp_saida", "roa_ganho", "roa_perdido", "aspa_ganho", "aspa_perdido", "outorga_nova"}
    texto = (RAIZ / "frontend/src/pages/MudancasPage.tsx").read_text(encoding="utf-8")
    assert "entradas e saídas do cadastro de PTTs, ROAs ganhos ou perdidos, ASPA e outorgas novas" in texto
