# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Orçamento por cliente (api/limites.py), concorrência por cliente (api/concurrency.py) e parâmetros desconhecidos (api/parametros.py)."""
import asyncio

import pytest
from fastapi import FastAPI, Query
from fastapi.testclient import TestClient

from api import limites
from api.concurrency import ConcurrencyLimitMiddleware
from api.parametros import ParametrosMiddleware, tabela_do_openapi


def test_rede_ipv6_agrega_por_64_e_ipv4_inteiro():
    assert limites.rede_do_ip("2001:db8:1:2::1") == limites.rede_do_ip("2001:db8:1:2:ffff::9") == "2001:db8:1:2::/64"
    assert limites.rede_do_ip("2001:db8:1:3::1") != limites.rede_do_ip("2001:db8:1:2::1")
    assert limites.rede_do_ip("200.160.2.3") == "200.160.2.3" != limites.rede_do_ip("200.160.2.4")
    assert limites.rede_do_ip("::ffff:200.160.2.3") == "200.160.2.3"
    assert limites.hash_da_rede("2001:db8:1:2::1") == limites.hash_da_rede("2001:db8:1:2::abcd")


def _escopo(ip: str, **extra):
    return {"type": "http", "headers": [(b"x-real-ip", ip.encode())], "client": ("10.0.0.1", 1), **extra}


def test_identidade_conta_allowlist_anonimo():
    redes = [__import__("ipaddress").ip_network("203.0.113.128/25")]
    assert limites.identificar(_escopo("203.0.113.130"), "c1", redes).chave == "conta:c1"
    a = limites.identificar(_escopo("203.0.113.130"), None, redes)
    assert a.classe == "allowlist" and a.chave.startswith("rede:")
    assert limites.identificar(_escopo("198.51.100.7"), None, redes).classe == "anon"


def test_custo_por_rota():
    assert limites.custo_api("/api/v1/asns/1") == 1
    assert limites.custo_api("/api/v1/query") == 3
    assert limites.custo_api("/api/v1/map/query") == 5 and limites.custo_api("/api/v1/asns/1/paths") == 5


def _app(perfil="api"):
    app = FastAPI()

    @app.get("/api/v1/x")
    def x():
        return {"ok": True}

    @app.post("/api/v1/query")
    def q():
        return {"ok": True}

    @app.get("/health")
    def h():
        return {"ok": True}

    @app.post("/mcp")
    def mcp():
        return {"ok": True}

    @app.get("/mcp")
    def mcp_get():
        return {"ok": True}

    app.add_middleware(limites.OrcamentoMiddleware, perfil=perfil)
    return app


def test_orcamento_anonimo_recusa_com_429_legivel(monkeypatch):
    monkeypatch.setenv("API_ORCAMENTO_ANON", "3/minute")
    monkeypatch.setenv("ALLOWED_IPS", "")
    c = TestClient(_app())
    h = {"X-Real-IP": "198.51.100.7"}
    assert [c.get("/api/v1/x", headers=h).status_code for _ in range(3)] == [200, 200, 200]
    r = c.get("/api/v1/x", headers=h)
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1 and r.headers["cache-control"] == "no-store"
    assert r.json()["janela"] == "minuto" and r.json()["rate_limited"] is True and "minuto" in r.json()["detail"]
    assert c.get("/api/v1/x", headers={"X-Real-IP": "198.51.100.8"}).status_code == 200      # outra rede, outro orçamento
    assert c.get("/health", headers=h).status_code == 200                                     # isento


def test_ipv6_trocar_sufixo_nao_renova_o_orcamento(monkeypatch):
    monkeypatch.setenv("API_ORCAMENTO_ANON", "2/minute")
    c = TestClient(_app())
    assert c.get("/api/v1/x", headers={"X-Real-IP": "2001:db8:5:6::1"}).status_code == 200
    assert c.get("/api/v1/x", headers={"X-Real-IP": "2001:db8:5:6::2"}).status_code == 200
    assert c.get("/api/v1/x", headers={"X-Real-IP": "2001:db8:5:6::3"}).status_code == 429


