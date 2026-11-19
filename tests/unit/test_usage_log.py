# SPDX-License-Identifier: AGPL-3.0-or-later
"""T0 — log de uso (`api/usage_log.py`): privacidade, medição e robustez."""
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import usage_log
from api.usage_log import UsageLogger, UsageLogMiddleware, instrument_mcp_tools, normalize_route


def _lines(base):
    out = []
    for p in sorted((base / "ops" / "usage").glob("*.jsonl")):
        out += [json.loads(l) for l in p.read_text().splitlines()]
    return out


def make_app(tmp_path, tier="anon"):
    app = FastAPI()

    @app.middleware("http")
    async def guard(request, call_next):
        request.state.access_tier = tier
        return await call_next(request)

    @app.get("/api/v1/asns/{asn}")
    def asn(asn: int):
        return {"asn": asn, "pad": "x" * 100}

    @app.get("/health")
    def health():
        return {"ok": True}

    app.add_middleware(UsageLogMiddleware, data_dir=tmp_path, src="api")
    return TestClient(app)


# ── medição ────────────────────────────────────────────────────────────────

def test_registra_template_da_rota_status_bytes_e_tier(tmp_path):
    c = make_app(tmp_path)
    r = c.get("/api/v1/asns/64500?date=2026-10-01&token=segredo", headers={"X-Real-IP": "203.0.113.9", "User-Agent": "ua"})
    rec = _lines(tmp_path)[0]
    assert rec["route"] == "/api/v1/asns/{asn}"
    assert rec["method"] == "GET" and rec["status"] == 200 and rec["src"] == "api"
    assert rec["bytes"] == len(r.content)
    assert rec["tier"] == "anon" and rec["ms"] >= 0 and rec["ts"].endswith("Z")


def test_nao_grava_ip_nem_querystring_nem_user_agent(tmp_path):
    c = make_app(tmp_path)
    c.get("/api/v1/asns/64500?email=pessoa@example.org", headers={"X-Real-IP": "203.0.113.9", "User-Agent": "Mozilla-Secreto"})
    raw = next((tmp_path / "ops" / "usage").glob("*.jsonl")).read_text()
    for proibido in ("203.0.113.9", "pessoa@example.org", "Mozilla-Secreto", "64500"):
        assert proibido not in raw


def test_rota_inexistente_vira_404_registrado(tmp_path):
    make_app(tmp_path).get("/api/v1/nao-existe/123")
    rec = _lines(tmp_path)[0]
    assert rec["status"] == 404 and "123" not in rec["route"]


@pytest.mark.parametrize("path", ["/health"])
def test_rotas_de_infraestrutura_nao_sao_registradas(tmp_path, path):
    make_app(tmp_path).get(path)
    assert _lines(tmp_path) == []


def test_desligado_por_variavel(tmp_path, monkeypatch):
    monkeypatch.setenv("USAGE_LOG", "off")
    make_app(tmp_path).get("/api/v1/asns/1")
    assert _lines(tmp_path) == []


def test_falha_de_gravacao_nao_afeta_a_resposta(tmp_path):
    arquivo = tmp_path / "ops"
    arquivo.write_text("eu sou um arquivo, não um diretório")
    r = make_app(tmp_path).get("/api/v1/asns/1")
    assert r.status_code == 200


# ── identificador anônimo ──────────────────────────────────────────────────

def test_hash_estavel_no_dia_e_diferente_entre_clientes(tmp_path):
    lg = UsageLogger(tmp_path)
    a = lg.client_hash("203.0.113.9", "ua")
    assert a == lg.client_hash("203.0.113.9", "ua")
    assert a != lg.client_hash("203.0.113.10", "ua")
    assert a != lg.client_hash("203.0.113.9", "outro")
    assert len(a) == 16 and "203" not in a


def test_hash_muda_quando_o_sal_gira(tmp_path, monkeypatch):
    lg = UsageLogger(tmp_path)
    hoje = lg.client_hash("203.0.113.9", "ua")
    amanha = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    monkeypatch.setattr(lg, "_today", lambda: amanha)
    assert lg.client_hash("203.0.113.9", "ua") != hoje


def test_sal_antigo_e_apagado_e_o_arquivo_do_sal_e_privado(tmp_path, monkeypatch):
    lg = UsageLogger(tmp_path)
    lg.client_hash("1.1.1.1", "")
    d = tmp_path / "ops" / "usage"
    (d / ".salt-2020-01-01").write_text("velho")
    lg2 = UsageLogger(tmp_path)
    lg2.client_hash("1.1.1.1", "")
    nomes = {p.name for p in d.glob(".salt-*")}
    assert nomes == {f".salt-{lg2._today()}"}
    modo = (d / f".salt-{lg2._today()}").stat().st_mode & 0o777
    assert modo == 0o600


def test_dois_processos_compartilham_o_mesmo_sal_do_dia(tmp_path):
    assert UsageLogger(tmp_path).client_hash("9.9.9.9", "u") == UsageLogger(tmp_path).client_hash("9.9.9.9", "u")


# ── retenção ───────────────────────────────────────────────────────────────

