# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Capacidades declaradas: validação das declarações e comportamento das rotas geradas por elas."""
import textwrap

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.capacidades import gerar_rotas
from core.capacidades import PASTA, CapacidadeErro, carregar_arquivo, carregar_todas, capacidade

BASE = {
    "entidade": "x", "rotulo": "X", "plural": "Xs", "nome_longo": "Serviço X", "servico": "stfc", "tag": "x",
    "operacoes": [{"id": "lista", "tipo": "lista_outorgas", "http": "GET /xs", "funcao": "list_xs", "summary": "s", "descricao": "d",
                   "filtros": ["uf"], "ordena_por": ["cnpj"]}],
}


def _grava(tmp_path, nome=None, **mudancas):
    doc = {**BASE, **mudancas}
    p = tmp_path / f"{nome or doc['entidade']}.yaml"
    p.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    return p


def test_as_quatro_declaracoes_carregam_e_cobrem_os_servicos_de_outorga():
    from core.outorgas import SERVICOS
    assert {c.servico for c in carregar_todas()} == set(SERVICOS)
    for c in carregar_todas():
        assert [o.id for o in c.operacoes] == ["lista", "stats", "por_cnpj"]
        assert c.privacidade == "sem_contatos"


@pytest.mark.parametrize("mudanca,trecho", [
    ({"servico": "inexistente"}, "servico 'inexistente'"),
    ({"privacidade": "com_contatos"}, "privacidade"),
    ({"entidade": "outro"}, "deve ser o nome do arquivo"),
    ({"operacoes": [{**BASE["operacoes"][0], "tipo": "magico"}]}, "tipo 'magico'"),
    ({"operacoes": [{**BASE["operacoes"][0], "filtros": ["nao_existe"]}]}, "filtro desconhecido 'nao_existe'"),
    ({"operacoes": [{**BASE["operacoes"][0], "http": "POST /xs"}]}, "GET /caminho"),
    ({"operacoes": [{**BASE["operacoes"][0], "ordena_por": []}]}, "ordena_por"),
    ({"operacoes": [{**BASE["operacoes"][0]}, {**BASE["operacoes"][0]}]}, "ids de operação repetidos"),
    ({"operacoes": [{k: v for k, v in BASE["operacoes"][0].items() if k != "funcao"}]}, "falta 'funcao'"),
])
def test_declaracao_invalida_aponta_arquivo_e_campo(tmp_path, mudanca, trecho):
    with pytest.raises(CapacidadeErro, match=trecho):
        carregar_arquivo(_grava(tmp_path, nome="x", **mudanca))


def test_rota_ou_funcao_repetida_entre_entidades_e_recusada(tmp_path):
    _grava(tmp_path, entidade="a")
    _grava(tmp_path, entidade="b")
    with pytest.raises(CapacidadeErro, match="já declarado"):
        carregar_todas.__wrapped__(tmp_path)


# --- comportamento das rotas geradas, com um Store falso ---------------------------------------------------------------------------

REGISTROS = [
    {"cnpj": "11111111000111", "razao_social": "Beta Telecom", "nome_fantasia": "Beta", "uf": "SP", "municipio": "Campinas", "situacao": "ATI",
     "data_outorga": "10/02/2020", "asns": [64501], "lat": None, "sici_ativo": True, "sici_acessos": 50},
    {"cnpj": "11111111000111", "razao_social": "Beta Telecom", "nome_fantasia": "Beta", "uf": "SP", "municipio": "Campinas", "situacao": "ATI",
     "data_outorga": "01/01/2022", "asns": [64501], "lat": -22.9, "lon": -47.0, "sici_ativo": True, "sici_acessos": 50},
    {"cnpj": "22222222000122", "razao_social": "alfa Net", "nome_fantasia": "", "uf": "RJ", "municipio": "Niterói", "situacao": "EXT",
     "data_outorga": "31/12/2019", "asns": [], "lat": -22.8, "sici_ativo": False, "sici_acessos": 0},
    {"cnpj": "33333333000133", "razao_social": "Gama", "nome_fantasia": "G", "uf": None, "municipio": None, "situacao": None,
     "data_outorga": "", "asns": [64502, 64503], "sici_acessos": None},
]


