# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4/T5 — pessoa natural (EI/MEI): nem o nome civil nem o ponto exato saem por tela, REST, MCP ou arquivo publicado (decisão D1, PT-11).

No dataset sintético, dois provedores viram titulares de pessoa natural ANTES do pipeline: o A é empresário individual pela natureza 213-5 (no cadastro por
ASN e na Receita), sem nome fantasia, com o CPF no fim da razão social; o B é MEI (opção do Simples na Receita), com nome fantasia. Os nomes civis e o ponto
exato da sede são plantados em todas as fontes que os carregam: cadastro por ASN, outorgas (SCM, SMP, STFC, SEAC), SICI, nome do AS (Registro.br) e membros
do PTT. O pipeline roda duas vezes:

- `publicado`: com a regra de publicação (`core.cpf.mascarar_snapshot` com o índice de pessoa natural): os arquivos publicados já saem sem o nome nem o ponto;
- `legado`: sem ela, como um snapshot publicado antes da regra: o arquivo tem o nome e o ponto, e a leitura (REST, MCP e motor de `query`) é que não os serve.

O teste varre os arquivos publicados, todas as tools e resources do MCP e todas as rotas GET da API (anônimo e allowlist, no contexto do A, do B e no padrão),
o `query` de todas as coleções (REST e MCP) e a busca, e falha se o nome civil, o CPF ou o ponto exato aparecerem. O CSV da tela é montado no navegador a partir
dessas mesmas respostas (`explorer/csv.ts`, `localizador/csv.ts`): o que a API não serve ele não exporta.

