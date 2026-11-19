# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — perfil da conta, chave de MCP e rotas internas, sobre a API real com o dataset sintético. A chave só existe em memória."""
import logging

import pytest

from api.auth import chaves_mcp, contas, sessao
from api.auth.jwt_utils import create_token

TOKEN_INTERNO = "interno-de-teste"
ACAO = {"X-Arandu-Acao": "1"}


@pytest.fixture()
def ctx(api, monkeypatch):
    monkeypatch.setenv("MCP_KEY_ATIVA", "1")
    monkeypatch.setenv("MCP_KEY_PEPPER", "p" * 40)
    monkeypatch.setenv("INTERNAL_API_TOKEN", TOKEN_INTERNO)
    from api.auth import internas
    internas.limite = type(internas.limite)()       # contadores zerados por teste
    sessao.limpar_cache()
    cfg = api.app.state.auth_config
    conta = contas.registrar_login(cfg.data_dir, "teste@example.org", "Teste", "google")
    jwt = create_token(conta.email, conta.nome, "google", cfg.jwt_secret, conta.conta_id)
    api.cookies.set("auth_token", jwt)
    yield api, cfg, conta
    api.cookies.clear()
    chaves_mcp.apagar_da_conta(cfg.data_dir, conta.conta_id)
    contas.apagar(cfg.data_dir, conta.conta_id)


def test_perfil_exige_login(api):
    api.cookies.clear()
    assert api.get("/auth/perfil").status_code == 401


def test_perfil_mostra_dados_minimos_sem_chave(ctx):
    api, _, conta = ctx
    r = api.get("/auth/perfil")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    j = r.json()
    assert j["email"] == conta.email and j["chave_mcp"] == {"disponivel": True, "ativa": None}


def test_gerar_usar_rotacionar_e_revogar(ctx, caplog):
    api, cfg, conta = ctx
    assert api.post("/auth/perfil/chave-mcp", json={}).status_code == 400                    # sem o cabeçalho de ação
    with caplog.at_level(logging.DEBUG):
        r = api.post("/auth/perfil/chave-mcp", json={"rotulo": "meu cliente"}, headers=ACAO)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    chave = r.json()["chave"]
    assert chave.startswith("arandu_mcp_")
    v = api.post("/internal/mcp-chave/verificar", json={"chave": chave, "cliente": "c1"}, headers={"X-Internal-Token": TOKEN_INTERNO})
    assert v.json() == {"valida": True, "conta_id": conta.conta_id}
    perfil = api.get("/auth/perfil").json()
    assert perfil["chave_mcp"]["ativa"]["rotulo"] == "meu cliente" and chave.split("_")[-1] not in str(perfil)        # o perfil nunca devolve a chave
    nova = api.post("/auth/perfil/chave-mcp", json={}, headers=ACAO).json()["chave"]
    h = {"X-Internal-Token": TOKEN_INTERNO}
    assert api.post("/internal/mcp-chave/verificar", json={"chave": chave}, headers=h).json()["valida"] is False
    assert api.post("/internal/mcp-chave/verificar", json={"chave": nova}, headers=h).json()["valida"] is True
    assert api.delete("/auth/perfil/chave-mcp", headers=ACAO).json() == {"revogada": True}
    assert api.post("/internal/mcp-chave/verificar", json={"chave": nova}, headers=h).json()["valida"] is False
    assert chave.split("_")[-1] not in caplog.text and nova.split("_")[-1] not in caplog.text                          # nada de segredo em log


def test_internas_exigem_o_token(ctx):
    api, *_ = ctx
    assert api.post("/internal/mcp-chave/verificar", json={"chave": "x"}).status_code == 403
    assert api.post("/internal/mcp-chave/verificar", json={"chave": "x"}, headers={"X-Internal-Token": "errado"}).status_code == 403
    assert api.post("/internal/uso-conta", json={"eventos": []}).status_code == 403


def test_tentativas_invalidas_levam_a_429_com_retry_after(ctx):
    api, *_ = ctx
    h = {"X-Internal-Token": TOKEN_INTERNO}
    for _ in range(10):
        assert api.post("/internal/mcp-chave/verificar", json={"chave": "arandu_mcp_" + "AAAAAAAA" + "_" + "B" * 52, "cliente": "abusador"}, headers=h).json()["valida"] is False
    r = api.post("/internal/mcp-chave/verificar", json={"chave": "x", "cliente": "abusador"}, headers=h)
    assert r.status_code == 429 and int(r.headers["Retry-After"]) > 0
    assert api.post("/internal/mcp-chave/verificar", json={"chave": "x", "cliente": "outro"}, headers=h).status_code == 200


