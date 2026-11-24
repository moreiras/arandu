# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4/T5 — endereço e coordenada exata da sede não saem pelo MCP nem pela API (decisão D1 do mantenedor).

Numa CÓPIA do dataset sintético, o cadastro da Receita (`geo_orgs`, `geo_org` dos documentos de ASN) e as outorgas da Anatel ganham um
endereço plantado (logradouro, número, complemento, bairro, CEP) e uma coordenada `exact_address` plantada. O teste chama TODAS as tools e
resources do MCP e todas as rotas GET da API e procura os valores plantados no texto da resposta. Município e UF continuam saindo.
Pontos de mapa (camadas GeoJSON) ficam fora da varredura de coordenada: a posição no mapa é do PT-11 (ponto a reconciliar de D1).
"""
import asyncio
import gzip
import json
import re
import shutil
from pathlib import Path

import pytest

from tests.products.api_contract import ALLOWED, ANON, discover, request_for
from tests.products.conftest import fake_pix
from tests.products.mcp_contract import SEM_DADOS_NO_SINTETICO, args_for
from tests.synth.world import T0, T1

ENDERECO = {"descricao_tipo_de_logradouro": "RUA", "logradouro": "Rua Plantada PT08", "numero": "4321", "complemento": "Sala PT08",
            "bairro": "Bairro PT08", "cep": "12345678"}
LAT, LON = -15.7654321987, -47.8765432198
# o que não pode aparecer em resposta nenhuma (CEP também na forma com hífen; coordenada até a 3ª casa, ~100 m)
TEXTO_PLANTADO = re.compile(r"Plantada PT08|Sala PT08|Bairro PT08|(?<!\d)12345-?678(?!\d)")
COORD_PLANTADA = re.compile(r"-15\.765|-47\.876")

# camadas de mapa: o ponto de cada titular é decisão do PT-11 (D1, "ponto a reconciliar"); o texto do endereço não sai nem nelas
ROTAS_DE_MAPA = re.compile(r"^GET /api/v1/(map/|.*/geo\b|.*/mapa\b|outorgas/mapa|localizador)")


def _plantar(x, geo_org=False):
    """Planta endereço e coordenada exata em todo registro de cadastro (tem campo de endereço, ou é um `geo_org`)."""
    if isinstance(x, list):
        for v in x:
            _plantar(v)
        return
    if not isinstance(x, dict):
        return
    if geo_org or {"logradouro", "cep", "bairro"} & x.keys():
        x.update(ENDERECO)
        if geo_org or "lat" in x:
            x.update(lat=LAT, lon=LON, geo_confidence="exact_address")
    for k, v in x.items():
        _plantar(v, geo_org=(k == "geo_org" and isinstance(v, dict)))


def _reescrever(caminho: Path, fn):
    gz = caminho.suffix == ".gz"
    abrir = (lambda m: gzip.open(caminho, m + "t", encoding="utf-8")) if gz else (lambda m: open(caminho, m, encoding="utf-8"))
    with abrir("r") as f:
        doc = json.load(f)
    fn(doc)
    with abrir("w") as f:
        json.dump(doc, f, ensure_ascii=False)


@pytest.fixture(scope="module")
def base(pipeline, tmp_path_factory):
    base0, _ = pipeline
    b = tmp_path_factory.mktemp("sede") / "data"
    shutil.copytree(base0, b)
    for d in (T0, T1):
        _reescrever(b / "normalized" / d / "summary" / "geo_orgs.json.gz",
                    lambda doc: [_plantar(o, geo_org=True) for o in doc["orgs"].values()])
        pub = b / "published" / d
        for p in sorted(pub.rglob("*.json")) + sorted(pub.rglob("*.json.gz")):
            if "maps" in p.relative_to(pub).parts:
                continue
            try:
                _reescrever(p, _plantar)
            except (ValueError, UnicodeDecodeError, OSError):
                continue
    return b


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

        mp.setattr(Store, "_load_pix_config", lambda self: fake_pix())
        mp.setattr(limiter, "enabled", False)
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
        for attr in ("store", "latest_cache"):
            if hasattr(app.state, attr):
                delattr(app.state, attr)


@pytest.fixture(scope="module")
def ctx(cliente):
    return discover(cliente)


@pytest.fixture(scope="module")
def srv(base, cliente):
    """Servidor MCP lendo a cópia plantada: toda tool lê o `_store` do próprio módulo (importado de `mcp_server.contexto`)."""
    import sys

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATA_DIR", str(base))
        from api.store import Store
        from mcp_server import app as m

        mp.setattr(Store, "_load_pix_config", lambda self: fake_pix())
        nova = Store(base)
        for nome, mod in list(sys.modules.items()):
            if nome.startswith("mcp_server") and hasattr(mod, "_store"):
                mp.setattr(mod, "_store", nova)
        yield m


def _run(coro):
    return asyncio.run(coro)


def _texto_da_tool(srv, nome, args) -> str:
    out = _run(srv.mcp.call_tool(nome, args))
    blocos = out[0] if isinstance(out, tuple) else out
    return "".join(getattr(b, "text", "") for b in blocos)


def _relatorio(vazou: dict) -> str:
    return "vazou:\n" + "\n".join(f"  {k}: {v}" for k, v in sorted(vazou.items()))


def _achados(texto: str, coordenada: bool = True) -> list[str]:
    achou = TEXTO_PLANTADO.findall(texto)
    if coordenada:
        achou += COORD_PLANTADA.findall(texto)
    return sorted(set(achou))


def test_dataset_plantado_tem_endereco_e_coordenada(base):
    """Sem o dado plantado o teste seria vazio: o cadastro e as outorgas da cópia têm endereço e coordenada exata."""
    with gzip.open(base / "normalized" / T1 / "summary" / "geo_orgs.json.gz", "rt") as f:
        org = next(iter(json.load(f)["orgs"].values()))
    assert org["logradouro"] == ENDERECO["logradouro"] and org["lat"] == LAT
    with gzip.open(base / "published" / T1 / "scm.json.gz", "rt") as f:
        rec = json.load(f)["scms"][0]
    assert rec["logradouro"] == ENDERECO["logradouro"] and rec["cep"] == ENDERECO["cep"]


def _chamadas_mcp(srv, ctx) -> dict[str, dict]:
    """Uma chamada válida por tool (a do contrato T5) e as que alcançam o cadastro da sede por outros caminhos."""
    ferramentas = {t.name: t for t in _run(srv.mcp.list_tools())}
    chamadas = {n: args_for(n, t.inputSchema or {}, ctx) for n, t in ferramentas.items()}
    asn, cnpj = int(ctx["asn"]), ctx["cnpj"]
    extras = {
        "asn_lote#completo": ("asn_lote", {"asns": [int(a) for a in ctx["asns"].split(",")]}),
        "geo_localizar#asn": ("geo_localizar", {"asn": asn}),
        "outorga_detalhe#cnpj": ("outorga_detalhe", {"cnpj": cnpj}),
        "outorga_lista#todos": ("outorga_lista", {"servico": "SCM,SMP,STFC,SEAC", "todos": True, "limit": 50}),
        "operadora_detalhe#cnpj": ("operadora_detalhe", {"cnpj": cnpj}),
        "operadora_grupo#cnpj": ("operadora_grupo", {"cnpj": cnpj, "limit": 50}),
    }
    from api.query_catalogo import SCHEMA
    for col in SCHEMA:
        extras[f"query#{col}"] = ("query", {"collection": col, "limit": 50})
    for col in ("asns", "scms", "smps", "operadoras"):
        extras[f"query#{col}#near"] = ("query", {"collection": col, "near": {"place": "Arandurápolis", "radius_km": 2000}, "limit": 50})
    return {**{n: (n, a) for n, a in chamadas.items()}, **extras}


def test_nenhuma_tool_do_mcp_devolve_endereco_ou_coordenada_da_sede(srv, ctx):
    vazou, erros = {}, {}
    for rotulo, (nome, args) in _chamadas_mcp(srv, ctx).items():
        try:
            texto = _texto_da_tool(srv, nome, args)
        except Exception as exc:  # noqa: BLE001
            if nome not in SEM_DADOS_NO_SINTETICO:
                erros[rotulo] = str(exc)[:160]
            continue
        if achou := _achados(texto):
            vazou[rotulo] = achou
    assert vazou == {}, _relatorio(vazou)
    assert not {k: v for k, v in erros.items() if not k.startswith("query#")}, erros


def test_nenhum_resource_do_mcp_devolve_endereco_ou_coordenada_da_sede(srv, ctx):
    from core.site import SITE

    uris = [str(r.uri) for r in _run(srv.mcp.list_resources())]
    uris += [SITE.uri(f"asn/{ctx['asn']}"), SITE.uri(f"operadora/{ctx['cnpj']}"), SITE.uri(f"municipio/{ctx['ibge']}"),
             SITE.uri(f"uf/{ctx['uf']}"), SITE.uri(f"ixp/{ctx['code']}")]
    vazou = {}
    for uri in uris:
        texto = "".join(c.content for c in _run(srv.mcp.read_resource(uri)))
        if achou := _achados(texto):
            vazou[uri] = achou
    assert vazou == {}, _relatorio(vazou)


def test_asn_detalhe_mantem_municipio_e_uf_da_sede(srv, ctx):
    doc = json.loads(_texto_da_tool(srv, "asn_detalhe", {"asn": int(ctx["asn"])}))
    org = doc.get("geo_org") or {}
    assert org.get("uf") and (org.get("city") or org.get("municipio")), org
    assert not ENDERECO.keys() & set(org) and not {"lat", "lon"} & set(org)
    geo = json.loads(_texto_da_tool(srv, "geo_localizar", {"asn": int(ctx["asn"])}))["asn"]
    assert geo.get("uf") and geo.get("municipio"), geo


def _operacoes(cliente) -> list[str]:
    spec = cliente.get("/api/v1/openapi.json").json()
    return sorted(f"GET {p}" for p, ops in spec["paths"].items() if "get" in ops)


def test_nenhuma_rota_da_api_devolve_endereco_ou_coordenada_da_sede(cliente, ctx):
    """Toda rota GET (anônima e da allowlist), menos /contacts. Coordenada: fora as camadas de mapa (PT-11)."""
    vazou = {}
    for k in _operacoes(cliente):
        if k.endswith("/contacts"):
            continue
        path = k.split(" ", 1)[1]
        try:
            url, query, _ = request_for(path, "GET", ctx)
        except KeyError:
            continue
        for h in (ANON, ALLOWED):
            r = cliente.get(url, params=query, headers=h)
            if r.status_code != 200:
                continue
            if achou := _achados(r.text, coordenada=not ROTAS_DE_MAPA.match(k)):
                vazou[k] = achou
                break
    assert vazou == {}, _relatorio(vazou)


def test_rotas_de_asn_com_include_e_lote_sem_endereco(cliente, ctx):
    asn = ctx["asn"]
    for url, params in ((f"/api/v1/asns/{asn}", {}), (f"/api/v1/asns/{asn}", {"fields": "scm,smp,stfc,seac,name"}),
                        ("/api/v1/asns", {"asns": ctx["asns"]}), (f"/api/v1/prefixes/lookup", {"ip": ctx["ip"]})):
        r = cliente.get(url, params=params, headers=ALLOWED)
        assert r.status_code == 200, (url, r.status_code)
        assert _achados(r.text) == [], (url, params)


@pytest.mark.parametrize("campo", ["phone", "email", "address", "logradouro", "cep", "bairro", "lat", "lon"])
def test_query_nao_seleciona_contato_endereco_nem_posicao_da_sede(srv, cliente, campo):
    """ASES-E15: nenhum campo de contato, endereço ou posição da sede é selecionável no `query` (anônimo, allowlist e MCP)."""
    from mcp.server.fastmcp.exceptions import ToolError

    for col in ("asns", "scms", "operadoras"):
        corpo = {"select": ["cnpj", campo], "limit": 5}
        for h in (ANON, ALLOWED):
            r = cliente.post(f"/api/v1/query/{col}", json=corpo, headers=h)
            assert r.status_code in (400, 422), (col, campo, r.status_code, r.text[:200])
        with pytest.raises(ToolError):
            _run(srv.mcp.call_tool("query", {"collection": col, **corpo}))


def test_receitas_do_schema_nao_pedem_contato(srv):
    from api.query_catalogo import RECIPES

    for receita in RECIPES:
        sel = set((receita.get("args") or {}).get("select") or [])
        assert not sel & {"phone", "email", "address", "telefone", "logradouro", "cep", "lat", "lon"}, receita["pergunta"]
    esquema = json.loads(_texto_da_tool(srv, "describe_schema", {"collection": "asns"}))
    assert not {"phone", "email", "address", "lat", "lon"} & {c["name"] for c in esquema["campos"]}
    assert esquema.get("geo")                                    # o `near` continua anunciado: a posição é usada por dentro


def test_near_continua_filtrando_pela_sede(srv, cliente):
    """A posição sai da resposta, não do filtro: `near` com raio grande acha as sedes; o item não traz lat/lon."""
    r = cliente.post("/api/v1/query/asns", json={"near": {"place": "Arandurápolis", "radius_km": 5000}, "limit": 5}, headers=ALLOWED).json()
    assert r["total"] > 0 and not {"lat", "lon"} & set(r["items"][0])
    r = cliente.post("/api/v1/query/scms", json={"near": {"place": "Arandurápolis", "radius_km": 5000}, "limit": 5}, headers=ALLOWED).json()
    assert r["total"] > 0 and not {"lat", "lon", "logradouro", "cep"} & set(r["items"][0])