O ponto de PJ no mapa fica como está (D1 deixa "a reconciliar"); o teste confere que uma PJ segue com a coordenada do cadastro.
"""
import asyncio
import gzip
import json
import re
import shutil
import zipfile
from pathlib import Path

import pytest

from tests.products.api_contract import ALLOWED, ANON, discover, request_for
from tests.products.conftest import fake_pix
from tests.products.mcp_contract import SEM_DADOS_NO_SINTETICO, args_for
from tests.synth.world import T0, T1

CPF = "52998224725"                                  # CPF com dígitos verificadores válidos
NOME_A = "JOAOZINHO PLANTADO PTONZE"
NOME_B = "MARIAZINHA PLANTADA PTONZE"
FANTASIA_B = "Fibra Plantada B"
LAT, LON = -20.2711234, -40.2622345                  # ponto exato plantado (Vitória, ES; o centróide do município é outro)
CENTRO = (-21.0, -41.0)                              # centro das consultas `near` (o eco do centro não pode casar com o ponto plantado)
CENTROIDE_VITORIA = (-20.2839, -40.2902)             # config/municipios-centroides.json, 3205309
ENDERECO = {"logradouro": "Rua Plantada PT11", "numero": "777", "complemento": "Sala PT11", "bairro": "Bairro PT11", "cep": "29010123"}

SENSIVEL = re.compile(r"JOAOZINHO|MARIAZINHA|PLANTAD[OA] PTONZE|52998224725|\*\*\*982247\*\*|Plantada PT11|Sala PT11|Bairro PT11|(?<!\d)29010-?123(?!\d)", re.I)
PONTO = re.compile(r"-20\.271|-40\.262")
ROTAS_DE_MAPA = re.compile(r"^GET /api/v1/(map/|.*/geo\b|.*/mapa\b|outorgas/mapa|localizador)")

_NOMES_DE_CAMPO = ("razao_social", "nome_fantasia", "empresa", "name", "nome")


def _ler(p: Path):
    if p.name.endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(p.read_text(encoding="utf-8"))


def _gravar(p: Path, doc) -> None:
    if p.name.endswith(".gz"):
        with gzip.open(p, "wt", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False)
    else:
        p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def _cnpj_do_asn(base: Path):
    """Os dois provedores plantados: BR com outorga SCM e CNPJ próprio (não compartilhado), os de maior ASN (longe dos cenários numerados)."""
    resumo = base / "normalized" / T1 / "summary"
    orgs = _ler(resumo / "geo_orgs.json.gz")["orgs"]
    scm = _ler(resumo / "anatel_scm.json.gz")["by_cnpj"]
    por_cnpj: dict = {}
    for asn, o in orgs.items():
        por_cnpj.setdefault(o.get("cnpj"), []).append(int(asn))
    candidatos = sorted(a for c, asns in por_cnpj.items() if c in scm and len(asns) == 1 for a in asns)
    a, b = candidatos[-1], candidatos[-2]
    return (a, orgs[str(a)]["cnpj"]), (b, orgs[str(b)]["cnpj"])


def _plantar_nomes(doc, cnpjs: dict, estrutura: dict):
    """Em todo dicionário com `cnpj` (ou filho de um mapa por CNPJ) dos titulares plantados: nome civil nos campos de nome, e o ponto exato."""
    if isinstance(doc, list):
        for v in doc:
            _plantar_nomes(v, cnpjs, estrutura)
        return
    if not isinstance(doc, dict):
        return
    cnpj = doc.get("cnpj") if isinstance(doc.get("cnpj"), str) else None
    if cnpj in cnpjs:
        nome, fantasia = cnpjs[cnpj]
        for k in _NOMES_DE_CAMPO:
            if k in doc:
                doc[k] = fantasia if k == "nome_fantasia" else nome
        if "logradouro" in doc or "cep" in doc:
            doc.update(ENDERECO)
        if "lat" in doc:
            doc.update(lat=LAT, lon=LON, geo_confidence="exact_address")
    for k, v in doc.items():
        if isinstance(v, dict) and k in cnpjs:                       # mapa por CNPJ (`by_cnpj`, `cnpjs`)
            nome, fantasia = cnpjs[k]
            for c in _NOMES_DE_CAMPO:
                if c in v:
                    v[c] = fantasia if c == "nome_fantasia" else nome
        if isinstance(v, (dict, list)):
            _plantar_nomes(v, cnpjs, estrutura)


def _plantar_multas_e_erbs(resumo: Path, cnpjs: dict) -> None:
    """Multas e ERBs trazem o nome do titular em `entidade` (a razão social da Anatel): um EI e um MEI multados e donos de estações."""
    multas = _ler(resumo / "anatel_multas.json.gz")
    erbs = _ler(resumo / "anatel_erbs.json.gz")
    modelo = erbs["estacoes"][0]
    for i, (cnpj, (nome, _fantasia)) in enumerate(cnpjs.items()):
        multas["empresas"].append({"raiz": cnpj[:8], "grupo": "SCM", "entidade": nome, "cnpjs": [cnpj], "uf": "ES", "multas": 2, "original": 200.0, "pago": 0.0,
                                   "saldo": 100.0, "situacoes": {"Devedor": 2}, "anos": {"2025": 2}})
        erbs["estacoes"].append({**modelo, "fistel": f"5990000{i}", "estacao": f"pt11{i}", "marca": "MARCA PLANTADA", "entidade": nome, "cnpj": cnpj})
    _gravar(resumo / "anatel_multas.json.gz", multas)
    _gravar(resumo / "anatel_erbs.json.gz", erbs)


def _plantar(base: Path) -> dict:
    (a, cnpj_a), (b, cnpj_b) = _cnpj_do_asn(base)
    nome_a = f"{NOME_A} {CPF}"
    cnpjs = {cnpj_a: (nome_a, ""), cnpj_b: (NOME_B, FANTASIA_B)}
    for d in (T0, T1):
        resumo = base / "normalized" / d / "summary"
        geo = _ler(resumo / "geo_orgs.json.gz")
        for asn, cnpj, nome, fantasia in ((a, cnpj_a, nome_a, ""), (b, cnpj_b, NOME_B, FANTASIA_B)):
            o = geo["orgs"][str(asn)]
            o.update(razao_social=nome, name=nome, nome_fantasia=fantasia, lat=LAT, lon=LON, geo_confidence="exact_address", municipio="Vitória",
                     city="Vitória", uf="ES", codigo_municipio_ibge=3205309, **ENDERECO)
            if asn == a:
                o.update(natureza_juridica="Empresário (Individual)", codigo_natureza_juridica=2135)
        _gravar(resumo / "geo_orgs.json.gz", geo)

        rf = _ler(resumo / "receita_cnpj.json.gz")
        raiz_a, raiz_b = cnpj_a[:8], cnpj_b[:8]
        rf["empresa"][raiz_a] = {"nat": "2135", "capital": 1000.0, "porte": "01"}
        rf["empresa"][raiz_b] = {"nat": "2135", "capital": 1000.0, "porte": "01"}
        rf["simples"][raiz_b] = {**rf["simples"].get(raiz_b, {}), "simples": True, "mei": True, "mei_in": "2020-01-01", "mei_out": None}
        for e in rf["estabelecimentos"][raiz_a]:
            e.pop("n", None)
        for e in rf["estabelecimentos"][raiz_b]:
            e["n"] = FANTASIA_B
        _gravar(resumo / "receita_cnpj.json.gz", rf)

        for arq in sorted(resumo.glob("anatel_*.json.gz")) + [resumo / "sici_acessos.json.gz", resumo / "sici_movel_acessos.json.gz"]:
            if arq.exists():
                doc = _ler(arq)
                _plantar_nomes(doc, cnpjs, {})
                _gravar(arq, doc)

        _plantar_multas_e_erbs(resumo, cnpjs)

        nomes = _ler(resumo / "asn_names.json.gz")
        nomes[str(a)], nomes[str(b)] = f"{nome_a}, BR", f"{NOME_B}, BR"
        _gravar(resumo / "asn_names.json.gz", nomes)
        for membros in (base / "raw" / d).glob("*/ixbr_members.json"):
            doc = _ler(membros)
            for m in doc["members"]:
                if m["asn"] in (a, b):
                    m["name"] = nome_a if m["asn"] == a else NOME_B
            _gravar(membros, doc)
    return {"a": (a, cnpj_a), "b": (b, cnpj_b)}


def _publicar(base: Path, com_regra: bool) -> None:
    from core import pessoa_natural
    from core.common import configure_logging
    from products.history import build as historico
    from tests.products.conftest import run_pipeline

    with pytest.MonkeyPatch.context() as mp:
        if not com_regra:                       # snapshot anterior à regra: a publicação não conhece o índice
            mp.setattr(pessoa_natural, "indice_do_snapshot", lambda b, d: pessoa_natural.Indice())
        for d in (T0, T1):
            run_pipeline(base, d, mp)
    for d in (T0, T1):
        historico.construir(base, d, configure_logging())


@pytest.fixture(scope="module", params=["publicado", "legado"])
def mundo(request, dataset, tmp_path_factory):
    """(base, titulares) com o pipeline rodado sobre a cópia plantada; `legado` publica sem a regra."""
    base = tmp_path_factory.mktemp(request.param) / "data"
    shutil.copytree(dataset, base)
    titulares = _plantar(base)
    _publicar(base, com_regra=request.param == "publicado")
    return request.param, base, titulares


@pytest.fixture(scope="module")
def base(mundo):
    return mundo[1]


@pytest.fixture(scope="module")
def cliente(base):
    from fastapi.testclient import TestClient

    with pytest.MonkeyPatch.context() as mp:
        for k, v in {"DATA_DIR": str(base), "JWT_SECRET": "x" * 32, "GOOGLE_CLIENT_ID": "a", "GOOGLE_CLIENT_SECRET": "b", "ALLOWED_IPS": "203.0.113.128/25",
                     "APP_BASE_URL": "http://localhost", "ANON_SESSION_LIMIT_MINUTES": "10", "ACCESS_POLICY_MODE": "enforce", "USAGE_LOG": "off",
                     "ANON_API_CLIENT_COST_SECONDS": "0"}.items():
            mp.setenv(k, v)
        from api.main import app
        from api.ratelimit import limiter
        from api.store import Store
        from core import marcas as marcas_mod
        from tests.synth.qualidade import CURADA

        mp.setattr(Store, "_load_pix_config", lambda self: fake_pix())
        mp.setattr(marcas_mod, "CAMINHO_CURADA", CURADA)
        mp.setattr(limiter, "enabled", False)
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
        for attr in ("store", "latest_cache"):
            if hasattr(app.state, attr):
                delattr(app.state, attr)


@pytest.fixture(scope="module")
def srv(base):
    import sys

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATA_DIR", str(base))
        from api.store import Store
        from core import marcas as marcas_mod
        from mcp_server import app as m
        from tests.synth.qualidade import CURADA

        mp.setattr(Store, "_load_pix_config", lambda self: fake_pix())
        mp.setattr(marcas_mod, "CAMINHO_CURADA", CURADA)
        nova = Store(base)
        for nome, mod in list(sys.modules.items()):
            if nome.startswith("mcp_server") and hasattr(mod, "_store"):
                mp.setattr(mod, "_store", nova)
        yield m


@pytest.fixture(scope="module")
def contextos(cliente, mundo):
    """Contexto de ids padrão, no do A e no do B (os ids dos titulares plantados entram no lugar dos do dataset)."""
    padrao = discover(cliente)
    out = {"padrao": padrao}
    for rotulo, (asn, cnpj) in mundo[2].items():
        ctx = dict(padrao)
        for k in list(ctx):
            if k == "asn" or k.startswith("asn_"):
                ctx[k] = str(asn)
            if k == "cnpj" or k.startswith("cnpj_"):
                ctx[k] = cnpj
        ctx["asns"] = str(asn)
        doc = cliente.get(f"/api/v1/asns/{asn}", headers=ALLOWED).text
        m = re.search(r'"((?:\d{1,3}\.){3}\d{1,3}/\d+)"', doc)
        if m:
            ctx["prefix"], ctx["ip"] = m.group(1), m.group(1).split("/")[0]
        out[rotulo] = ctx
    return out


def _run(coro):
    return asyncio.run(coro)


def _texto_da_tool(srv, nome, args) -> str:
    out = _run(srv.mcp.call_tool(nome, args))
    blocos = out[0] if isinstance(out, tuple) else out
    return "".join(getattr(b, "text", "") for b in blocos)


def _achados(texto: str, ponto: bool = True) -> list[str]:
    achou = SENSIVEL.findall(texto)
    if ponto:
        achou += PONTO.findall(texto)
    return sorted(set(achou))


def _relatorio(vazou: dict) -> str:
    return "vazou:\n" + "\n".join(f"  {k}: {v}" for k, v in sorted(vazou.items()))


# ── o dado plantado existe; a regra de publicação vale só para o `publicado` ─────────────────────────────────

def _textos_publicados(base: Path):
    """Todo documento publicado como texto (JSON, `.json.gz` e as entradas de `asns.zip`)."""
    pub = base / "published" / T1
    for p in sorted(pub.rglob("*")):
        if not p.is_file() or p.name == "manifest.json":
            continue
        rel = str(p.relative_to(pub))
        if p.name.endswith(".zip"):
            with zipfile.ZipFile(p) as z:
                for i in z.infolist():
                    yield f"{rel}!{i.filename}", z.read(i.filename).decode("utf-8", "replace")
        elif p.name.endswith((".json", ".geojson")):
            yield rel, p.read_text(encoding="utf-8", errors="replace")
        elif p.name.endswith((".json.gz", ".geojson.gz")):
            yield rel, gzip.decompress(p.read_bytes()).decode("utf-8", "replace")


def test_o_que_foi_plantado_existe_nas_fontes(base, mundo):
    (a, cnpj_a), (b, cnpj_b) = mundo[2]["a"], mundo[2]["b"]
    resumo = base / "normalized" / T1 / "summary"
    org = _ler(resumo / "geo_orgs.json.gz")["orgs"]
    assert org[str(a)]["razao_social"].startswith(NOME_A) and org[str(a)]["lat"] == LAT
    assert _ler(resumo / "asn_names.json.gz")[str(b)] == f"{NOME_B}, BR"
    assert any(NOME_A in json.dumps(r) for r in _ler(resumo / "anatel_scm.json.gz")["by_cnpj"][cnpj_a])


def test_arquivos_publicados(mundo):
    """`publicado`: nenhum arquivo traz o nome civil, o CPF nem o ponto exato (PJ não é tocada). `legado`: traz, ou a variante não prova nada."""
    variante, base, _ = mundo
    achados = {rel: a for rel, texto in _textos_publicados(base) if (a := _achados(texto))}
    if variante == "publicado":
        assert achados == {}, _relatorio(achados)
        man = json.loads((base / "published" / T1 / "manifest.json").read_text(encoding="utf-8"))
        assert man["privacidade"]["pessoa_natural"] >= 1 and man["privacidade"]["titulares"] >= 2
    else:
        assert achados, "o snapshot legado não tem o dado plantado: a leitura não está sendo testada"
        assert "privacidade" not in json.loads((base / "published" / T1 / "manifest.json").read_text(encoding="utf-8"))


# ── MCP ──────────────────────────────────────────────────────────────────────────────────────────────────

def _chamadas_mcp(srv, ctx) -> dict[str, tuple[str, dict]]:
    ferramentas = {t.name: t for t in _run(srv.mcp.list_tools())}
    chamadas = {n: args_for(n, t.inputSchema or {}, ctx) for n, t in ferramentas.items()}
    asn, cnpj = int(ctx["asn"]), ctx["cnpj"]
    extras = {
        "asn_lote#completo": ("asn_lote", {"asns": [asn]}),
        "geo_localizar#asn": ("geo_localizar", {"asn": asn}),
        "outorga_detalhe#cnpj": ("outorga_detalhe", {"cnpj": cnpj}),
        "outorga_lista#todos": ("outorga_lista", {"servico": "SCM,SMP,STFC,SEAC", "todos": True, "limit": 50}),
        "operadora_detalhe#cnpj": ("operadora_detalhe", {"cnpj": cnpj}),
        "operadora_grupo#cnpj": ("operadora_grupo", {"cnpj": cnpj, "limit": 50}),
        "operadora_acessos#cnpj": ("operadora_acessos", {"cnpj": cnpj}),
        "operadora_resolver#nome": ("operadora_resolver", {"name": "Plantada"}),
        "ixp_assinantes#ixp": ("ixp_assinantes", {"code": ctx["code"]}),
        "ixp_proximos#ixp": ("ixp_proximos", {"code": ctx["code"], "radius_km": 5000}),
        "infra_proximos#ponto": ("infra_proximos", {"lat": CENTRO[0], "lon": CENTRO[1], "radius_km": 5000}),
    }
    from api.query_catalogo import SCHEMA

    for col in SCHEMA:
        extras[f"query#{col}"] = ("query", {"collection": col, "limit": 500})
    for col in ("asns", "scms", "smps", "operadoras"):
        extras[f"query#{col}#near"] = ("query", {"collection": col, "near": {"point": list(CENTRO), "radius_km": 2000}, "limit": 500})
    return {**{n: (n, a) for n, a in chamadas.items()}, **extras}


@pytest.mark.parametrize("quem", ["padrao", "a", "b"])
def test_nenhuma_tool_do_mcp_devolve_nome_civil_nem_ponto_exato(srv, contextos, quem):
    vazou, erros = {}, {}
    for rotulo, (nome, args) in _chamadas_mcp(srv, contextos[quem]).items():
        try:
            texto = _texto_da_tool(srv, nome, args)
        except Exception as exc:  # noqa: BLE001
            if nome not in SEM_DADOS_NO_SINTETICO:
                erros[rotulo] = str(exc)[:160]
            continue
        if achou := _achados(texto):
            vazou[rotulo] = achou
    assert vazou == {}, _relatorio(vazou)
    if quem == "padrao":                                                  # nos contextos dos titulares, tools sem dado do AS erram por falta de dado
        assert not {k: v for k, v in erros.items() if not k.startswith("query#")}, erros


def test_nenhum_resource_do_mcp_devolve_nome_civil_nem_ponto_exato(srv, contextos):
    from core.site import SITE

    vazou = {}
    for quem in ("padrao", "a", "b"):
        ctx = contextos[quem]
        uris = [str(r.uri) for r in _run(srv.mcp.list_resources())]
        uris += [SITE.uri(f"asn/{ctx['asn']}"), SITE.uri(f"operadora/{ctx['cnpj']}"), SITE.uri(f"municipio/{ctx['ibge']}"),
                 SITE.uri(f"uf/{ctx['uf']}"), SITE.uri(f"ixp/{ctx['code']}")]
        for uri in uris:
            texto = "".join(c.content for c in _run(srv.mcp.read_resource(uri)))
            if achou := _achados(texto):
                vazou[f"{quem} {uri}"] = achou
    assert vazou == {}, _relatorio(vazou)


# ── REST ─────────────────────────────────────────────────────────────────────────────────────────────────

def _operacoes(cliente) -> list[str]:
    spec = cliente.get("/api/v1/openapi.json").json()
    return sorted(f"GET {p}" for p, ops in spec["paths"].items() if "get" in ops)


@pytest.mark.parametrize("quem", ["padrao", "a", "b"])
def test_nenhuma_rota_da_api_devolve_nome_civil_nem_ponto_exato(cliente, contextos, quem):
    """Toda rota GET, anônimo e allowlist, no contexto do titular (menos /contacts, que é por conta e cobrada)."""
    vazou = {}
    for k in _operacoes(cliente):
        if k.endswith("/contacts"):
            continue
        path = k.split(" ", 1)[1]
        try:
            url, query, _ = request_for(path, "GET", contextos[quem])
        except KeyError:
            continue
        for h in (ANON, ALLOWED):
            r = cliente.get(url, params=query, headers=h)
            if r.status_code != 200:
                continue
            if achou := _achados(r.text):
                vazou[k] = achou
                break
    assert vazou == {}, _relatorio(vazou)


def test_query_de_toda_colecao_pela_rest(cliente):
    from api.query_catalogo import SCHEMA

    vazou = {}
    for col in SCHEMA:
        for h in (ANON, ALLOWED):
            r = cliente.post(f"/api/v1/query/{col}", json={"limit": 500}, headers=h)
            if r.status_code == 200 and (achou := _achados(r.text)):
                vazou[f"{col}"] = achou
        if col in ("asns", "scms", "smps", "operadoras"):
            r = cliente.post(f"/api/v1/query/{col}", json={"near": {"point": list(CENTRO), "radius_km": 2000}, "limit": 500}, headers=ALLOWED)
            if r.status_code == 200 and (achou := _achados(r.text)):
                vazou[f"{col}#near"] = achou
    assert vazou == {}, _relatorio(vazou)


def test_busca_nao_acha_o_nome_civil_e_acha_o_rotulo(cliente, mundo):
    for q in ("JOAOZINHO", "MARIAZINHA", "Plantado PTONZE"):
        r = cliente.get("/api/v1/busca", params={"q": q}, headers=ALLOWED)
        assert r.status_code == 200 and _achados(json.dumps(r.json()["grupos"], ensure_ascii=False)) == [], (q, r.text[:300])
    r = cliente.get("/api/v1/busca", params={"q": "Fibra Plantada"}, headers=ALLOWED)
    assert "Fibra Plantada B" in r.text


def test_motor_de_query_nao_filtra_nem_agrupa_pelo_nome_civil(cliente):
    """O motor opera sobre a tabela já sem o nome civil: o filtro pelo nome não acha ninguém, e o agrupamento mostra o público."""
    r = cliente.post("/api/v1/query/asns", json={"filter": {"field": "razao_social", "op": "contains", "value": "JOAOZINHO"}, "limit": 10}, headers=ALLOWED)
    assert r.status_code == 200 and r.json()["total"] == 0
    r = cliente.post("/api/v1/query/asns", json={"filter": {"field": "razao_social", "op": "contains", "value": "Empresário individual"}, "limit": 10}, headers=ALLOWED)
    assert r.json()["total"] >= 1
    r = cliente.post("/api/v1/query/asns", json={"filter": {"field": "razao_social", "op": "contains", "value": "Fibra Plantada"}, "limit": 10}, headers=ALLOWED)
    assert r.json()["total"] >= 1


# ── o que a regra deve entregar no lugar ─────────────────────────────────────────────────────────────────

def test_ei_sem_fantasia_vira_rotulo_com_asn_e_cnpj_mascarado(srv, cliente, mundo):
    (a, cnpj_a) = mundo[2]["a"]
    rotulo = f"Empresário individual (AS{a}, CNPJ **.***.{cnpj_a[5:8]}/{cnpj_a[8:12]}-**)"
    doc = cliente.get(f"/api/v1/asns/{a}", headers=ALLOWED).json()
    assert doc["name"].startswith(rotulo), doc["name"]
    assert {x["name"] for x in doc.get("alt_names", [])} <= {rotulo}, doc["alt_names"]
    mcp = json.loads(_texto_da_tool(srv, "asn_detalhe", {"asn": a}))
    org = mcp["geo_org"]
    assert org["razao_social"] == rotulo and not {"lat", "lon", "logradouro", "cep"} & set(org), org
    assert org["uf"] == "ES"                                              # município e UF ficam


def test_mei_com_fantasia_mostra_a_fantasia(srv, cliente, mundo):
    (b, _) = mundo[2]["b"]
    doc = cliente.get(f"/api/v1/asns/{b}", headers=ALLOWED).json()
    assert doc["name"].startswith(FANTASIA_B) and {x["name"] for x in doc.get("alt_names", [])} <= {FANTASIA_B}
    org = json.loads(_texto_da_tool(srv, "asn_detalhe", {"asn": b}))["geo_org"]
    assert org["razao_social"] == FANTASIA_B and org["nome_fantasia"] == FANTASIA_B


def _e_centroide(coords) -> bool:
    return abs(coords[1] - CENTROIDE_VITORIA[0]) < 1e-3 and abs(coords[0] - CENTROIDE_VITORIA[1]) < 1e-3


@pytest.mark.parametrize("rota", ["/api/v1/map/asns", "/api/v1/map/scms"])
def test_ponto_de_ei_no_mapa_e_o_centroide_do_municipio_e_o_de_pj_nao_muda(cliente, mundo, rota):
    (a, cnpj_a), (b, cnpj_b) = mundo[2]["a"], mundo[2]["b"]
    r = cliente.get(rota, headers=ALLOWED)
    assert r.status_code == 200, (rota, r.status_code)
    feicoes = r.json()["features"]
    de_ei = [f for f in feicoes if f["properties"].get("asn") in (a, b) or f["properties"].get("cnpj") in (cnpj_a, cnpj_b)]
    assert de_ei, "titulares plantados ausentes da camada"
    for f in de_ei:
        coords = (f.get("geometry") or {}).get("coordinates")
        if coords and rota.endswith("/asns"):                             # cadastro por ASN tem o município IBGE: o centróide; a outorga sintética não tem, e o ponto some
            assert _e_centroide(coords), f
        elif rota.endswith("/scms"):
            assert not coords or _e_centroide(coords), f
    pj = [f for f in feicoes if f not in de_ei and (f.get("geometry") or {}).get("coordinates")]
    assert pj, "nenhuma PJ com ponto: o dataset perdeu o contraste"       # PJ: ponto como está (D1: a reconciliar)


# ── mitigação da triangulação (`within_radius` com raio pequeno) ─────────────────────────────────────────

@pytest.mark.parametrize("colecao", ["asns", "scms", "operadoras"])
def test_raio_pequeno_e_recusado_nas_colecoes_com_posicao_de_sede(cliente, colecao):
    from api.privacidade import RAIO_MINIMO_SEDE_KM

    pequeno = RAIO_MINIMO_SEDE_KM / 4
    for corpo in ({"near": {"point": list(CENTRO), "radius_km": pequeno}},
                  {"filter": {"op": "within_radius", "centers": [list(CENTRO)], "radius_km": pequeno}},
                  {"filter": {"and": [{"field": "uf", "op": "eq", "value": "ES"},
                                      {"op": "within_radius", "centers": [list(CENTRO)], "radius_km": pequeno}]}}):
        r = cliente.post(f"/api/v1/query/{colecao}", json={**corpo, "limit": 5}, headers=ALLOWED)
        assert r.status_code in (400, 422) and "raio mínimo" in r.text, (colecao, corpo, r.status_code, r.text[:200])
    ok = cliente.post(f"/api/v1/query/{colecao}", json={"near": {"point": list(CENTRO), "radius_km": RAIO_MINIMO_SEDE_KM}, "limit": 5}, headers=ALLOWED)
    assert ok.status_code == 200


def test_raio_pequeno_segue_valendo_onde_nao_ha_sede(cliente):
    """Prefixos têm a posição do IP, não a da sede: o piso não vale para eles (não muda comportamento fora do escopo)."""
    r = cliente.post("/api/v1/query/prefixes", json={"near": {"point": [-23.6, -46.7], "radius_km": 0.5}, "limit": 5}, headers=ALLOWED)
    assert r.status_code == 200


# ── multas e ERBs: o nome do titular está em `entidade` ──────────────────────────────────────────────────

def _rotulo_do_a(mundo) -> str:
    (a, cnpj_a) = mundo[2]["a"]
    return f"Empresário individual (AS{a}, CNPJ **.***.{cnpj_a[5:8]}/{cnpj_a[8:12]}-**)"


def _entidades(doc, cnpj: str) -> set:
    """`entidade` dos registros do documento cujo `raiz`, `cnpj` ou `cnpj_matriz` é do titular."""
    achou = set()
    if isinstance(doc, dict):
        if "entidade" in doc and any(isinstance(doc.get(k), str) and doc[k].startswith(cnpj[:8]) for k in ("raiz", "cnpj", "cnpj_matriz")):
            achou.add(doc["entidade"])
        for v in doc.values():
            achou |= _entidades(v, cnpj)
    elif isinstance(doc, list):
        for v in doc:
            achou |= _entidades(v, cnpj)
    return achou


def test_multas_de_ei_e_mei_saem_com_o_nome_publico_na_rest(cliente, mundo):
    (_, cnpj_a), (_, cnpj_b) = mundo[2]["a"], mundo[2]["b"]
    for visao in ("servico", "raiz"):
        r = cliente.get("/api/v1/multas/empresas", params={"visao": visao, "limit": 500}, headers=ALLOWED)
        assert r.status_code == 200 and _achados(r.text) == [], r.text[:300]
        doc = r.json()
        assert _entidades(doc, cnpj_a) == {_rotulo_do_a(mundo)} and _entidades(doc, cnpj_b) == {FANTASIA_B}, visao
    r = cliente.post("/api/v1/query/multas_empresa", json={"limit": 500}, headers=ALLOWED)
    assert r.status_code == 200 and _entidades(r.json(), cnpj_a) == {_rotulo_do_a(mundo)} and _entidades(r.json(), cnpj_b) == {FANTASIA_B}


def test_multas_de_ei_saem_com_o_nome_publico_no_mcp(srv, mundo):
    (_, cnpj_a), (_, cnpj_b) = mundo[2]["a"], mundo[2]["b"]
    doc = json.loads(_texto_da_tool(srv, "query", {"collection": "multas_empresa", "limit": 500}))
    assert _achados(json.dumps(doc, ensure_ascii=False)) == []
    assert _entidades(doc, cnpj_a) == {_rotulo_do_a(mundo)} and _entidades(doc, cnpj_b) == {FANTASIA_B}


def test_erbs_de_ei_e_mei_saem_com_o_nome_publico_na_rest(cliente, mundo):
    (_, cnpj_a), (_, cnpj_b) = mundo[2]["a"], mundo[2]["b"]
    r = cliente.get("/api/v1/erbs/resumo", headers=ALLOWED)
    assert r.status_code == 200 and _achados(r.text) == [], r.text[:300]
    doc = r.json()
    assert _entidades(doc, cnpj_a) == {_rotulo_do_a(mundo)} and _entidades(doc, cnpj_b) == {FANTASIA_B}
