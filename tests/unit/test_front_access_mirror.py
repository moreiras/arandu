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


def test_ptt_externo_nao_exige_login_no_servidor_nem_no_frontend():
    """PT-12b (revisão da D9, 2026-11-25): `/external-ixps/{code}` (API) e `/ixp-externo/:code` (SPA) são `metered`; a lista de PTTs externos continua aberta."""
    assert "LOGIN_PREFIX" not in TS and "externo" not in _set("LOGIN_EXACT")
    from api.auth.access_policy import METERED, OPEN, classify
    assert classify("GET", "/api/v1/external-ixps/decix-rj", {}, ["2026-11-15"]).cls == METERED
    assert classify("GET", "/api/v1/ixp-compare/members", {"ixps": "ixbr:sp,ext:decix-rj"}, ["2026-11-15"]).cls == METERED
    assert classify("GET", "/api/v1/external-ixps", {}, ["2026-11-15"]).cls == OPEN
    main = (ROOT / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    assert re.search(r'path="ixp-externo/:code" element=\{<P>', main)             # a rota existe e passa pela porta de acesso


def test_snapshots_da_entrada_nao_chamam_a_rota_login():
    """D9: as páginas abertas usam `/brasil/snapshots`; `/snapshots` (lista inteira) só com login. O frontend não chama `/api/v1/snapshots` sem ser pela lista completa."""
    api = (ROOT / "frontend" / "src" / "services" / "api.ts").read_text(encoding="utf-8")
    assert "get(completo ? '/api/v1/snapshots' : '/api/v1/brasil/snapshots')" in api and "get(`/api/v1/brasil/snapshots/${date}`" in api      # a chamada leva `esquema` (PT-16), então o parêntese não fecha logo
    calls = json.loads((ROOT / "tests" / "access_entry_calls.json").read_text(encoding="utf-8"))
    for pagina, urls in calls["paginas"].items():
        assert not any(u.startswith("/api/v1/snapshots") for u in urls), (pagina, "chama a rota login /snapshots")


def test_preview_limit_do_front_e_o_do_servidor():
    m = re.search(r"PREVIEW_LIMIT\s*=\s*(\d+)", TS)
    assert m
    from api.auth import access_policy

    server = getattr(access_policy, "PREVIEW_LIMIT", None)
    assert server is not None, "access_policy.PREVIEW_LIMIT não existe"
    assert int(m.group(1)) == server


def test_rota_medida_do_spa_passa_pelo_protectedroute():
    """Toda rota do SPA que o espelho classifica como `metered` passa pelo `<P>` (ProtectedRoute): sem ele, com o orçamento anônimo
    esgotado, a página chama a API e recebe 403 (`/grupo/:id` mostrava "não encontrado"). Redirecionamentos não renderizam nada."""
    main = (ROOT / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    abertas, login = _set("OPEN_EXACT"), _set("LOGIN_EXACT")
    sem_porta = []
    for caminho, elemento in re.findall(r'<Route\s+path="([^"]+)"\s+element=\{(.*?)\}\s*/>', main):
        if caminho == "*":
            # rota curinga (página "não encontrada"): não chama a API ao abrir; passar pelo <P> mostraria o aviso de orçamento
            # esgotado no lugar do 404
            continue
        pagina = "/" + re.sub(r":[^/]+|\*", "x", caminho)
        if pagina in abertas or pagina in login:
            continue
        if "<P>" in elemento or "Navigate" in elemento or "Redireciona" in elemento:
            continue
        sem_porta.append(caminho)
    assert sem_porta == [], f"rotas metered sem <P> em main.tsx: {sem_porta}"