def test_custo_da_consulta_gasta_mais(monkeypatch):
    monkeypatch.setenv("API_ORCAMENTO_ANON", "5/minute")
    c = TestClient(_app())
    h = {"X-Real-IP": "198.51.100.9"}
    assert c.post("/api/v1/query", headers=h).status_code == 200          # custa 3
    assert c.post("/api/v1/query", headers=h).status_code == 429          # 3 + 3 > 5: não debita
    assert c.get("/api/v1/x", headers=h).status_code == 200               # 3 + 1 cabe


def test_varias_janelas_valem_ao_mesmo_tempo(monkeypatch):
    monkeypatch.setenv("API_ORCAMENTO_ANON", "100/minute;2/hour")
    c = TestClient(_app())
    h = {"X-Real-IP": "198.51.100.10"}
    assert [c.get("/api/v1/x", headers=h).status_code for _ in range(3)] == [200, 200, 429]
    assert c.get("/api/v1/x", headers=h).json()["janela"] == "hora"


def test_conta_pelo_cookie_independe_do_ip(monkeypatch):
    monkeypatch.setenv("API_ORCAMENTO_CONTA", "2/minute")
    monkeypatch.setattr(limites, "_resolver_api", lambda scope: (lambda tok: "conta-1" if tok == "bom" else None))
    c = TestClient(_app())
    c.cookies.set("auth_token", "bom")
    assert c.get("/api/v1/x", headers={"X-Real-IP": "198.51.100.11"}).status_code == 200
    assert c.get("/api/v1/x", headers={"X-Real-IP": "203.0.113.5"}).status_code == 200
    r = c.get("/api/v1/x", headers={"X-Real-IP": "203.0.113.6"})
    assert r.status_code == 429 and "sua conta" in r.json()["detail"]


def test_desligado_com_zero(monkeypatch):
    monkeypatch.setenv("API_ORCAMENTO_ANON", "0")
    c = TestClient(_app())
    assert all(c.get("/api/v1/x", headers={"X-Real-IP": "198.51.100.12"}).status_code == 200 for _ in range(20))


def test_mcp_conta_so_post_e_usa_conta_do_escopo(monkeypatch):
    monkeypatch.setenv("MCP_ORCAMENTO_ANON", "2/minute")
    c = TestClient(_app("mcp"))
    h = {"X-Real-IP": "198.51.100.13"}
    assert all(c.get("/mcp", headers=h).status_code == 200 for _ in range(5))      # GET de sessão não gasta
    assert [c.post("/mcp", headers=h).status_code for _ in range(3)] == [200, 200, 429]


def test_concorrencia_por_cliente_nao_segura_vaga_global():
    async def cenario():
        liberar = asyncio.Event()
        entrou = []

        async def app(scope, receive, send):
            entrou.append(scope["state"]["identidade"].chave)
            await liberar.wait()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        mw = ConcurrencyLimitMiddleware(app, max_inflight=2, queue_timeout_s=0.3, por_cliente=1)
        enviados = []

        async def send(msg):
            if msg["type"] == "http.response.start":
                enviados.append(msg["status"])

        def escopo(chave):
            return {"type": "http", "path": "/api/v1/x", "state": {"identidade": limites.Identidade("anon", chave, "r")}}

        t1 = asyncio.create_task(mw(escopo("a"), None, send))
        t2 = asyncio.create_task(mw(escopo("a"), None, send))          # mesmo cliente: espera e é recusado
        t3 = asyncio.create_task(mw(escopo("b"), None, send))          # outro cliente: a vaga global restante é dele
        await asyncio.sleep(0.4)
        assert sorted(entrou) == ["a", "b"] and enviados == [503]
        liberar.set()
        await asyncio.gather(t1, t2, t3)
        assert sorted(enviados) == [200, 200, 503] and mw._clientes == {}

    asyncio.run(cenario())


def _app_param():
    app = FastAPI()

    @app.get("/api/v1/asns/{asn}")
    def asn(asn: int, include: str = Query(None)):
        return {"asn": asn}

    app.add_middleware(ParametrosMiddleware)
    return app


