# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Privacidade da chave de MCP: nenhum arquivo versionado (contratos, fixtures, docs, código) contém uma chave de MCP real.

O padrão é `arandu_mcp_<8>_<52+>` em base32. Os testes que precisam de uma chave a montam em memória ou usam o valor de mentira de `tests/unit/test_mcp_chave.py`
(montado por concatenação, para o texto do arquivo não casar com o padrão).
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
PADRAO = re.compile(rb"arandu_mcp_[A-Z2-7]{8}_[A-Z2-7]{40,}")
ISENTOS: set[str] = set()


@pytest.mark.skipif(shutil.which("git") is None, reason="lista os arquivos por `git ls-files`; sem o git (python:3.12-slim do ci.sh --docker) não há o que varrer")
def test_nenhum_arquivo_versionado_tem_chave_de_mcp():
    arquivos = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.splitlines()
    achados = []
    for rel in arquivos:
        p = RAIZ / rel
        if rel in ISENTOS or not p.is_file() or p.stat().st_size > 5_000_000:
            continue
        if PADRAO.search(p.read_bytes()):
            achados.append(rel)
    assert achados == []
