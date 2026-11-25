# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PT-22 (uso-da-internet 5.2): as células que a síntese do topo de /uso-da-internet cita existem nas planilhas oficiais da edição.

`frontend/src/features/cetic/temasSintese.json` lista as células por igualdade em tabela, dimensão, recorte, item e resposta. Se uma edição nova mudar o nome de
uma tabela ou de uma resposta, a frase some na tela sem erro; este teste, sobre as planilhas reais do repositório, falha de modo visível para alguém ajustar o JSON.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.cetic import normalizar

RAIZ = Path(__file__).resolve().parents[2]
FIXTURES = RAIZ / "tests" / "fixtures" / "raw" / "cetic"
TEMAS = json.loads((RAIZ / "frontend" / "src" / "features" / "cetic" / "temasSintese.json").read_text(encoding="utf-8"))
ZIPS = {
    "domicilios": FIXTURES / "tic_domicilios_2025_domicilios_tabelas_xlsx_v1.0.zip",
    "provedores": FIXTURES / "tic_provedores_2024_tabela_xlsx_v1.0.zip",
}


@pytest.fixture(scope="module")
def linhas() -> dict[str, list[dict]]:
    return {p: normalizar(z.read_bytes(), 1)[1] for p, z in ZIPS.items()}


@pytest.mark.parametrize("pesquisa", ["domicilios", "provedores"])
def test_toda_celula_citada_pela_sintese_existe_na_planilha(pesquisa, linhas):
    ausentes = []
    for t in TEMAS[pesquisa]:
        achada = [l for l in linhas[pesquisa] if all(l[k] == t[k] for k in ("tabela", "dimensao", "recorte", "item", "resposta"))]
        if len(achada) != 1 or achada[0]["proporcao"] is None:
            ausentes.append((t["id"], len(achada)))
    assert not ausentes, f"células da síntese que não casam uma a uma com a planilha de {pesquisa}: {ausentes}"


def test_valores_conferidos_com_a_planilha_oficial(linhas):
    """Os números do relatório de análise (A4 total 86,3047 ±0,798; A5 banda larga fixa 76,36 ±1,295; E1A 34,4067 ±2,4763) são os das planilhas."""
    def valor(pesquisa, tema_id):
        t = next(x for x in TEMAS[pesquisa] if x["id"] == tema_id)
        l = next(l for l in linhas[pesquisa] if all(l[k] == t[k] for k in ("tabela", "dimensao", "recorte", "item", "resposta")))
        return l["proporcao"], l["margem_proporcao"]
    assert valor("domicilios", "a4") == (86.3047, 0.798)
    assert valor("domicilios", "a5_banda_larga_fixa") == (76.36, 1.295)
    assert valor("provedores", "e1a") == (34.4067, 2.4763)
    assert valor("provedores", "c1") == (43.61, 0.0)
