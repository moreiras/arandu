# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — scripts/post_deploy_check.py com um transporte falso (nenhuma rede)."""
import json

from scripts import post_deploy_check as pdc

TOOLS = list(pdc.TOOLS_CHAVE) + ["outorga_lista"]
HTML = b'<!doctype html><html><body><div id="root"></div></body></html>'


SEM_CHAVE = {"result": {"structuredContent": {"snapshot_date": "2026-10-11", "contatos_liberados": False, "motivo": "exige chave"}}}


def fake(version="1.1.5", tools=TOOLS, contacts=401, coleta_ok=True, drop=(), mcp_contatos=SEM_CHAVE):
    def call(method, path, body=None, headers=None):
        p = path.split("?")[0]
        if p in drop:
            return 500, {}, b"erro"
        if p == "/health":
            return 200, {}, json.dumps({"status": "ok", "version": version, "latest_snapshot": "2026-10-11"}).encode()
        if p == "/api/v1/snapshots":
            return 200, {}, json.dumps({"snapshots": ["2026-10-11"], "latest": "2026-10-11"}).encode()
        if p == "/api/v1/snapshots/2026-10-11":
            return 200, {}, json.dumps({"manifest": {"pipeline_version": version, "coleta_ok": coleta_ok,
                                                      "coleta": "completa" if coleta_ok else "parcial",
                                                      "checks": {"vrps": {"status": "ok" if coleta_ok else "falha"}}}}).encode()
        if p == "/api/v1/ixps":
            return 200, {}, json.dumps({"ixps": [], "snapshot_date": "x"}).encode()
        if p == "/api/v1/asns":
            return 200, {}, json.dumps({"items": [], "total": 0, "snapshot_date": "x"}).encode()
        if p == "/api/v1/cdns/presence":
            return 200, {}, b'{"cdns": []}'
        if p == "/api/v1/schema":
            return 200, {}, b'{"collections": {}}'
        if p == "/api/v1/acessos/stats":
            return 200, {}, b'{"total_acessos": 1}'
        if p == "/api/v1/rpki/summary":
            return 200, {}, b'{"br_asns_total": 1}'
        if p.endswith("/contacts"):
            return contacts, {}, b'{"detail": "login"}'
        if p == "/mcp":
            m = (body or {}).get("method")
            if m == "initialize":
                return 200, {"Mcp-Session-Id": "s1"}, b'event: message\r\ndata: {"jsonrpc":"2.0","id":1,"result":{}}\r\n\r\n'
            if m == "tools/list":
                return 200, {}, ("data: " + json.dumps({"result": {"tools": [{"name": t} for t in tools]}})).encode()
            if m == "tools/call":
                return 200, {}, ("data: " + json.dumps(mcp_contatos)).encode()
            return 202, {}, b""
        return 200, {}, HTML
    return call


def failed(results):
    return sorted(r["check"] for r in results if not r["ok"])


def test_instancia_saudavel_passa_em_tudo():
    r = pdc.run_checks(fake(), "1.1.5", mcp_tools=len(TOOLS))
    assert failed(r) == [] and len(r) >= 18


def test_versao_errada_e_detectada():
    assert failed(pdc.run_checks(fake(version="1.1.4"), "1.1.5", len(TOOLS))) == ["versão exposta"]


def test_rota_quebrada_e_detectada():
    assert failed(pdc.run_checks(fake(drop={"/api/v1/ixps"}), "1.1.5", len(TOOLS))) == ["rota /api/v1/ixps"]


def test_contatos_abertos_sao_falha_de_privacidade():
    assert "privacidade: contatos exigem login" in failed(pdc.run_checks(fake(contacts=200), "1.1.5", len(TOOLS)))


def test_mcp_com_tool_de_contatos_ou_sem_tool_chave():
    r = pdc.run_checks(fake(tools=TOOLS + ["get_peeringdb_contacts"]), "1.1.5", len(TOOLS) + 1)
    assert failed(r) == ["mcp sem tool de contatos além das com chave"]
    com = TOOLS + list(pdc.TOOLS_CONTATOS)
    assert failed(pdc.run_checks(fake(tools=com), "1.1.5", len(com))) == []
    vazou = {"result": {"structuredContent": {"contacts": [{"email": "noc@exemplo.test"}]}}}
    assert failed(pdc.run_checks(fake(tools=com, mcp_contatos=vazou), "1.1.5", len(com))) == ["mcp: contatos exigem chave"]
    r = pdc.run_checks(fake(tools=[t for t in TOOLS if t != "query"]), "1.1.5", len(TOOLS))
    assert set(failed(r)) == {"mcp tools-chave", "mcp nº de tools = contrato"}


def test_snapshot_parcial_reprova_a_sanidade_de_coleta():
    assert failed(pdc.run_checks(fake(coleta_ok=False), "1.1.5", len(TOOLS))) == ["sanidade de coleta"]


def test_contrato_do_mcp_tem_ao_menos_52_tools_visiveis():
    assert pdc.contract_tools() >= 52     # piso: sobe a cada tool nova
