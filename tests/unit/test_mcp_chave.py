# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""MCP com chave: middleware ASGI com a API simulada (sem rede). Chave válida → nível user; inválida → 401; sem chave → anônimo."""
import asyncio
import json

import httpx
import pytest

from mcp_server import chave as m

VALIDA = "arandu_mcp_" + "AAAAAAAA" + "_" + "B" * 52          # montada aqui: o texto do arquivo não casa com o padrão de chave real
CONTA = "conta-uuid-1"


class Api:
    """API de mentira: aceita só `VALIDA`; conta as perguntas e guarda os eventos de uso."""
    def __init__(self):
        self.perguntas, self.eventos, self.fora, self.limitar = 0, [], False, False

    def __call__(self, req: httpx.Request) -> httpx.Response:
        if self.fora:
            raise httpx.ConnectError("fora do ar")
        corpo = json.loads(req.content)
        if req.url.path.endswith("/verificar"):
            self.perguntas += 1
            if self.limitar:
                return httpx.Response(429, headers={"Retry-After": "120"}, json={"valida": False, "limitada": True})
            return httpx.Response(200, json={"valida": True, "conta_id": CONTA} if corpo["chave"] == VALIDA else {"valida": False})
        self.eventos += corpo["eventos"]
        return httpx.Response(200, json={"recebidos": len(corpo["eventos"])})


async def chamar(mw, headers=None, method="POST"):
    resp, estado = {}, {}

    async def app(scope, receive, send):
        estado.update(scope.get("state", {}))
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    mw.app = app

    async def send(msg):
        if msg["type"] == "http.response.start":
            resp["status"] = msg["status"]
            resp["headers"] = {k.decode(): v.decode() for k, v in msg["headers"]}
        else:
            resp["body"] = msg["body"]

    scope = {"type": "http", "method": method, "path": "/mcp", "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()], "client": ("1.2.3.4", 1)}
    await mw(scope, lambda: None, send)
    return resp, estado


@pytest.fixture()
def mw(monkeypatch):
    monkeypatch.setenv("MCP_KEY_ATIVA", "1")
    monkeypatch.setenv("MCP_COTA_DIARIA", "3")
    api = Api()
    mw = m.ChaveMiddleware(None, api_url="http://api", token="t", cliente=httpx.AsyncClient(transport=httpx.MockTransport(api)))
    mw.api = api
    return mw


def rodar(c):
    return asyncio.run(c)


def test_sem_chave_atende_como_anonimo(mw):
    r, estado = rodar(chamar(mw))
    assert r["status"] == 200 and "access_tier" not in estado and mw.api.perguntas == 0


def test_chave_valida_vira_user_e_a_resposta_fica_em_cache(mw):
    for _ in range(2):
        r, estado = rodar(chamar(mw, {"Authorization": f"Bearer {VALIDA}"}))
        assert r["status"] == 200 and estado["access_tier"] == "user" and estado["conta_id"] == CONTA
    assert mw.api.perguntas == 1                        # a segunda veio do cache de 30 s


def test_chave_invalida_ou_de_outro_formato_e_401_nunca_anonimo(mw):
    for h in ("Bearer arandu_mcp_" + "ZZZZZZZZ" + "_" + "C" * 52, "Bearer outra-coisa", "Basic abc"):
        r, _ = rodar(chamar(mw, {"Authorization": h}))
        assert r["status"] == 401 and "Bearer" in r["headers"]["www-authenticate"]


def test_api_fora_do_ar_falha_fechada_so_para_quem_usa_chave(mw):
    mw.api.fora = True
    r, _ = rodar(chamar(mw, {"Authorization": f"Bearer {VALIDA}"}))
    assert r["status"] == 401 and r["headers"]["retry-after"] == "5"
    r, _ = rodar(chamar(mw))
    assert r["status"] == 200


def test_limite_de_tentativas_da_api_vira_429_com_retry_after(mw):
    mw.api.limitar = True
    r, _ = rodar(chamar(mw, {"Authorization": f"Bearer {VALIDA}"}))
    assert r["status"] == 429 and r["headers"]["retry-after"] == "120"


def test_cota_diaria_da_conta_responde_429_sem_suspender(mw):
    h = {"Authorization": f"Bearer {VALIDA}"}
    assert [rodar(chamar(mw, h))[0]["status"] for _ in range(3)] == [200, 200, 200]
    r, _ = rodar(chamar(mw, h))
    assert r["status"] == 429 and int(r["headers"]["retry-after"]) > 0
    assert rodar(chamar(mw, h, method="GET"))[0]["status"] == 200         # só POST (as chamadas do MCP) gasta a cota


def test_ligada_so_com_a_flag(monkeypatch):
    monkeypatch.setenv("MCP_KEY_ATIVA", "0")
    mw = m.ChaveMiddleware(None, api_url="http://api", token="t", cliente=httpx.AsyncClient(transport=httpx.MockTransport(Api())))
    r, estado = rodar(chamar(mw, {"Authorization": "Bearer lixo"}))
    assert r["status"] == 200 and "access_tier" not in estado               # desligada: ignora o cabeçalho (volta ao anônimo)


def test_s13_cliente_e_o_ip_e_ipv6_pelo_64():
    """O cliente da contagem de tentativas é o IP (IPv6 pelo /64), não IP+User-Agent."""
    from mcp_server.chave import _rede_do_cliente
    assert _rede_do_cliente("203.0.113.7") == "203.0.113.7"
    assert _rede_do_cliente("2001:db8:1:2:aaaa::1") == _rede_do_cliente("2001:db8:1:2:bbbb::9") == "2001:db8:1:2::/64"
    assert _rede_do_cliente("2001:db8:1:3::1") != _rede_do_cliente("2001:db8:1:2::1")
    assert _rede_do_cliente("lixo") == "lixo"