class LojaFalsa:
    def resolve_date(self, d):
        return d or "2026-09-20" if d != "vazio" else None

    def stfc_index(self, d):
        return list(REGISTROS)

    def scm_index(self, d):
        return list(REGISTROS)

    def _load_scm(self, d):
        return {"scms": REGISTROS, "by_cnpj": {r["cnpj"]: [r] for r in REGISTROS}, "cnpj_to_asns": {"11111111000111": [64501]},
                "total": 4, "unique_cnpjs": 3, "matched_asns": 1}

    def scm_asn_set(self, d):
        return frozenset({64501})

    def asn_index(self, d):
        return [{"asn": 64501, "is_br": True}, {"asn": 64999, "is_br": True}, {"asn": 1, "is_br": False}]

    def scm_for_cnpj(self, d, cnpj):
        return [r for r in REGISTROS if r["cnpj"] == cnpj]


def _cliente(entidade):
    app = FastAPI()
    app.state.store = LojaFalsa()
    router, _ = gerar_rotas(entidade)
    app.include_router(router)
    return TestClient(app)


def _cnpjs(r):
    return [i["cnpj"] for i in r.json()["items"]]


def test_filtros_busca_e_ordenacao_da_lista():
    c = _cliente("scm")
    assert _cnpjs(c.get("/scms", params={"uf": "sp"})) == ["11111111000111"]                    # uma linha por CNPJ (a geolocalizada vence)
    assert c.get("/scms", params={"uf": "sp"}).json()["items"][0]["data_outorga"] == "01/01/2022"
    assert _cnpjs(c.get("/scms", params={"q": "ALFA"})) == ["22222222000122"]
    assert _cnpjs(c.get("/scms", params={"q": "33.333.333/0001-33"})) == ["33333333000133"]     # a busca por CNPJ ignora a máscara
    assert _cnpjs(c.get("/scms", params={"com_asn": "true", "sort_by": "asns", "sort_desc": "true"})) == ["33333333000133", "11111111000111"]
    assert _cnpjs(c.get("/scms", params={"ativo": "false"})) == ["22222222000122", "33333333000133"]
    assert _cnpjs(c.get("/scms", params={"min_acessos": 1})) == ["11111111000111"]
    assert _cnpjs(c.get("/scms", params={"sort_by": "data_outorga"})) == ["33333333000133", "22222222000122", "11111111000111"]
    assert _cnpjs(c.get("/scms", params={"sort_by": "campo_que_nao_existe"})) == ["11111111000111", "22222222000122", "33333333000133"]
    r = c.get("/scms", params={"limit": 2, "page": 2}).json()
    assert (r["total"], r["pages"], len(r["items"])) == (3, 2, 1)


def test_lista_sem_deduplicar_mantem_as_outorgas_repetidas():
    assert len(_cliente("stfc").get("/stfcs").json()["items"]) == 4      # só o SCM deduplica por CNPJ


def test_stats_com_blocos_e_erros():
    c = _cliente("scm")
    r = c.get("/scms/stats").json()
    assert list(r)[:6] == ["snapshot_date", "total", "unique_cnpjs", "geolocated", "matched_asns", "cnpjs_with_asn"]
    assert (r["total_asns_br"], r["as_with_scm"], r["as_without_scm"], r["geolocated"], r["cnpjs_with_asn"]) == (2, 1, 1, 2, 1)
    assert r["by_uf"] == {"SP": 2, "RJ": 1, "??": 1} and r["top_municipios"][0] == {"municipio": "Campinas", "uf": "SP", "count": 2}
    assert c.get("/scms/stats", params={"date": "vazio"}).status_code == 404


