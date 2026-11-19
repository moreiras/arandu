# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Leitor mínimo de planilhas XLSX (Office Open XML) só com a biblioteca padrão.

Lê o que as tabelas do Cetic.br usam: abas nomeadas, texto compartilhado e números. Não interpreta fórmulas, estilos nem datas. Existe para não
acrescentar `openpyxl` (e suas dependências) à imagem de produção por causa de uma fonte anual.
"""
from __future__ import annotations

import io
import re
import zipfile
import xml.etree.ElementTree as ET

_M = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _coluna(ref: str) -> int:
    n = 0
    for c in re.match(r"[A-Z]+", ref).group():
        n = n * 26 + ord(c) - 64
    return n - 1


def _texto(no) -> str:
    return "".join(t.text or "" for t in no.iter(f"{{{_M}}}t"))


def ler_xlsx(conteudo: bytes) -> dict[str, list[list[str | None]]]:
    """{nome da aba: linhas}, cada linha uma lista de texto (ou None onde a célula está vazia); números vêm como texto, sem conversão."""
    z = zipfile.ZipFile(io.BytesIO(conteudo))
    comp: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        comp = [_texto(si) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(f"{{{_M}}}si")]
    alvo = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    abas: dict[str, list[list[str | None]]] = {}
    for s in ET.fromstring(z.read("xl/workbook.xml")).find(f"{{{_M}}}sheets"):
        caminho = alvo[s.get(f"{{{_R}}}id")].lstrip("/")
        caminho = caminho if caminho.startswith("xl/") else "xl/" + caminho
        linhas: list[list[str | None]] = []
        for r in ET.fromstring(z.read(caminho)).iter(f"{{{_M}}}row"):
            celulas: dict[int, str | None] = {}
            for c in r.findall(f"{{{_M}}}c"):
                v = c.find(f"{{{_M}}}v")
                if v is not None:
                    celulas[_coluna(c.get("r"))] = comp[int(v.text)] if c.get("t") == "s" else v.text
                elif c.find(f"{{{_M}}}is") is not None:
                    celulas[_coluna(c.get("r"))] = _texto(c.find(f"{{{_M}}}is"))
            linhas.append([celulas.get(i) for i in range(max(celulas) + 1)] if celulas else [])
        abas[s.get("name")] = linhas
    return abas