def test_retencao_apaga_arquivos_antigos(tmp_path, monkeypatch):
    monkeypatch.setenv("USAGE_LOG_RETENTION_DAYS", "30")
    d = tmp_path / "ops" / "usage"
    d.mkdir(parents=True)
    antigo = (datetime.now(timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%d")
    recente = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
    (d / f"{antigo}.jsonl").write_text("{}\n")
    (d / f"{recente}.jsonl").write_text("{}\n")
    UsageLogger(tmp_path).client_hash("1.1.1.1", "")
    assert not (d / f"{antigo}.jsonl").exists()
    assert (d / f"{recente}.jsonl").exists()


@pytest.mark.parametrize("valor, esperado", [("30", 30), ("0", 1), ("abc", 90), ("", 90)])
def test_retention_days(monkeypatch, valor, esperado):
    monkeypatch.setenv("USAGE_LOG_RETENTION_DAYS", valor)
    assert usage_log.retention_days() == esperado


# ── normalização de rota ───────────────────────────────────────────────────

@pytest.mark.parametrize("path, expected", [
    ("/api/v1/asns/64500", "/api/v1/asns/{n}"),
    ("/api/v1/snapshots/2026-10-01", "/api/v1/snapshots/{date}"),
    ("/api/v1/ixps/sp", "/api/v1/ixps/sp"),
    ("/", "/"),
])
def test_normalize_route(path, expected):
    assert normalize_route(path) == expected


# ── MCP ────────────────────────────────────────────────────────────────────

def test_instrument_mcp_tools_registra_sincronas_e_assincronas(tmp_path):
    from mcp.server.fastmcp import FastMCP

    m = FastMCP("teste")

    @m.tool()
    def soma(a: int, b: int) -> int:
        """soma"""
        return a + b

    @m.tool()
    async def eco(texto: str) -> str:
        """eco"""
        return texto

    @m.tool()
    def quebra() -> str:
        """erro"""
        raise ValueError("falhou")

    assert instrument_mcp_tools(m, tmp_path) == 3
    assert instrument_mcp_tools(m, tmp_path) == 0   # idempotente

    async def go():
        await m.call_tool("soma", {"a": 1, "b": 2})
        await m.call_tool("eco", {"texto": "olá"})
        with pytest.raises(Exception):
            await m.call_tool("quebra", {})

    asyncio.run(go())
    por_rota = {r["route"]: r for r in _lines(tmp_path)}
    assert por_rota["tool:soma"]["status"] == "ok" and por_rota["tool:soma"]["src"] == "mcp"
    assert por_rota["tool:eco"]["status"] == "ok"
    assert por_rota["tool:quebra"]["status"] == "erro"
    assert all(r["client"] is None for r in por_rota.values())


def test_instrument_mcp_tools_sem_gerenciador_interno_nao_quebra(tmp_path):
    assert instrument_mcp_tools(object(), tmp_path) == 0


def test_instrument_mcp_tools_aceita_funcao_data_dir(tmp_path):
    """mcp_server/app.py passa a FUNÇÃO `data_dir`, não um caminho."""
    from mcp.server.fastmcp import FastMCP

    m = FastMCP("teste")

    @m.tool()
    def ping() -> str:
        """ping"""
        return "pong"

    assert instrument_mcp_tools(m, lambda: tmp_path) == 1
    asyncio.run(m.call_tool("ping", {}))
    assert _lines(tmp_path)[0]["route"] == "tool:ping"


def test_modulo_do_mcp_importa_e_instrumenta_as_tools(tmp_path, monkeypatch):
    """O app do MCP precisa importar (senão derruba o health check no deploy) e ter as tools instrumentadas."""
    import importlib
    import sys

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    sys.modules.pop("mcp_server.app", None)
    mod = importlib.import_module("mcp_server.app")
    tools = mod.mcp._tool_manager._tools
    assert len(tools) > 30 and all(getattr(t.fn, "_usage_logged", False) for t in tools.values())
    names = {type(m.cls).__name__ for m in mod.app.user_middleware}
    assert "UsageLogMiddleware" in names or any("UsageLog" in str(m) for m in mod.app.user_middleware)


def test_chamada_interna_do_prewarm_nao_e_registrada(tmp_path):
    c = make_app(tmp_path)
    c.get("/api/v1/asns/1", headers={"X-Arandu-Internal": "prewarm"})
    assert _lines(tmp_path) == []
    c.get("/api/v1/asns/1")
    assert len(_lines(tmp_path)) == 1


def test_route_template_resolve_pelas_rotas_do_app(tmp_path):
    from api.usage_log import route_template

    app = make_app(tmp_path).app
    assert route_template(app, "/api/v1/asns/64500") == "/api/v1/asns/{asn}"
    assert route_template(app, "/nao/existe") is None


def test_resposta_de_middleware_sem_roteador_usa_o_mesmo_nome_de_rota(tmp_path):
    """Hit do byte-cache responde antes do roteador: o nome da rota não pode virar outro."""
    from fastapi import FastAPI
    from starlette.responses import PlainTextResponse

    app = FastAPI()

    @app.get("/api/v1/asns/{asn}")
    def asn(asn: int):
        return {"asn": asn}

    @app.middleware("http")
    async def curto(request, call_next):         # simula LatestCacheMiddleware devolvendo bytes
        if request.url.path == "/api/v1/asns/7":
            return PlainTextResponse("cache")
        return await call_next(request)

    app.add_middleware(UsageLogMiddleware, data_dir=tmp_path)
    c = TestClient(app)
    c.get("/api/v1/asns/7")        # servido pelo "cache"
    c.get("/api/v1/asns/8")        # servido pela rota
    assert {r["route"] for r in _lines(tmp_path)} == {"/api/v1/asns/{asn}"}