def test_por_cnpj_valida_digitos_e_ausencia():
    c = _cliente("scm")
    ok = c.get("/scms/11.111.111-0001-11").json()
    assert ok["cnpj"] == "11111111000111" and ok["total"] == 2
    assert c.get("/scms/123").status_code == 400
    r = c.get("/scms/99999999000199")
    assert r.status_code == 404 and "SCM" in r.json()["detail"]


def test_operationid_e_descricao_vem_da_declaracao():
    app = FastAPI()
    router, funcoes = gerar_rotas("smp")
    app.include_router(router, prefix="/api/v1")
    op = app.openapi()["paths"]["/api/v1/smps"]["get"]
    cap = capacidade("smp").operacao("lista")
    assert op["operationId"] == "list_smps_api_v1_smps_get" and op["summary"] == cap.summary
    assert op["description"].strip() == cap.descricao.strip() and set(funcoes) == {"list_smps", "smp_stats", "get_smp"}
    sort_by = next(p for p in op["parameters"] if p["name"] == "sort_by")
    assert sort_by["description"].endswith(", ".join(sorted(cap.ordena_por)))


# --- tools do MCP geradas ---------------------------------------------------------------------------------------------------------

def _mcp():
    import asyncio

    from mcp.server.fastmcp import FastMCP

    from mcp_server.capacidades import registrar_tools

    m = FastMCP("t")
    loja = LojaFalsa()
    nomes = registrar_tools(m, lambda: loja, lambda d: loja.resolve_date(d))

    def chamar(nome, args):
        import json
        out = asyncio.run(m.call_tool(nome, args))
        blocos = out[0] if isinstance(out, tuple) else out
        return json.loads("".join(b.text for b in blocos))
    return m, nomes, chamar


def test_so_o_scm_declara_tools_e_o_resto_justifica():
    _, nomes, _ = _mcp()
    assert nomes == ["list_scms", "get_scm"]
    for c in carregar_todas():
        for o in c.operacoes:
            assert o.mcp is not None or o.sem_mcp, f"{c.entidade}/{o.id}: sem tool e sem justificativa"


def test_tool_gerada_tem_o_esquema_do_docstring_e_dos_filtros_declarados():
    import asyncio
    m, _, _ = _mcp()
    tools = {t.name: t for t in asyncio.run(m.list_tools())}
    esquema = tools["list_scms"].inputSchema
    assert list(esquema["properties"]) == ["uf", "q", "com_asn", "situacao", "page", "limit", "date"] and not esquema.get("required")
    assert "Lista paginada de outorgas SCM" in tools["list_scms"].description and "Args:" in tools["list_scms"].description
    assert tools["get_scm"].inputSchema["required"] == ["cnpj"]


def test_tool_list_scms_tri_estado_sem_deduplicar_e_limite():
    _, _, chamar = _mcp()
    assert chamar("list_scms", {"uf": "sp"})["total"] == 2                                  # as duas outorgas do CNPJ (o MCP não deduplica)
    assert [i["cnpj"] for i in chamar("list_scms", {"com_asn": False})["items"]] == ["22222222000122"]
    assert chamar("list_scms", {"com_asn": True})["total"] == 3
    r = chamar("list_scms", {"limit": 99999, "page": -4})
    assert (r["limit"], r["page"], r["total"]) == (500, 1, 4)


def test_tool_get_scm_devolve_records_e_recusa_ausente():
    from mcp.server.fastmcp.exceptions import ToolError
    _, _, chamar = _mcp()
    r = chamar("get_scm", {"cnpj": "11.111.111/0001-11"})
    assert r["cnpj"] == "11111111000111" and r["total"] == 2 and len(r["records"]) == 2
    with pytest.raises(ToolError, match="não encontrado nas outorgas SCM"):
        chamar("get_scm", {"cnpj": "99999999000199"})