def test_chave_desligada_nao_gera_nem_valida(ctx, monkeypatch):
    api, *_ = ctx
    monkeypatch.setenv("MCP_KEY_ATIVA", "0")
    assert api.post("/auth/perfil/chave-mcp", json={}, headers=ACAO).status_code == 404
    assert api.get("/auth/perfil").json()["chave_mcp"] == {"disponivel": False, "ativa": None}


def test_sair_de_todos_derruba_a_sessao(ctx):
    api, *_ = ctx
    assert api.post("/auth/perfil/sair-de-todos", headers=ACAO).status_code == 200
    import time
    time.sleep(1.1)           # o JWT novo teria `iat` posterior; aqui o cookie foi apagado e o antigo é anterior ao corte
    assert api.get("/auth/perfil").status_code == 401


def test_exclusao_desativa_agora_revoga_a_chave_e_agenda_30_dias(ctx):
    api, cfg, conta = ctx
    chave = api.post("/auth/perfil/chave-mcp", json={}, headers=ACAO).json()["chave"]
    r = api.post("/auth/perfil/excluir", headers=ACAO)
    assert r.status_code == 200 and r.json()["prazo_dias"] == 30
    c = contas.por_id(cfg.data_dir, conta.conta_id)
    assert c.desativada and c.exclusao_efetiva_em() == r.json()["exclusao_efetiva_em"]
    assert chaves_mcp.verificar(cfg.data_dir, chave) is None
    # o cookie antigo não vale mais, mesmo sem esperar: a conta está desativada
    sessao.limpar_cache()
    jwt = create_token(conta.email, conta.nome, "google", cfg.jwt_secret, conta.conta_id)
    api.cookies.set("auth_token", jwt)
    assert api.get("/auth/perfil").status_code == 401


def test_uso_da_conta_do_site_e_registrado_sem_querystring(ctx, tmp_path, monkeypatch):
    api, cfg, conta = ctx
    from api import uso_conta
    uso_conta.registrar(cfg.data_dir, conta.conta_id, "api", "/api/v1/ixps", 200)
    j = api.get("/auth/perfil").json()
    assert j["uso"] and j["uso"][-1]["chamadas"] >= 1 and all(set(x) == {"dia", "chamadas"} for x in j["uso"])      # só contagem por dia, sem rotas


def test_fluxo_completo_gerar_usar_no_mcp_e_revogar(ctx):
    """Gera pelo perfil, usa no middleware do MCP falando com a API real (sem rede) e revoga: depois do cache, a chave deixa de valer."""
    import asyncio

    import httpx

    from mcp_server import chave as m

    api, cfg, conta = ctx
    chave = api.post("/auth/perfil/chave-mcp", json={}, headers=ACAO).json()["chave"]
    mw = m.ChaveMiddleware(None, api_url="http://api.test", token=TOKEN_INTERNO, cliente=httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), timeout=5))

    async def chamar(c):
        res, estado = {}, {}

        async def app(scope, receive, send):
            estado.update(scope.get("state", {}))
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        mw.app = app

        async def send(msg):
            if msg["type"] == "http.response.start":
                res["status"] = msg["status"]

        await mw({"type": "http", "method": "GET", "path": "/mcp", "headers": [(b"authorization", f"Bearer {c}".encode())], "client": ("1.2.3.4", 1)}, lambda: None, send)
        return res["status"], estado

    status, estado = asyncio.run(chamar(chave))
    assert status == 200 and estado["conta_id"] == conta.conta_id and estado["access_tier"] == "user"
    assert api.delete("/auth/perfil/chave-mcp", headers=ACAO).json() == {"revogada": True}
    mw._cache.clear()                       # vence o cache de 30 s
    assert asyncio.run(chamar(chave))[0] == 401


def test_s13_limite_global_saturado_nao_nega_a_chave_valida(ctx):
    """saturar o limite global (200 falhas, variando o cliente) negava serviço a toda chave válida."""
    from api.auth import internas
    from api.auth.tentativas import FALHAS_GLOBAIS
    api, cfg, conta = ctx
    chave = api.post("/auth/perfil/chave-mcp", json={}, headers=ACAO).json()["chave"]
    h = {"X-Internal-Token": TOKEN_INTERNO}
    for i in range(FALHAS_GLOBAIS):
        internas.limite.falha(f"abusador-{i}")
    assert internas.limite.saturado()
    r = api.post("/internal/mcp-chave/verificar", json={"chave": chave, "cliente": "legitimo"}, headers=h)
    assert r.status_code == 200 and r.json()["valida"] is True
    r = api.post("/internal/mcp-chave/verificar", json={"chave": "arandu_mcp_" + "AAAAAAAA" + "_" + "B" * 52, "cliente": "novo"}, headers=h)
    assert r.status_code == 429 and r.json()["limitada"] is True
