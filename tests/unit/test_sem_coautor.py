# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — nenhum commit leva `Co-Authored-By`: a autoria é do mantenedor (ferramentas e agentes não entram como coautores).

Percorre o histórico inteiro (a CI faz o checkout com `fetch-depth: 0`). A única exceção é o commit já publicado que saiu com a linha
antes desta regra; reescrever o histórico mudaria o hash de todas as versões seguintes.
"""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
JA_PUBLICADOS = {"bc4e3511219c85a21ea53b044def1953f59d732e"}   # 2.0.1 (implantação rootless), 2026-11-19
_COAUTOR = re.compile(r"^\s*co-authored-by\s*:", re.I | re.M)


def _commits() -> list[tuple[str, str]]:
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "log", "--format=%H%x00%B%x1e"], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("sem histórico git (cópia sem .git)")
    return [tuple(c.strip("\n").split("\x00", 1)) for c in r.stdout.split("\x1e") if "\x00" in c]


def test_nenhum_commit_com_co_authored_by():
    try:
        raso = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--is-shallow-repository"], capture_output=True, text=True).stdout.strip()
    except OSError:
        pytest.skip("git ausente")
    if raso == "true":
        pytest.skip("checkout raso: a CI usa fetch-depth: 0")
    achados = [h[:12] for h, corpo in _commits() if _COAUTOR.search(corpo) and h not in JA_PUBLICADOS]
    assert achados == [], f"commits com Co-Authored-By (a autoria é só do mantenedor): {achados}"
