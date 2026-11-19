#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Verificação pós-implantação: confere uma instância já no ar, SOMENTE LEITURA.

    python3 scripts/post_deploy_check.py [--base https://exemplo.example] [--expect-version 1.1.5]
                                         [--mcp-tools N] [--json]

Verifica: `/health` (status ok e versão esperada), rotas-chave da API (200 + JSON com os campos de topo),
privacidade (contatos exigem login), MCP (initialize + tools/list com as tools-chave, sem a de contatos,
mesma contagem do contrato) e páginas de fumaça do frontend. Código de saída 1 se algo falhar.
Só faz GET e o handshake de leitura do MCP; nada é escrito na instância.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
UA = "arandurape-post-deploy-check/1"

ROTAS = [   # (caminho, campos de topo obrigatórios)
    ("/api/v1/snapshots", ["snapshots", "latest"]),
    ("/api/v1/ixps", ["ixps", "snapshot_date"]),
    ("/api/v1/asns?limit=1", ["items", "total", "snapshot_date"]),
    ("/api/v1/cdns/presence", ["cdns"]),
    ("/api/v1/schema", ["collections"]),
    ("/api/v1/acessos/stats", ["total_acessos"]),
    ("/api/v1/rpki/summary", ["br_asns_total"]),
]
TOOLS_CHAVE = ["historico_snapshots", "asn_detalhe", "ixp_detalhe", "query", "describe_schema", "ixp_lista", "operadora_ranking"]   # nomes por domínio
PAGINAS = ["/", "/privacidade", "/ixps", "/asns"]       # SPA: todas devolvem o index.html


Transport = Callable[[str, str, dict | None, dict | None], tuple[int, dict, bytes]]


def http(base: str) -> Transport:
    def call(method: str, path: str, body: dict | None = None, headers: dict | None = None):
        req = urllib.request.Request(base.rstrip("/") + path, method=method, headers={"User-Agent": UA, **(headers or {})},
                                     data=json.dumps(body).encode() if body is not None else None)
        if body is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()
    return call


def _json(body: bytes):
    try:
        return json.loads(body)
    except ValueError:
        return None


def _mcp_body(body: bytes):
    """Resposta do MCP: JSON puro ou SSE (`data: {...}`)."""
    text = body.decode("utf-8", "replace").strip()
    if text.startswith("{"):
        return _json(text.encode())
    for line in text.splitlines():
        if line.startswith("data:"):
            return _json(line[5:].strip().encode())
    return None


def run_checks(call: Transport, expect_version: str, mcp_tools: int | None) -> list[dict]:
    out: list[dict] = []

    def add(nome: str, ok: bool, detalhe: str = "") -> None:
        out.append({"check": nome, "ok": bool(ok), "detalhe": detalhe})

    st, _, body = call("GET", "/health", None, None)
    h = _json(body) or {}
    add("health", st == 200 and h.get("status") == "ok", f"status={st} {h}")
    add("versão exposta", h.get("version") == expect_version, f"/health={h.get('version')} esperado={expect_version}")
    latest = h.get("latest_snapshot")
    add("snapshot mais recente", bool(latest), str(latest))

    for path, keys in ROTAS:
        st, hd, body = call("GET", path, None, {"X-Arandu-Area": "post-deploy"})
        j = _json(body)
        faltam = [k for k in keys if not isinstance(j, dict) or k not in j]
        add(f"rota {path}", st == 200 and not faltam, f"status={st}" + (f" faltam={faltam}" if faltam else ""))

    if latest:
        st, _, body = call("GET", f"/api/v1/snapshots/{latest}", None, None)
        j = _json(body) or {}
        manifest = (j.get("manifest") or {}) if isinstance(j, dict) else {}
        add("manifesto do snapshot", st == 200 and manifest.get("pipeline_version"), f"status={st}")
        if "coleta_ok" in manifest and manifest.get("coleta_ok") is not None:
            add("sanidade de coleta", manifest.get("coleta_ok") is True,
                f"coleta={manifest.get('coleta')} falhas={[k for k, v in (manifest.get('checks') or {}).items() if v.get('status') == 'falha']}")

    st, _, _ = call("GET", "/api/v1/asns/1251/contacts", None, None)
    add("privacidade: contatos exigem login", st in (401, 403), f"status={st}")

    # MCP (handshake de leitura)
    hdr = {"Accept": "application/json, text/event-stream"}
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "post-deploy-check", "version": "1"}}}
    st, rh, body = call("POST", "/mcp", init, hdr)
    r = _mcp_body(body) or {}
    add("mcp initialize", st == 200 and "result" in r, f"status={st}")
    sid = next((v for k, v in rh.items() if k.lower() == "mcp-session-id"), None)
    if sid:
        hdr["Mcp-Session-Id"] = sid
    call("POST", "/mcp", {"jsonrpc": "2.0", "method": "notifications/initialized"}, hdr)
    st, _, body = call("POST", "/mcp", {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, hdr)
    r = _mcp_body(body) or {}
    nomes = [t["name"] for t in (r.get("result") or {}).get("tools", [])]
    add("mcp tools/list", st == 200 and bool(nomes), f"{len(nomes)} tools")
    faltam = [t for t in TOOLS_CHAVE if t not in nomes]
    add("mcp tools-chave", not faltam, f"faltam={faltam}" if faltam else "ok")
    add("mcp sem tool de contatos", not [n for n in nomes if "contact" in n], "")
    if mcp_tools is not None:
        add("mcp nº de tools = contrato", len(nomes) == mcp_tools, f"{len(nomes)} (contrato: {mcp_tools})")

    for p in PAGINAS:
        st, hd, body = call("GET", p, None, None)
        html = body.decode("utf-8", "replace")
        add(f"página {p}", st == 200 and '<div id="root"' in html.replace("'", '"'), f"status={st}")
    return out


def contract_tools() -> int | None:
    try:
        return len(json.loads((ROOT / "tests" / "contracts" / "mcp_contract.json").read_text())["tools"])
    except (OSError, ValueError, KeyError):
        return None


def _site_url() -> str | None:
    """`SITE_URL` do ambiente ou, como no restart-safe.sh, do `.env` da raiz (o script roda fora do contêiner)."""
    if os.environ.get("SITE_URL", "").strip():
        return os.environ["SITE_URL"].strip()
    try:
        linhas = (ROOT / ".env").read_text().splitlines()
    except OSError:
        return None
    valores = [ln.split("=", 1)[1].strip().strip('"\'') for ln in linhas if ln.startswith("SITE_URL=")]
    return valores[-1] if valores and valores[-1] else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    padrao = _site_url()
    ap.add_argument("--base", default=padrao, required=not padrao,
                    help="URL pública da instância (padrão: SITE_URL do ambiente ou do .env)")
    ap.add_argument("--expect-version", default=None, help="padrão: conteúdo do arquivo VERSION")
    ap.add_argument("--mcp-tools", type=int, default=None, help="padrão: nº de tools do contrato (T5)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    version = a.expect_version or (ROOT / "VERSION").read_text().strip()
    tools = a.mcp_tools if a.mcp_tools is not None else contract_tools()
    try:
        results = run_checks(http(a.base), version, tools)
    except (OSError, urllib.error.URLError) as exc:
        print(f"ERRO: não foi possível falar com {a.base}: {exc}", file=sys.stderr)
        return 2
    falhas = [r for r in results if not r["ok"]]
    if a.json:
        print(json.dumps({"base": a.base, "ok": not falhas, "resultados": results}, ensure_ascii=False, indent=1))
    else:
        for r in results:
            print(f"  [{'OK ' if r['ok'] else 'FALHA'}] {r['check']}" + (f" — {r['detalhe']}" if r["detalhe"] and not r["ok"] else ""))
        print(f"{len(results) - len(falhas)}/{len(results)} verificações ok em {a.base}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
