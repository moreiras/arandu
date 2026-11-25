# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — `GET /api/v1/limites` (PT-21, TRANSV-E13): a rota devolve os mesmos valores das constantes do código, sem número duplicado."""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
ENV = ("API_ORCAMENTO_ANON", "API_ORCAMENTO_CONTA", "MCP_ORCAMENTO_ANON", "MCP_ORCAMENTO_CONTA", "MCP_COTA_DIARIA", "MCP_KEY_ATIVA",
       "MCP_KEY_PEPPER", "ANON_SESSION_LIMIT_MINUTES", "ANON_API_CLIENT_COST_SECONDS")
CONTATOS = tuple(f"CONTATOS_CONTA_{c}" for c in ("RAJADA", "HORA", "DIA", "30D", "NOVA_DIA", "NOVA_DIAS"))      # o conftest os desliga (0)


@pytest.fixture()
def cli(monkeypatch):
    for v in ENV + CONTATOS:
        monkeypatch.delenv(v, raising=False)
    from api.routes import limites
    app = FastAPI()
    app.include_router(limites.router, prefix="/api/v1")
    return TestClient(app)


def _janelas(texto: str) -> list[tuple[int, str]]:
    return [(int(n), j) for n, j in (p.split("/") for p in texto.split(";"))]


def test_rota_devolve_os_valores_das_constantes(cli):
    from api import contatos_cota
    from api.auth.access_policy import N_DATAS_ATUAIS, PREVIEW_LIMIT
    from api.limites import PADROES, custo_api
    from mcp_server import chave
    r = cli.get("/api/v1/limites")
    assert r.status_code == 200 and "max-age" in r.headers["cache-control"]
    d = r.json()
    nome = {"minute": "minuto", "hour": "hora", "day": "dia"}
    for perfil, classes in (("api", {"sem_conta": "anon", "com_conta": "conta"}), ("mcp", {"sem_chave": "anon", "com_chave": "conta"})):
        for chave_json, classe in classes.items():
            esperado = [(n, nome[j]) for n, j in _janelas(PADROES[perfil][classe])]
            assert [(j["limite"], j["janela"]) for j in d[perfil][chave_json]] == esperado, (perfil, chave_json)
    assert d["mcp"]["chave"]["cota_diaria"] == chave.COTA_DIARIA_PADRAO == chave.cota_diaria()
    assert d["sem_conta"]["orcamento_diario_segundos"] == 600 and d["sem_conta"]["custo_por_chamada_segundos"] == 3
    assert d["sem_conta"]["chamadas_medidas_por_dia"] == 200
    assert d["sem_conta"]["previa_linhas"] == PREVIEW_LIMIT and d["sem_conta"]["snapshots_atuais"] == N_DATAS_ATUAIS
    assert d["api"]["custo_por_rota"] == {"/api/v1/asns": custo_api("/api/v1/asns"), "/api/v1/query": 3, "/api/v1/map/query": 5, "demais": 1}
    assert d["api"]["chave_na_rest"] is False
    assert d["contatos"] == contatos_cota.tetos_da_conta()
    assert d["contatos"]["por_dia"] == contatos_cota.PADROES["CONTATOS_CONTA_DIA"]


def test_nao_publica_o_que_ensinaria_a_esgotar_a_cota_dos_outros(cli):
    corpo = cli.get("/api/v1/limites").text
    for proibido in ("GLOBAL", "global", "REDE_", "SUSPENDER", "suspens", "MAX_SESSOES"):
        assert proibido not in corpo, proibido


def test_variaveis_de_ambiente_mudam_a_rota_e_o_middleware(cli, monkeypatch):
    monkeypatch.setenv("API_ORCAMENTO_ANON", "30/minute;200/day")
    monkeypatch.setenv("MCP_COTA_DIARIA", "0")
    monkeypatch.setenv("ANON_SESSION_LIMIT_MINUTES", "1")
    d = cli.get("/api/v1/limites").json()
    assert d["api"]["sem_conta"] == [{"janela": "minuto", "segundos": 60, "limite": 30}, {"janela": "dia", "segundos": 86400, "limite": 200}]
    assert d["mcp"]["chave"]["sem_teto_diario"] is True and d["mcp"]["chave"]["cota_diaria"] is None
    assert d["sem_conta"]["orcamento_diario_segundos"] == 60 and d["sem_conta"]["chamadas_medidas_por_dia"] == 20
    from api.limites import OrcamentoMiddleware        # o middleware lê pela mesma função
    mw = OrcamentoMiddleware(app=None, perfil="api")
    assert [(i.amount, i.get_expiry()) for i in mw.limites["anon"]] == [(30, 60), (200, 86400)]


def test_classe_desligada_vira_lista_vazia(cli, monkeypatch):
    monkeypatch.setenv("MCP_ORCAMENTO_ANON", "0")
    assert cli.get("/api/v1/limites").json()["mcp"]["sem_chave"] == []


def test_chave_so_consta_como_ativa_com_pepper(cli, monkeypatch):
    assert cli.get("/api/v1/limites").json()["mcp"]["chave"]["ativa"] is False
    monkeypatch.setenv("MCP_KEY_ATIVA", "1")
    monkeypatch.setenv("MCP_KEY_PEPPER", "p" * 32)
    assert cli.get("/api/v1/limites").json()["mcp"]["chave"]["ativa"] is True


def test_rota_e_open_e_aparece_na_matriz_de_cobertura():
    from api.auth.access_policy import OPEN, classify
    assert classify("GET", "/api/v1/limites", {}, ["2026-11-15"]).cls == OPEN
    assert "GET /limites" in (ROOT / "serve" / "capabilities" / "_manuais.yaml").read_text(encoding="utf-8")
    assert "/limites" in (ROOT / "docs" / "cobertura.md").read_text(encoding="utf-8")


def test_llms_txt_reflete_os_valores_reais(monkeypatch):
    for v in ENV:
        monkeypatch.delenv(v, raising=False)
    from api.routes import sitemap
    t = sitemap.llms()
    assert "anônima com os mesmos limites" not in t
    assert "600 s por dia UTC" in t and "3 s por chamada medida" in t and "/api/v1/limites" in t and "60/minuto, 1000/hora, 5000/dia" in t
    assert "Com chave" not in t, "com a chave de MCP desligada, o llms.txt não pode prometê-la"
    monkeypatch.setenv("MCP_KEY_ATIVA", "1")
    monkeypatch.setenv("MCP_KEY_PEPPER", "p" * 32)
    t = sitemap.llms()
    assert "Com chave" in t and "60/minuto, 400/hora" in t and "cota de 1000 requisições por dia UTC" in t
    monkeypatch.setenv("MCP_COTA_DIARIA", "0")
    assert "sem teto diário" in sitemap.llms()

