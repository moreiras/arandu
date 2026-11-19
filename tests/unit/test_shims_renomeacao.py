# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — atalhos da renomeação de pastas: os nomes antigos continuam funcionando."""
import importlib
import importlib.util
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("codemod", ROOT / "scripts" / "codemod_1_2_2.py")
codemod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(codemod)

PARES = []
for fase, mv in (("core", codemod.CORE), ("products", codemod.PRODUCTS)):
    PARES += [(codemod.modulo(a), codemod.modulo(b)) for a, b in mv.items()]
# `sources` já foi movido: o mapa vem dos próprios atalhos que ficaram nas pastas antigas
for pasta, arq in (("collector", "collect"), ("enrich", "enrich")):
    for f in sorted((ROOT / pasta).glob("*.py")):
        if f.stem.startswith("_") or f.stem == "__init__":
            continue
        PARES.append((f"{pasta}.{f.stem}", f"sources.{f.stem}.{arq}"))


def test_mapa_cobre_todos_os_modulos_movidos():
    assert len(PARES) == 2 + 5 + 34


@pytest.mark.parametrize("antigo, novo", PARES, ids=[p[0] for p in PARES])
def test_nome_antigo_e_o_mesmo_modulo_que_o_novo(antigo, novo):
    sys.modules.pop(antigo, None)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        velho = importlib.import_module(antigo)
    assert velho is importlib.import_module(novo)
    assert any(issubclass(x.category, DeprecationWarning) and novo in str(x.message) for x in w)


def test_python_m_com_o_nome_antigo_ainda_executa_o_modulo_novo():
    for antigo in ("collector.lg_ixbr", "analysis.metrics", "enrich.rdap"):
        r = subprocess.run([sys.executable, "-W", "ignore", "-m", antigo, "--help"], cwd=ROOT, capture_output=True, text=True, timeout=60)
        assert r.returncode == 0 and "usage" in r.stdout.lower(), (antigo, r.stderr[-300:])


def test_nenhum_codigo_vivo_importa_pelos_nomes_antigos():
    import re

    ruins = []
    for pasta in ("api", "mcp_server", "arandu", "core", "publish", "sources", "products", "scripts", "tests"):
        for f in (ROOT / pasta).rglob("*.py"):
            if f.name == "codemod_1_2_2.py" or f.name == "test_shims_renomeacao.py":
                continue
            for n, l in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if re.match(r"\s*(from|import)\s+(collector|enrich|analysis)(\.| import|\s*$)", l):
                    ruins.append(f"{f.relative_to(ROOT)}:{n}: {l.strip()}")
    assert ruins == []
