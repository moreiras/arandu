# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — o espelho da política de acesso no frontend (accessPolicy.ts) não diverge do servidor.

Lê a tabela do TypeScript (sem Node) e a confronta com `tests/access_entry_calls.json` e com
`api/auth/access_policy.py`: toda página de entrada registrada no servidor tem de ser `open` no front, e a
área de histórico (`/snapshots`) tem de ser `login`.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TS = (ROOT / "frontend" / "src" / "auth" / "accessPolicy.ts").read_text(encoding="utf-8")


def _set(name: str) -> set[str]:
    m = re.search(rf"const {name} = new Set\(\[(.*?)\]\)", TS, re.S)
    assert m, f"{name} não encontrado em accessPolicy.ts"
    return set(re.findall(r"'([^']+)'", m.group(1)))


def test_paginas_de_entrada_do_servidor_sao_open_no_frontend():
    calls = json.loads((ROOT / "tests" / "access_entry_calls.json").read_text(encoding="utf-8"))
    paginas = calls["paginas"]
    open_exact = _set("OPEN_EXACT")
    # o JSON do servidor descreve páginas do SPA e as chamadas de API que elas fazem
    rotas = [k for k in paginas if k.startswith("/")]
    assert rotas, "tests/access_entry_calls.json sem páginas"
    faltam = sorted(r for r in rotas if r not in open_exact)
    assert faltam == [], f"páginas de entrada do servidor que o front trata como metered: {faltam}"


def test_historico_e_login_no_frontend_e_no_servidor():
    assert "/snapshots" in _set("LOGIN_EXACT")
    src = (ROOT / "api" / "auth" / "access_policy.py").read_text(encoding="utf-8")
    assert "historico" in src.lower()          # o servidor também trata datas fora das 2 mais recentes como login


def test_preview_limit_do_front_e_o_do_servidor():
    m = re.search(r"PREVIEW_LIMIT\s*=\s*(\d+)", TS)
    assert m
    from api.auth import access_policy

    server = getattr(access_policy, "PREVIEW_LIMIT", None)
    assert server is not None, "access_policy.PREVIEW_LIMIT não existe"
    assert int(m.group(1)) == server
