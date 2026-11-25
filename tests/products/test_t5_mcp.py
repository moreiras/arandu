# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T5 — contrato do servidor MCP sobre o dataset sintético.

Inventário (tools, resources, prompt), uma chamada válida por tool e coerência das instruções do servidor,
conferidos contra `tests/contracts/mcp_contract.json`. Tool nova sem contrato falha; remoção de tool ou de
campo de topo falha; campo novo passa. Atualizar: `--update-golden` e REVISAR o diff.
"""
import asyncio
import json

from core.site import com_identidade
import re
from pathlib import Path

import pytest

from api.privacidade import e_chave_de_contato
from tests.products.api_contract import discover
from tests.products.conftest import fake_pix
from tests.products.mcp_contract import SEM_DADOS_NO_SINTETICO, args_for
from core.site import SITE

CONTRACT = Path(__file__).resolve().parents[1] / "contracts" / "mcp_contract.json"
PII_KEYS = {"email", "telefone", "phone"}


@pytest.fixture(scope="module")
def srv(pipeline, api):
    """Módulo do servidor MCP apontando para o publicado sintético (o `api` fornece o contexto de IDs)."""
    base, _ = pipeline
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATA_DIR", str(base))
        from api.store import Store
        from mcp_server import app as m

        mp.setattr(m, "_store", Store(base))
        mp.setattr(Store, "_load_pix_config", lambda self: fake_pix())
        yield m


@pytest.fixture(scope="module")
def ctx(api):
    return discover(api)


def run(coro):
    return asyncio.run(coro)


def tools_of(srv):
    return {t.name: t for t in run(srv.mcp.list_tools())}


def call(srv, name: str, args: dict):
    out = run(srv.mcp.call_tool(name, args))
    blocks = out[0] if isinstance(out, tuple) else out
    text = "".join(getattr(b, "text", "") for b in blocks)
    try:
        return json.loads(text)
    except ValueError:
        return text


def _keys(x, found=None):
    found = set() if found is None else found
    if isinstance(x, dict):
        for k, v in x.items():
            found.add(k.lower())
            _keys(v, found)
    elif isinstance(x, list):
        for v in x[:300]:
            _keys(v, found)
    return found


def _inventory(srv) -> dict:
    tools = tools_of(srv)
    return {
        "tools": {n: {"obrigatorios": sorted((t.inputSchema or {}).get("required", [])),
                      "parametros": sorted((t.inputSchema or {}).get("properties", {}))} for n, t in sorted(tools.items())},
        "resources": sorted(str(r.uri) for r in run(srv.mcp.list_resources())),
        "aliases": {n: {"obrigatorios": sorted((t.parameters or {}).get("required", [])),
                        "parametros": sorted((t.parameters or {}).get("properties", {}))}
                    for n, t in sorted(srv.mcp._tool_manager._tools.items()) if n in srv.mcp.ocultas},
        "templates": sorted(t.uriTemplate for t in run(srv.mcp.list_resource_templates())),
        "prompts": sorted(p.name for p in run(srv.mcp.list_prompts())),
    }


def _chamar(srv, name, ctx, t):
    """Chama a tool com argumentos válidos; as de SEM_DADOS_NO_SINTETICO respondem "indisponível" no dataset sintético (como a REST, 404)."""
    try:
        return call(srv, name, args_for(name, t.inputSchema or {}, ctx))
    except Exception as exc:  # noqa: BLE001
        if name in SEM_DADOS_NO_SINTETICO and "indisponível" in str(exc):
            return "indisponível"
        raise


def test_contrato_do_mcp(srv, ctx, request):
    inv = _inventory(srv)
    tools = tools_of(srv)
    calls = {}
    for name, t in tools.items():
        r = _chamar(srv, name, ctx, t)
        calls[name] = {"tipo": "objeto" if isinstance(r, dict) else "lista" if isinstance(r, list) else "texto",
                       **({"chaves": sorted(r)} if isinstance(r, dict) else {})}
    current = {**inv, "chamadas": calls}
    if request.config.getoption("--update-golden"):
        CONTRACT.parent.mkdir(parents=True, exist_ok=True)
        CONTRACT.write_text(json.dumps({"_doc": __doc__.strip().splitlines()[0], **current},
                                       ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return
    gold = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert set(inv["tools"]) == set(gold["tools"]), (
        f"tools novas: {sorted(set(inv['tools']) - set(gold['tools']))}; "
        f"removidas: {sorted(set(gold['tools']) - set(inv['tools']))} (rode com --update-golden e revise)")
    for n, g in gold["tools"].items():
        assert set(g["obrigatorios"]) == set(inv["tools"][n]["obrigatorios"]), f"{n}: obrigatórios mudaram"
        assert set(g["parametros"]) <= set(inv["tools"][n]["parametros"]), f"{n}: parâmetros removidos"
    for n, g in gold["aliases"].items():          # nada removido sem aviso: o nome antigo segue atendendo, com a mesma assinatura
        assert n in inv["aliases"] or n in inv["tools"], f"alias removido: {n} (duas versões de aviso antes de remover)"
        a = inv["aliases"].get(n) or inv["tools"][n]
        assert set(g["obrigatorios"]) == set(a["obrigatorios"]) and set(g["parametros"]) <= set(a["parametros"]), f"alias {n}: assinatura mudou"
    assert inv["resources"] == gold["resources"]
    assert inv["templates"] == gold["templates"]
    assert inv["prompts"] == gold["prompts"]
    for n, g in gold["chamadas"].items():
        c = calls[n]
        assert c["tipo"] == g["tipo"], f"{n}: tipo {c['tipo']} ≠ {g['tipo']}"
        faltam = sorted(set(g.get("chaves", [])) - set(c.get("chaves", [])))
        assert not faltam, f"{n}: campos removidos da resposta: {faltam}"


def test_toda_tool_tem_chamada_valida_sem_erro(srv, ctx):
    erros = {}
    for name, t in tools_of(srv).items():
        try:
            r = _chamar(srv, name, ctx, t)
        except Exception as exc:  # noqa: BLE001
            erros[name] = str(exc)[:160]
            continue
        if isinstance(r, dict) and r.get("error"):
            erros[name] = str(r["error"])[:160]
    assert erros == {}


def test_resources_e_prompt_legiveis(srv):
    from core.common import app_version

    for r in run(srv.mcp.list_resources()):
        content = run(srv.mcp.read_resource(r.uri))
        text = "".join(c.content for c in content)
        assert text.strip(), f"resource vazio: {r.uri}"
        if str(r.uri) == SITE.uri("overview"):
            assert app_version() in text
    p = run(srv.mcp.get_prompt(SITE.mcp_esquema))
    assert p.messages


def test_nenhuma_tool_devolve_email_ou_telefone_e_nao_ha_tool_de_contatos(srv, ctx):
    """Contatos só pelas duas tools com chave (`asn_contatos`, `operadora_contatos`, cota do site); aqui não há chave e nenhuma devolve contato."""
    tools = tools_of(srv)
    assert not [n for n in tools if "contact" in n or ("contato" in n and n not in ("asn_contatos", "operadora_contatos"))]
    for nome in ("asn_contatos", "operadora_contatos"):
        assert _chamar(srv, nome, ctx, tools[nome])["contatos_liberados"] is False, nome
    achados = {}
    for name, t in tools.items():
        resposta = _chamar(srv, name, ctx, t)
        hit = (PII_KEYS & _keys(resposta)) | {k for k in _keys(resposta) if e_chave_de_contato(k)}      # inclui ddd_telefone_1 e afins
        if hit:
            achados[name] = sorted(hit)
    assert achados == {}


def test_instrucoes_do_servidor_so_citam_tools_que_existem(srv):
    """O playbook enviado ao cliente (`instructions`) cita tools entre crases: nenhuma pode ter sumido.
    Identificadores snake_case que não são tool precisam ser coleção, campo ou operador do `describe_schema`."""
    tools = set(tools_of(srv))
    texto = srv.mcp.instructions or ""
    citadas = set(re.findall(r"`([a-z]+(?:_[a-z0-9]+)+)(?:\(|`)", texto))
    from api.query_catalogo import OPS_GUIDE, SCHEMA
    esquema = json.dumps({"s": SCHEMA, "o": OPS_GUIDE})          # o describe_schema() sem collection virou índice: o catálogo inteiro vem daqui
    conhecidos = tools | set(re.findall(r"[a-z]+(?:_[a-z0-9]+)+", esquema))
    ausentes = sorted(c for c in citadas if c not in conhecidos)
    assert ausentes == [], f"instruções citam nomes que não são tool nem campo do schema: {ausentes}"


def test_perfis_do_mcp_tem_a_mesma_forma_da_api(srv, api, ctx):
    """Get_operator/get_municipio/get_uf devolvem o mesmo dado das rotas /operadoras, /municipios e /ufs."""
    from tests.products.api_contract import ALLOWED
    cnpj, ibge, uf = ctx["cnpj"], ctx["ibge"], ctx["uf"]
    op = call(srv, "operadora_detalhe", {"cnpj": cnpj})
    assert op == api.get(f"/api/v1/operadoras/{cnpj}", headers=ALLOWED).json()
    assert set(call(srv, "operadora_detalhe", {"cnpj": cnpj, "blocos": ["scm"]})) <= {"snapshot_date", "cnpj", "scm", "rede"}
    mun = call(srv, "municipio_detalhe", {"ibge": ibge})
    assert mun == api.get(f"/api/v1/municipios/{ibge}", headers=ALLOWED).json()
    ufp = call(srv, "uf_detalhe", {"uf": uf.lower()})
    assert ufp["totais"] == api.get(f"/api/v1/ufs/{uf}", headers=ALLOWED).json()["totais"]
    assert not (PII_KEYS & _keys_deep([op, mun, ufp]))
    for tool, args in (("uf_detalhe", {"uf": "XX"}), ("municipio_detalhe", {"ibge": "0000000"}), ("operadora_detalhe", {"cnpj": cnpj, "blocos": ["zz"]})):
        with pytest.raises(Exception):
            run(srv.mcp.call_tool(tool, args))



def test_asn_interconexao_mcp_e_rest_dizem_o_mesmo_e_o_carregador_e_o_par_do_ptt(srv, api):
    """ASN-E1: o carregador é o último AS de cada caminho gravado (o par do PTT); MCP e REST devolvem o mesmo."""
    from tests.products.api_contract import ALLOWED
    vistos = 0
    for item in api.get("/api/v1/asns", params={"limit": 100}, headers=ALLOWED).json()["items"]:
        rest = api.get(f"/api/v1/asns/{item['asn']}/interconexao", headers=ALLOWED)
        if rest.status_code != 200:
            continue
        r = rest.json()
        assert call(srv, "asn_interconexao", {"asn": item["asn"]}) == r
        doc = api.get(f"/api/v1/asns/{item['asn']}/paths", headers=ALLOWED).json()
        for o in r["origem_sem_direto"]:
            caminhos = (doc.get("ixp_paths") or {}).get(o["ixp"]) or []
            ultimos = {c[-1] for c in caminhos if c}
            assert {c["asn"] for c in o["carregadores"]} <= ultimos and item["asn"] not in {c["asn"] for c in o["carregadores"]}
            if caminhos:
                assert o["carregadores"], (item["asn"], o["ixp"])                         # caminho observado sempre tem quem entrega
                vistos += 1
    assert vistos, "o dataset sintético deveria ter um AS originando num PTT sem ser par direto, com caminho gravado"


def _keys_deep(x, found=None):
    found = set() if found is None else found
    if isinstance(x, dict):
        for k, v in x.items():
            found.add(k)
            _keys_deep(v, found)
    elif isinstance(x, list):
        for v in x:
            _keys_deep(v, found)
    return found


def test_query_cobre_todas_as_outorgas_e_as_colecoes_moveis(srv, ctx):
    """`stfcs` e `seacs` entram no `query`; as de outorga estão nas instruções e todas no describe_schema."""
    for colecao in ("scms", "smps", "stfcs", "seacs", "operadoras_movel", "acessos_movel_municipio"):
        r = call(srv, "query", {"collection": colecao, "limit": 1})
        assert isinstance(r, dict) and "total" in r, (colecao, r)
    assert call(srv, "query", {"collection": "stfcs", "limit": 1})["total"] > 0
    esquema = call(srv, "describe_schema", {"collection": "seacs"})
    assert esquema["collection"] == "seacs" and any(f["name"] == "cnpj" for f in esquema["campos"])
    for nome in ("scms", "smps", "stfcs", "seacs"):
        assert nome in srv.mcp.instructions, nome
    todas = {c["collection"] if isinstance(c, dict) else c for c in call(srv, "describe_schema", {})["collections"]}
    assert {"operadoras_movel", "acessos_movel_municipio"} <= todas


def test_sici_movel_nas_quatro_tools_e_serie_nacional(srv, ctx):
    """`servico="movel"` em operator_accesses, top_operators, municipality_broadband e access_history; sem id, access_history é nacional."""
    top = call(srv, "operadora_ranking", {"servico": "movel", "limit": 3})
    assert top["servico"] == "movel" and top["items"], top
    assert "acessos_m2m" in top["items"][0] and "capacidade_mbps" not in top["items"][0]
    cnpj = top["items"][0]["cnpj"]
    op = call(srv, "operadora_acessos", {"cnpj": cnpj, "servico": "movel"})
    assert op["servico"] == "movel" and op["cnpj"] == cnpj and "divergencia_apnic_anatel" not in op
    hist = call(srv, "historico_acessos", {"cnpj": cnpj, "servico": "movel"})
    assert hist["servico"] == "movel" and hist["serie"]
    nacional = call(srv, "historico_acessos", {"servico": "movel"})
    assert nacional["serie_nacional"] and "distrib_modalidade" in nacional and "cnpj" not in nacional
    fixa = call(srv, "historico_acessos", {})
    assert fixa["servico"] == "fixa" and fixa["serie_nacional"] and "distrib_velocidade" in fixa
    mun = call(srv, "municipio_banda_larga", {"ibge": ctx["ibge_movel"], "servico": "movel"})
    assert mun["servico"] == "movel" and mun.get("operadores")
    assert call(srv, "operadora_ranking", {"servico": "movel", "ibge": ctx["ibge_movel"]})["servico"] == "movel"


def test_sici_servico_invalido_e_capacidade_movel_sao_recusados(srv):
    import pytest
    from mcp.server.fastmcp.exceptions import ToolError
    with pytest.raises(ToolError, match="servico inválido"):
        call(srv, "operadora_ranking", {"servico": "satelite"})
    with pytest.raises(ToolError, match="capacidade"):
        call(srv, "operadora_ranking", {"servico": "movel", "metric": "capacidade"})


def test_list_outorgas_e_get_outorgas_batem_com_a_rota(srv, api, ctx):
    """As tools usam a mesma consulta de GET /outorgas (uma função, dois transportes)."""
    import pytest
    from mcp.server.fastmcp.exceptions import ToolError
    from tests.products.api_contract import ALLOWED
    for params in ({}, {"servico": "SCM,STFC", "todos": True}, {"uf": "SP", "com_asn": True}, {"q": "a", "sort_by": "razao_social", "sort_desc": False}):
        rest = api.get("/api/v1/outorgas", params={**params, "limit": 20, "date": ctx["date"]}, headers=ALLOWED).json()
        mcp_r = call(srv, "outorga_lista", {**params, "limit": 20, "date": ctx["date"]})
        assert mcp_r == rest, params
    item = call(srv, "outorga_lista", {"limit": 1})["items"][0]
    por = call(srv, "outorga_detalhe", {"cnpj": item["cnpj"]})
    assert por["cnpj"] == item["cnpj"] and set(por["servicos"]) == set(item["servicos"])
    assert call(srv, "outorga_detalhe", {"cnpj": item["cnpj"], "servico": item["servicos"][0]})["servicos"].keys() == {item["servicos"][0]}
    with pytest.raises(ToolError, match="servico inválido"):
        call(srv, "outorga_lista", {"servico": "XYZ"})
    with pytest.raises(ToolError, match="sem outorgas|CNPJ inválido"):     # CNPJ com DV errado já é recusado na entrada (mcp_server/entrada.py)
        call(srv, "outorga_detalhe", {"cnpj": "00000000000000"})


def test_cadastro_da_receita_com_telefone_nao_sai_pelo_mcp(srv, ctx, monkeypatch):
    """`geo_org` (cadastro da Receita) traz `ddd_telefone_1/2`; get_asn, get_asns e get_prefix não podem repassá-lo."""
    original = srv._store.asn_full

    def com_telefone(d, asn):
        doc = original(d, asn)
        if doc is None:
            return None
        return {**doc, "geo_org": {**(doc.get("geo_org") or {}), "razao_social": "EMPRESA X", "ddd_telefone_1": "1133334444",
                                   "ddd_telefone_2": "11999998888", "email": "x@exemplo.com.br"}}

    monkeypatch.setattr(srv._store, "asn_full", com_telefone)
    for resposta in (call(srv, "asn_detalhe", {"asn": int(ctx["asn"])}), call(srv, "asn_lote", {"asns": [int(ctx["asn"])]}),
                     call(srv, "rota_prefixo", {"prefix": ctx["prefix"]})):
        texto = json.dumps(resposta, ensure_ascii=False)
        for valor in ("1133334444", "11999998888", "x@exemplo.com.br"):
            assert valor not in texto, (valor, texto[:200])
        assert not {k for k in _keys(resposta) if e_chave_de_contato(k)}
    doc = call(srv, "asn_detalhe", {"asn": int(ctx["asn"])})
    assert doc["geo_org"]["razao_social"] == "EMPRESA X"             # o resto do cadastro continua
    assert set(doc["contacts_available"]) >= {"peeringdb", "anatel", "receita", "total"}      # só contagens


def test_asn_exposicao_por_asn_e_por_uf_igual_a_api_e_exige_um_dos_dois(srv, api, ctx):
    """Uma tool só cobre o ASN e a UF (mesmas fontes das rotas); contagens do Shodan com atribuição, nunca host individual; ausência não é zero."""
    from tests.products.api_contract import ALLOWED

    asn = int(ctx["asn_exposicao"])
    mcp_asn = call(srv, "asn_exposicao", {"asn": asn})
    assert mcp_asn == api.get(f"/api/v1/asns/{asn}/exposicao", headers=ALLOWED).json() and "Shodan" in mcp_asn["fonte"]["atribuicao"]
    uf = next(u for u in ("SP", "RJ", "MG", "PR", "RS", "BA", "SC", "AM", "PE", "CE") if api.get(f"/api/v1/exposicao/ufs/{u}", headers=ALLOWED).status_code == 200)
    assert call(srv, "asn_exposicao", {"uf": uf}) == api.get(f"/api/v1/exposicao/ufs/{uf}", headers=ALLOWED).json()
    texto = json.dumps(mcp_asn, ensure_ascii=False)
    assert "matches" not in texto and "ip_str" not in texto
    for args in ({}, {"asn": asn, "uf": uf}, {"asn": 4294967295}):
        with pytest.raises(Exception):
            call(srv, "asn_exposicao", args)


def test_economic_group_por_cnpj_e_por_id_e_ixp_assinantes(srv, api, ctx):
    """O grupo por CNPJ e por id são o mesmo; relações diretas só quando se parte do CNPJ; ixp_assinantes é a rota resumida."""
    import pytest
    from mcp.server.fastmcp.exceptions import ToolError
    from tests.products.api_contract import ALLOWED
    g = call(srv, "operadora_grupo", {"cnpj": ctx["cnpj"], "limit": 2})
    assert g["cnpjs_total"] >= 1 and len(g["cnpjs"]) <= 2 and "municipios_total" in g and "relacionadas" in g
    assert "nomes_em_comum" not in json.dumps(g)                     # nome de sócio pessoa física não sai pelo MCP
    assert any(c["cnpj"] == ctx["cnpj"] for c in call(srv, "operadora_grupo", {"cnpj": ctx["cnpj"], "limit": 200})["cnpjs"])
    por_id = call(srv, "operadora_grupo", {"grupo_id": g["grupo_id"], "limit": 2})
    assert por_id["grupo_id"] == g["grupo_id"] and "relacionadas" not in por_id and por_id["assinantes"] == g["assinantes"]
    rest = api.get("/api/v1/grupos", params={"date": ctx["date"]}, headers=ALLOWED).json()["grupos"]
    assert g["assinantes"] == next(x for x in rest if x["grupo_id"] == g["grupo_id"])["assinantes"]       # mesmo número da rota
    for args, erro in (({}, "Informe grupo_id ou cnpj"), ({"cnpj": "123"}, "CNPJ inválido"), ({"grupo_id": "nao-existe"}, "não encontrado")):
        with pytest.raises(ToolError, match=erro):
            call(srv, "operadora_grupo", args)
    a = call(srv, "ixp_assinantes", {"code": ctx["code"], "limit": 3})
    rota = api.get(f"/api/v1/ixps/{ctx['code']}/assinantes", params={"date": ctx["date"]}, headers=ALLOWED).json()
    assert a["assinantes_diretos"] == rota["assinantes_diretos"] and a["assinantes_total"] == rota["assinantes_total"]
    assert a["asns_total"] == len(rota["asns"]) and len(a["asns"]) <= 3 and set(a["peers_top"]) == set(rota["peers"])
    with pytest.raises(ToolError, match="não encontrado|Código de PTT desconhecido"):     # código desconhecido é recusado na entrada
        call(srv, "ixp_assinantes", {"code": "zz"})


def test_get_prefix_por_ip_e_get_uf_sem_argumento_batem_com_as_rotas(srv, api, ctx):
    """`get_prefix(ip=)` é o /prefixes/lookup; `get_uf()` sem UF é o /ufs."""
    import pytest
    from mcp.server.fastmcp.exceptions import ToolError
    from tests.products.api_contract import ALLOWED
    rota = api.get("/api/v1/prefixes/lookup", params={"ip": ctx["ip"], "date": ctx["date"]}, headers=ALLOWED).json()
    tool = call(srv, "rota_prefixo", {"ip": ctx["ip"], "date": ctx["date"]})
    assert tool["consulta"] == rota["consulta"] == ctx["ip"] and tool["prefix"] == rota["prefix"]
    assert call(srv, "rota_prefixo", {"prefix": ctx["prefix"]})["prefix"] == ctx["prefix"] and "consulta" not in call(srv, "rota_prefixo", {"prefix": ctx["prefix"]})
    for args, erro in (({}, "Informe prefix ou ip"), ({"ip": "não-é-ip"}, "não é um endereço IP válido"), ({"ip": "203.0.113.7"}, "Nenhum prefixo conhecido")):
        with pytest.raises(ToolError, match=erro):
            call(srv, "rota_prefixo", args)
    ufs = api.get("/api/v1/ufs", params={"date": ctx["date"]}, headers=ALLOWED).json()
    lista = call(srv, "uf_detalhe", {"date": ctx["date"]})
    assert lista["total"] == ufs["total"] == len(lista["items"]) and lista["items"] == ufs["items"]
    assert call(srv, "uf_detalhe", {"uf": ctx["uf"]})["totais"]


def _preenche(v, c):
    if isinstance(v, str):
        return v.format(**c) if "{" in v else v
    if isinstance(v, dict):
        return {k: _preenche(x, c) for k, x in v.items()}
    if isinstance(v, list):
        return [_preenche(x, c) for x in v]
    return v


def test_perguntas_de_referencia(srv, ctx):
    """As 30 perguntas de `tests/contracts/perguntas_mcp.json` têm a tool esperada, com argumentos válidos e a resposta esperada."""
    from mcp.server.fastmcp.exceptions import ToolError
    from tests.synth.world import MUNICIPIOS
    perguntas = json.loads((Path(__file__).resolve().parents[1] / "contracts" / "perguntas_mcp.json").read_text(encoding="utf-8"))["perguntas"]
    c = {**ctx, "lat": MUNICIPIOS[0][3], "lon": MUNICIPIOS[0][4], "municipio": MUNICIPIOS[0][1]}
    nomes = set(tools_of(srv))
    assert len(perguntas) == 30 and [p["id"] for p in perguntas] == list(range(1, 31))
    falhas = []
    for p in perguntas:
        assert p["tool"] in nomes, f"pergunta {p['id']}: a tool {p['tool']} não existe"
        args = _preenche(p["args"], c)
        for chave in ("asn",):
            if isinstance(args.get(chave), str):
                args[chave] = int(args[chave])
        try:
            r = call(srv, p["tool"], args)
        except ToolError as exc:
            if p.get("indisponivel_ok") and "indisponível" in str(exc):
                continue
            falhas.append((p["id"], str(exc)[:120]))
            continue
        faltam = [k for k in p["espera"] if not (isinstance(r, dict) and k in r)]
        if faltam:
            falhas.append((p["id"], f"faltam {faltam}"))
    assert not falhas, falhas



# ---------------------------------------------------------------------------
# organização do MCP
# ---------------------------------------------------------------------------

def _sem_aviso(r):
    return {k: v for k, v in r.items() if k != "aviso_obsoleta"} if isinstance(r, dict) else r


def test_nomes_por_dominio_e_aliases_ocultos(srv):
    """Os nomes antigos não aparecem na listagem, seguem chamáveis e dizem qual é o substituto; a listagem tem só nomes de domínio."""
    visiveis = set(tools_of(srv))
    dominios = ("asn_", "ixp_", "rota_", "operadora_", "municipio_", "uf_", "outorga_", "infra_", "historico_", "geo_", "cdn_", "facility_", "grupo_")
    fora = sorted(n for n in visiveis if not n.startswith(dominios) and n not in {"query", "describe_schema", "viz"})
    assert fora == [], f"tool visível sem nome de domínio: {fora}"
    assert len(visiveis) <= 58, f"{len(visiveis)} tools visíveis"   # teto: cada tool nova é uma escolha consciente (+2: contatos com chave)
    todas = set(srv.mcp._tool_manager._tools)
    assert set(srv.mcp.ocultas) == todas - visiveis
    for antigo in sorted(srv.mcp.ocultas):
        assert antigo not in visiveis
        assert "[obsoleta" in srv.mcp._tool_manager._tools[antigo].description, antigo


def test_alias_responde_igual_a_tool_nova(srv, ctx):
    pares = [("get_asn", {"asn": int(ctx["asn"])}, "asn_detalhe", {"asn": int(ctx["asn"])}),
             ("get_ixp", {"code": ctx["code"]}, "ixp_detalhe", {"code": ctx["code"]}),
             ("list_snapshots", {}, "historico_snapshots", {}),
             ("get_snapshot", {"date": ctx["date"]}, "historico_snapshots", {"date": ctx["date"]}),
             ("ixp_members", {"code": ctx["code"]}, "ixp_participantes", {"code": ctx["code"], "visao": "membros"}),
             ("ixp_peers", {"code": ctx["code"], "afi": "v4"}, "ixp_participantes", {"code": ctx["code"], "visao": "peers", "afi": "v4"}),
             ("get_asn_paths", {"asn": int(ctx["asn"])}, "asn_rede", {"asn": int(ctx["asn"]), "visao": "caminhos"}),
             ("get_asn_ixp_peers", {"asn": int(ctx["asn"])}, "asn_rede", {"asn": int(ctx["asn"]), "visao": "ixp_peers"}),
             ("ixp_estimated_users", {"code": ctx["code"]}, "ixp_usuarios", {"code": ctx["code"]}),
             ("all_ixp_estimated_users", {}, "ixp_usuarios", {}),
             ("list_external_ixps", {}, "ixp_externo", {}),
             ("get_external_ixp", {"code": ctx["ext_code"]}, "ixp_externo", {"code": ctx["ext_code"]}),
             ("rpki_summary", {}, "rota_rpki", {}),
             ("hilbert_v4", {}, "viz", {"kind": "hilbert_v4"}),
             ("map_pix", {}, "viz", {"kind": "map_pix"}),
             ("asn_geo", {"asn": int(ctx["asn"])}, "viz", {"kind": "asn_geo", "asn": int(ctx["asn"])}),
             ("ixp_hilbert_v4", {"code": ctx["code"]}, "viz", {"kind": "ixp_hilbert_v4", "code": ctx["code"]})]
    for antigo, a_args, novo, n_args in pares:
        velho, nova = call(srv, antigo, a_args), call(srv, novo, n_args)
        assert "aviso_obsoleta" in velho and novo in velho["aviso_obsoleta"].replace("`", "") or antigo in {"ixp_peers"}, antigo
        assert _sem_aviso(velho) == {k: v for k, v in nova.items() if k != "snapshot_date" or "snapshot_date" in velho}, f"{antigo} ≠ {novo}"


def test_envelope_padrao_snapshot_date_em_toda_tool_com_data(srv, ctx):
    sem = {}
    for name, t in tools_of(srv).items():
        if "date" not in (t.inputSchema or {}).get("properties", {}):
            continue
        r = _chamar(srv, name, ctx, t)
        if isinstance(r, dict) and "snapshot_date" not in r:
            sem[name] = sorted(r)[:5]
    assert sem == {}


def test_viz_valida_kind_e_argumentos(srv, ctx):
    from mcp.server.fastmcp.exceptions import ToolError
    with pytest.raises(ToolError, match="kind inválido"):
        call(srv, "viz", {"kind": "nao_existe"})
    with pytest.raises(ToolError, match="faltam argumentos: asn"):
        call(srv, "viz", {"kind": "asn_geo"})
    r = call(srv, "viz", {"kind": "ixp_geo", "code": ctx["code"], "layer": "asns_members"})
    assert r["layer"] == "asns_members" and "feature_count" in r
    with pytest.raises(ToolError, match="visao inválida"):
        call(srv, "asn_rede", {"asn": int(ctx["asn"]), "visao": "x"})


def test_rota_rpki_sem_prefixo_resume_e_com_prefixo_valida(srv, ctx):
    assert "br_asns_with_roa" in call(srv, "rota_rpki", {})
    assert "estado" in call(srv, "rota_rpki", {"prefix": ctx["prefix"]})


def test_guia_so_cita_tools_visiveis_e_cobre_todas(srv):
    """A tabela `tarefa → tool` que gera as instruções: toda tool citada existe e toda tool visível está lá (ou é do próprio guia)."""
    from mcp_server import guia
    visiveis = set(tools_of(srv))
    citadas = {n for _, tools, _ in guia.TAREFAS for n in tools}
    assert citadas <= visiveis, sorted(citadas - visiveis)
    assert visiveis - citadas <= guia.FORA_DO_GUIA, sorted(visiveis - citadas - guia.FORA_DO_GUIA)
    assert set(guia.DETALHE_DA_COLLECTION.values()) - {None} <= visiveis
    assert srv.mcp.instructions == guia.instrucoes()


def test_instrucoes_nao_aumentaram(srv):
    """Tetos de tamanho para as instruções e as descrições das tools (tokens que o cliente paga em toda sessão)."""
    # +tabela dos 40 códigos de PTT e as 49 collections do
    # `query`, que os modelos menores não achavam; em troca as descrições das tools caíram de ~42 mil para ~11 mil caracteres (teto do total abaixo)
    assert len(srv.mcp.instructions) <= 6500
    descricoes = sum(len(srv.mcp._tool_manager._tools[n].description or "") for n in tools_of(srv))
    assert len(srv.mcp.instructions) + descricoes <= 18000, descricoes


def test_describe_schema_liga_tarefas_e_collections_a_tools(srv):
    """Índice sem collection: toda collection tem a tool de detalhe; com collection, os campos vêm primeiro e só as receitas dela."""
    from mcp_server import guia
    todo = call(srv, "describe_schema", {})
    assert set(todo["ferramenta_detalhe"]) >= set(todo["collections"])
    um = call(srv, "describe_schema", {"collection": "scms"})
    assert um["ferramenta_detalhe"] == "outorga_detalhe" and list(um)[:4] == ["collection", "descricao", "chave", "campos"]
    assert all((r.get("args") or {}).get("collection") == "scms" for r in um["receitas"])
    visiveis = set(tools_of(srv))
    assert {t for x in guia.tarefas() for t in x["tools"]} <= visiveis


def test_mcp_ixps_membro_e_sessao_rs_na_collection_asns_com_alias_do_nome_antigo(srv):
    """PT-15: `ixps_direct` do `query` era o cadastro de participantes; o MCP descreve os dois campos novos e avisa de quem usa o antigo."""
    campos = {c["name"]: c for c in call(srv, "describe_schema", {"collection": "asns"})["campos"]}
    assert {"ixps_membro", "ixps_sessao_rs"} <= set(campos) and campos["ixps_direct"]["description"].startswith("[obsoleto")
    antigo = call(srv, "query", {"collection": "asns", "filter": {"field": "ixps_direct", "op": "exists", "value": True}, "limit": 1})
    assert "ixps_membro" in antigo["aviso_obsoleta"]
    novo = call(srv, "query", {"collection": "asns", "filter": {"field": "ixps_sessao_rs", "op": "exists", "value": True}, "limit": 1})
    assert "aviso_obsoleta" not in novo


def test_resources_por_entidade_e_prompts_tematicos(srv, ctx):
    ent = {f"{SITE.mcp_esquema}://asn/{ctx['asn']}": "asn", f"{SITE.mcp_esquema}://ixp/{ctx['code']}": "code",
           f"{SITE.mcp_esquema}://operadora/{ctx['cnpj']}": "cnpj", f"{SITE.mcp_esquema}://uf/{ctx['uf']}": "uf", f"{SITE.mcp_esquema}://municipio/{ctx['ibge']}": "ibge"}
    for uri, _ in ent.items():
        doc = json.loads("".join(c.content for c in run(srv.mcp.read_resource(uri))))
        assert doc, uri
        assert not (PII_KEYS & _keys(doc)), uri
    assert json.loads("".join(c.content for c in run(srv.mcp.read_resource(f"{SITE.mcp_esquema}://asn/{ctx['asn']}"))))["asn"] == int(ctx["asn"])
    visiveis = set(tools_of(srv))
    for nome, args in (("diagnostico_de_as", {"asn": "64500"}), ("potencial_de_ptt", {"code": "sp"}),
                       ("mercado_de_municipio", {"ibge": "1"}), ("grupo_economico_oculto", {"cnpj": "1"})):
        texto = run(srv.mcp.get_prompt(nome, args)).messages[0].content.text
        citadas = set(re.findall(r"`([a-z]+(?:_[a-z0-9]+)+|query)[(`]", texto))
        assert citadas - {"mesmo_grupo", "relacionadas_parcial"} <= visiveis, (nome, sorted(citadas - visiveis))


def test_historico_serie_e_mudancas_no_mcp(srv, ctx):
    """As duas tools de histórico dão o mesmo que a API REST e recusam escopo e métrica inválidos."""
    from mcp.server.fastmcp.exceptions import ToolError
    from tests.synth.world import T0, T1

    s = call(srv, "historico_serie", {"escopo": "asn:64503"})
    assert [p["date"] for p in s["snapshots"]] == [T0, T1]
    assert call(srv, "historico_serie", {"escopo": "uf:PR"})["uf"] == "PR"
    assert call(srv, "historico_serie", {"escopo": "ixp:" + ctx["code"]})["ixp"] == ctx["code"]
    t = call(srv, "historico_serie", {"escopo": "brasil", "metrica": "n_asns"})
    assert t["total"] == 2 and t["variacao"]["de"] == T0 and t["variacao"]["para"] == T1
    u = call(srv, "historico_serie", {"escopo": "uf:PR", "metrica": "users"})
    assert [p["valor"] for p in u["serie"]] and u["escopo"] == "uf:PR"
    for args, erro in (({"escopo": "brasil"}, "exige `metrica`"), ({"escopo": "x"}, "escopo deve ser"), ({"escopo": "uf:PR", "metrica": "zz"}, "Sem a métrica"),
                       ({"escopo": "asn:64503", "metrics": "zz"}, "metrics inválidas")):
        with pytest.raises(ToolError, match=erro):
            call(srv, "historico_serie", args)
    m = call(srv, "historico_mudancas", {"estado": "todos"})
    assert m["total"] > 0 and all(e["estado"] in ("pendente", "confirmado", "revertido") for e in m["items"])
    assert call(srv, "historico_mudancas", {"resumo": True})["total"] == m["total"]
    d = call(srv, "historico_mudancas", {"comparar": T0})
    assert d["a"] == T0 and d["b"] == T1 and d["eventos"]["total"] == m["total"]
    with pytest.raises(ToolError, match="estado inválido"):
        call(srv, "historico_mudancas", {"estado": "x"})


def test_resources_de_historico(srv):
    """`<esquema>://changes/latest` e `<esquema>://tendencias` leem a camada de histórico e não trazem nome de empresa nem contato."""
    ch = json.loads("".join(c.content for c in run(srv.mcp.read_resource(SITE.uri("changes/latest")))))
    assert ch["snapshot_date"] and "items" in ch
    tend = json.loads("".join(c.content for c in run(srv.mcp.read_resource(SITE.uri("tendencias")))))
    assert tend["snapshots_com_historico"] == 2 and tend["tendencias"]["n_asns"]["total"] == 2
    assert "razao_social" not in json.dumps([ch, tend]) and "@" not in json.dumps([ch, tend])


def test_nenhuma_tool_geolocaliza_prefixo_ou_ip(srv, ctx):
    """Nenhuma tool devolve lat/lon/cidade de um prefixo ou IP (espelha `test_t4_geo_prefixo.py`)."""
    from tests.products.test_t4_geo_prefixo import _achados

    vazamentos = []
    for name, t in tools_of(srv).items():
        r = _chamar(srv, name, ctx, t)
        for a in list(_achados(r))[:3] if isinstance(r, (dict, list)) else []:
            vazamentos.append(f"{name} → {a}")
    # as tools de prefixo, com os argumentos que as fariam vazar
    for nome, args in (("map_prefixes", {"full": True}), ("list_prefixes", {"limit": 5}),
                       ("query", {"collection": "global_prefixes", "limit": 5})):
        if nome in tools_of(srv):
            r = call(srv, nome, args)
            vazamentos += [f"{nome}{args} → {a}" for a in list(_achados(r))[:3]]
    assert not vazamentos, "geolocalização por prefixo/IP exposta pelo MCP:\n" + "\n".join(vazamentos)


def test_codigo_de_ixp_com_traversal_nao_le_arquivo_fora_do_publicado(srv, pipeline):
    """`code` com `../` não pode ler `.json` de `raw/` (contatos brutos do PeeringDB): é erro de validação."""
    base, _ = pipeline
    d = srv._store.latest()
    pasta = base / "raw" / d / "summary"
    pasta.mkdir(parents=True, exist_ok=True)
    canario = pasta / "canario-s01.json"
    canario.write_text(json.dumps({"segredo": "CONTEUDO-SECRETO-S01", "email": "canario@example.org"}), encoding="utf-8")
    try:
        for tool in ("ixp_externo", "ixp_detalhe"):
            for code in (f"../../../raw/{d}/summary/canario-s01", f"..%2f..%2f..%2fraw/{d}/summary/canario-s01", "/etc/passwd", "a\\b", "x" * 80):
                try:
                    out = call(srv, tool, {"code": code})
                except Exception as exc:  # noqa: BLE001  (a tool devolve erro de validação)
                    out = str(exc)
                assert "CONTEUDO-SECRETO-S01" not in json.dumps(out) and "@example.org" not in json.dumps(out), (tool, code)
        # Tools de grupo e de mudanças: `grupo_id` só é procurado na lista de grupos e `asn` é inteiro; nenhum vira caminho.
        for code in (f"../../../raw/{d}/summary/canario-s01", "/etc/passwd", "grp_../../x"):
            try:
                out = call(srv, "grupo_perfil", {"grupo_id": code, "blocos": ["mercado", "regulatorio", "tecnico", "relacoes"]})
            except Exception as exc:  # noqa: BLE001
                out = str(exc)
            assert "CONTEUDO-SECRETO-S01" not in json.dumps(out) and "@example.org" not in json.dumps(out), ("grupo_perfil", code)
    finally:
        canario.unlink(missing_ok=True)


def test_toda_tool_visivel_tem_descricao_curta_e_toda_collection_esta_nas_instrucoes(srv):
    """O que vai ao modelo é `mcp_server/descricoes.py` e as instruções citam todas as collections."""
    from api.query_catalogo import SCHEMA
    from mcp_server import guia
    from mcp_server.descricoes import DESCRICOES
    visiveis = set(tools_of(srv))
    assert visiveis <= set(DESCRICOES), sorted(visiveis - set(DESCRICOES))
    for nome in visiveis:
        assert srv.mcp._tool_manager._tools[nome].description == com_identidade(DESCRICOES[nome]), nome
    agrupadas = {c for _, cols in guia.GRUPOS_COLLECTIONS for c, _ in cols}
    assert agrupadas == set(SCHEMA), (sorted(set(SCHEMA) - agrupadas), sorted(agrupadas - set(SCHEMA)))
    for codigo in ("ce", "vix", "mao"):
        assert f"{codigo}=" in srv.mcp.instructions


def test_toda_tool_e_anotada_como_so_leitura(srv):
    """`readOnlyHint` em todas, inclusive aliases ocultos e as geradas das capacidades: nenhuma tool escreve."""
    todas = srv.mcp._tool_manager.list_tools()
    assert todas
    sem = [t.name for t in todas if not (t.annotations and t.annotations.readOnlyHint is True
                                         and t.annotations.idempotentHint is True and t.annotations.openWorldHint is False)]
    assert sem == [], sem
    visiveis = run(srv.mcp.list_tools())
    assert all(t.annotations and t.annotations.readOnlyHint for t in visiveis)



def test_collection_com_nome_antigo_responde_pela_nova_com_aviso(srv):
    """D12: `omissao_sici` virou `sem_declaracao_sici`; o nome antigo é alias com `aviso_obsoleta` (query e describe_schema)."""
    novo = call(srv, "query", {"collection": "sem_declaracao_sici", "limit": 5})
    velho = call(srv, "query", {"collection": "omissao_sici", "limit": 5})
    assert "aviso_obsoleta" not in novo and "sem_declaracao_sici" in velho["aviso_obsoleta"]
    assert _sem_aviso(velho) == novo
    d_novo, d_velho = call(srv, "describe_schema", {"collection": "sem_declaracao_sici"}), call(srv, "describe_schema", {"collection": "omissao_sici"})
    assert d_velho["collection"] == "sem_declaracao_sici" and "aviso_obsoleta" in d_velho and "aviso_obsoleta" not in d_novo
    assert "omissao_sici" not in call(srv, "describe_schema", {})["collections"]


def test_pt19_agregacao_do_query_e_igual_na_rest_e_no_mcp(srv, api):
    """PT-19 / TRANSV-E10: mesmo código na REST e no MCP; sort por alias, limit, page, `total_grupos` e `count` com campo."""
    from tests.products.api_contract import ALLOWED
    corpo = {"group_by": ["empresa"], "aggregate": [{"fn": "sum", "field": "acessos"}, {"fn": "count"}, {"fn": "count", "field": "asns", "as": "com_asns"}],
             "sort": [{"field": "sum_acessos", "dir": "desc"}]}
    todos = call(srv, "query", {"collection": "acessos_municipio", **corpo})
    assert todos["total_grupos"] == len(todos["groups"]) > 2
    soma = [g["sum_acessos"] for g in todos["groups"]]
    assert soma == sorted(soma, reverse=True) and all(g["com_asns"] <= g["count"] for g in todos["groups"])
    rest = api.post("/api/v1/query/acessos_municipio", json={**corpo, "limit": 2}, headers=ALLOWED).json()
    mcp = call(srv, "query", {"collection": "acessos_municipio", **corpo, "limit": 2})
    assert rest == mcp and len(rest["groups"]) == 2 and rest["total_grupos"] == todos["total_grupos"] and rest["groups"] == todos["groups"][:2]
    p2 = api.post("/api/v1/query/acessos_municipio", json={**corpo, "limit": 2, "page": 2}, headers=ALLOWED).json()
    assert p2["groups"] == todos["groups"][2:4] == call(srv, "query", {"collection": "acessos_municipio", **corpo, "limit": 2, "page": 2})["groups"]
    ruim = api.post("/api/v1/query/acessos_municipio", json={**corpo, "sort": [{"field": "acessos"}]}, headers=ALLOWED)
    assert ruim.status_code == 400 and "sum_acessos" in ruim.json()["detail"]


def test_pt19_mes_referencia_do_sici_em_municipios_e_acessos_municipio(srv, api):
    """PT-19 / TRANSV-E11: as duas collections trazem o mês do SICI, no schema e nas linhas, na REST e no MCP."""
    from tests.products.api_contract import ALLOWED
    d = srv._store.resolve_date(None)
    mes = srv._store.sici_meta(d)["mes_referencia"]
    assert re.fullmatch(r"\d{4}-\d{2}", mes)
    for colecao in ("municipios", "acessos_municipio"):
        assert any(c["name"] == "mes_referencia" for c in call(srv, "describe_schema", {"collection": colecao})["campos"]), colecao
        linhas = call(srv, "query", {"collection": colecao, "limit": 5})["items"]
        assert linhas and {r["mes_referencia"] for r in linhas} == {mes}, colecao
        filtrado = call(srv, "query", {"collection": colecao, "filter": {"field": "mes_referencia", "op": "eq", "value": mes}, "limit": 1})
        assert filtrado["total"] == call(srv, "query", {"collection": colecao, "limit": 1})["total"]
        rest = api.post(f"/api/v1/query/{colecao}", json={"limit": 1}, headers=ALLOWED).json()
        assert rest["items"][0]["mes_referencia"] == mes


def test_describe_schema_traz_fonte_selo_e_licenca_e_indice_sem_truncar_o_aviso_do_sici(srv):
    """PT-20 / TRANSV-E12 e E17: fonte, selo e licença por collection; "ixps" sem número fixo; aviso do SICI inteiro no índice."""
    um = call(srv, "describe_schema", {"collection": "bloqueios_asn"})
    assert um["selo"] == "fato" and um["uso_comercial_efetivo"] == "restrito" and [f["id"] for f in um["fontes"]] == ["ooni_bloqueios"]
    todo = call(srv, "describe_schema", {})
    assert set(todo["fonte_e_selo"]) == set(todo["collections"]) and todo["fonte_e_selo"]["bloqueios_asn"]["uso_comercial"] == "restrito"
    assert "mês de referência do SICI" in todo["collections"]["operadoras"] and not todo["collections"]["operadoras"].endswith("…")
    assert not any(c.isdigit() for c in todo["collections"]["ixps"]), todo["collections"]["ixps"]
    assert todo["ferramenta_detalhe"]["faixas_espectro"] is None
