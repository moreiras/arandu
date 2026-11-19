# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""sem chave, o MCP serve a mesma prévia que o site serve sem login."""
from types import SimpleNamespace

import pytest

from api.auth.access_policy import PREVIEW_LIMIT
from mcp_server import previa

REC = ["2026-11-06", "2026-11-13"]


def _c(nome, explicitos=(), **args):
    return previa.conferir(nome, {**args, "__explicitos__": set(explicitos)}, REC)


def test_dentro_da_previa_passa():
    assert _c("query", ["limit"], collection="asns", limit=100, page=1, date="2026-11-13")["limit"] == 100
    assert _c("asn_lista", [], limit=50, date=None)["limit"] == 50


@pytest.mark.parametrize("nome,expl,args,trecho", [
    ("query", ["limit"], {"collection": "asns", "limit": 1000}, "limit=1000"),
    ("query", ["page"], {"collection": "asns", "limit": 100, "page": 2}, "page=2"),
    ("operadora_lista", ["offset"], {"offset": 100}, "offset=100"),
    ("asn_detalhe", ["date"], {"date": "2026-10-11"}, "date=2026-10-11"),
    ("historico_serie", [], {"escopo": "brasil", "de": None}, "histórico"),
    ("historico_mudancas", ["de"], {"de": "2026-10-01", "limit": 50}, "histórico"),
    ("query", [], {"collection": "eventos", "limit": 100, "date": None}, "histórico"),
])
def test_alem_da_previa_e_erro_que_explica_a_chave(nome, expl, args, trecho):
    with pytest.raises(previa.PreviaExcedida, match=trecho) as e:
        _c(nome, expl, **args)
    assert "/perfil" in str(e.value) and "Authorization: Bearer" in str(e.value)


def test_padrao_da_tool_acima_da_previa_e_reduzido():
    assert _c("ixp_nearby", [], code="sp", limit=500)["limit"] == PREVIEW_LIMIT


def test_historico_a_partir_de_snapshot_recente_passa():
    assert _c("historico_mudancas", ["de"], de="2026-11-06", limit=50)["de"] == "2026-11-06"


def _mcp_com(pedido):
    ctx = SimpleNamespace(request_context=SimpleNamespace(request=pedido))
    return SimpleNamespace(get_context=lambda: ctx)


def _pedido(tier=None, ip="203.0.113.9"):
    return SimpleNamespace(scope={"state": {"access_tier": tier}} if tier else {}, headers={"x-real-ip": ip}, client=None)


def test_nivel(monkeypatch):
    monkeypatch.setenv("ALLOWED_IPS", "10.0.0.0/8")
    assert previa.nivel(SimpleNamespace(get_context=lambda: (_ for _ in ()).throw(ValueError()))) == "local"
    assert previa.nivel(_mcp_com(None)) == "local"
    assert previa.nivel(_mcp_com(_pedido("user"))) == "user"
    assert previa.nivel(_mcp_com(_pedido(ip="10.1.2.3"))) == "allowed"
    assert previa.nivel(_mcp_com(_pedido())) == "anon"


def test_envoltorio_aplica_so_ao_anonimo(monkeypatch):
    chamadas = []

    def tool(collection: str, limit: int = 100, page: int = 1, date=None):
        chamadas.append((collection, limit, page, date))
        return "ok"

    mcp = SimpleNamespace(_tool_manager=SimpleNamespace(_tools={"query": SimpleNamespace(fn=tool)}))
    assert previa.aplicar(mcp, lambda: REC) == 1
    fn = mcp._tool_manager._tools["query"].fn
    monkeypatch.setattr(previa, "nivel", lambda m: "anon")
    with pytest.raises(previa.PreviaExcedida):
        fn("asns", limit=1000)
    assert fn("asns", limit=10) == "ok"
    monkeypatch.setattr(previa, "nivel", lambda m: "user")
    assert fn("asns", limit=1000, page=3) == "ok"
    assert chamadas == [("asns", 10, 1, None), ("asns", 1000, 3, None)]
    assert previa.aplicar(mcp, lambda: REC) == 0                      # não envolve duas vezes


def test_todas_as_tools_reais_estao_envolvidas():
    from mcp_server import app as m
    assert all(getattr(t.fn, "_previa", False) for t in m.mcp._tool_manager._tools.values())


def test_varias_tools_pelo_caminho_do_fastmcp(monkeypatch):
    """A envolvente não pode ver a assinatura da ÚLTIMA tool registrada (closure no laço): `asn_lista` e `query` passariam sem prévia e
    `asn_detalhe` receberia `prefix`. Aqui pelo `call_tool` do FastMCP, que passa todos os campos (inclusive os padrões) à função."""
    import asyncio
    from mcp.server.fastmcp import FastMCP
    from mcp.server.fastmcp.exceptions import ToolError
    srv = FastMCP("t")
    recebido = {}

    @srv.tool()
    def asn_lista(q: str = "", page: int = 1, limit: int = 100, date: str = "") -> dict:
        recebido["asn_lista"] = (q, page, limit, date)
        return {"ok": 1}

    @srv.tool()
    def asn_detalhe(asn: int, date: str = "") -> dict:
        recebido["asn_detalhe"] = (asn, date)
        return {"ok": 1}

    @srv.tool()
    def grande(limit: int = 500) -> dict:
        recebido["grande"] = limit
        return {"ok": 1}

    @srv.tool()
    def rota_prefixo(prefix: str, date: str = "") -> dict:
        return {"ok": 1}

    assert previa.aplicar(srv, lambda: REC) == 4
    monkeypatch.setattr(previa, "nivel", lambda m: "anon")
    chamar = lambda n, a: asyncio.run(srv.call_tool(n, a))
    for nome, args in (("asn_lista", {"limit": 500}), ("asn_lista", {"page": 2}), ("asn_detalhe", {"asn": 1, "date": "2026-01-01"})):
        with pytest.raises(ToolError):
            chamar(nome, args)
    chamar("asn_detalhe", {"asn": 263276, "date": REC[0]})
    assert recebido["asn_detalhe"] == (263276, REC[0])
    chamar("asn_lista", {})
    assert recebido["asn_lista"] == ("", 1, 100, "")
    chamar("grande", {})
    assert recebido["grande"] == PREVIEW_LIMIT                      # padrão acima da prévia é reduzido, não recusado
    with pytest.raises(ToolError):
        chamar("grande", {"limit": 300})
    monkeypatch.setattr(previa, "nivel", lambda m: "user")
    chamar("asn_lista", {"limit": 500, "page": 3})
    assert recebido["asn_lista"] == ("", 3, 500, "")