def test_tabela_do_openapi_prefere_caminho_fixo():
    esquema = {"paths": {"/api/v1/asns/{asn}": {"get": {"parameters": [{"name": "include", "in": "query"}]}},
                         "/api/v1/asns/summary": {"get": {"parameters": [{"name": "limit", "in": "query"}]}}}}
    tab = tabela_do_openapi(esquema)
    assert tab[0][1] == "/api/v1/asns/summary" and "include" in tab[1][2] and "date" in tab[1][2]


@pytest.mark.parametrize("modo,status", [("registrar", 200), ("rejeitar", 400), ("off", 200)])
def test_parametro_desconhecido(monkeypatch, modo, status):
    monkeypatch.setenv("API_PARAMETROS_DESCONHECIDOS", modo)
    c = TestClient(_app_param())
    assert c.get("/api/v1/asns/1?include=a&date=2026-11-01&v=x").status_code == 200
    r = c.get("/api/v1/asns/1?cachebuster=123")
    assert r.status_code == status
    if status == 400:
        assert "cachebuster" in r.json()["detail"] and r.headers["cache-control"] == "no-store"


def test_fila_das_pesadas_nao_segura_as_leves():
    from api.concurrency import e_pesada

    assert e_pesada({"path": "/api/v1/ixps/sp", "query_string": b"date=2026-11-13&include=membros"})
    assert e_pesada({"path": "/api/v1/asns/1/paths", "query_string": b""})
    assert not e_pesada({"path": "/api/v1/map/submarine-cables", "query_string": b"v=abc"})

    async def cenario():
        liberar = asyncio.Event()
        entrou = []

        async def app(scope, receive, send):
            entrou.append(scope["path"])
            if e_pesada(scope):
                await liberar.wait()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        mw = ConcurrencyLimitMiddleware(app, max_inflight=8, queue_timeout_s=5, por_cliente=0)
        mw.sem_pesadas, mw.timeout_pesadas = asyncio.Semaphore(2), 0.3
        enviados = []

        async def send(msg):
            if msg["type"] == "http.response.start":
                enviados.append(msg["status"])

        def escopo(path, qs=b""):
            return {"type": "http", "path": path, "query_string": qs, "state": {}}

        pesadas = [asyncio.create_task(mw(escopo(f"/api/v1/ixps/p{i}", b"include=membros"), None, send)) for i in range(3)]
        await asyncio.sleep(0.05)
        await mw(escopo("/api/v1/map/submarine-cables"), None, send)          # leve: passa com 2 pesadas calculando
        assert enviados == [200] and sum(p.startswith("/api/v1/ixps/") for p in entrou) == 2
        await asyncio.sleep(0.4)                                               # a 3ª pesada esgota a espera da fila própria
        assert 503 in enviados
        liberar.set()
        await asyncio.gather(*pesadas)
        assert sorted(enviados) == [200, 200, 200, 503] and mw.sem._value == 8 and mw.sem_pesadas._value == 2

    asyncio.run(cenario())


def test_pedido_interno_do_aquecimento_fica_fora_do_orcamento(monkeypatch):
    import httpx

    monkeypatch.setenv("API_ORCAMENTO_ANON", "2/minute")
    monkeypatch.setenv("API_ORCAMENTO_CONTA", "2/minute")
    monkeypatch.setenv("ALLOWED_IPS", "127.0.0.1")
    app = _app()

    async def cenario():
        h = {"x-arandu-internal": "prewarm"}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://prewarm") as c:
            assert [(await c.get("/api/v1/x", headers=h)).status_code for _ in range(5)] == [200] * 5
            # de fora (com X-Real-IP, como o nginx manda) o mesmo cabeçalho não dá passe livre
            r = [(await c.get("/api/v1/x", headers={**h, "X-Real-IP": "198.51.100.20"})).status_code for _ in range(3)]
            assert r == [200, 200, 429]

    asyncio.run(cenario())
