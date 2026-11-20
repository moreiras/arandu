# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — sitemaps, robots e llms.txt: lista de páginas em dia com o menu, índice
de sitemaps com o domínio do `.env`, XML válido e dentro dos limites do protocolo."""
import importlib.util
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("gen_sitemap", ROOT / "scripts" / "gen_sitemap.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _cliente():
    from api.routes import sitemap
    app = FastAPI()
    app.include_router(sitemap.router)
    return TestClient(app), sitemap


def test_lista_de_paginas_esta_em_dia():
    assert gen.SAIDA.read_text(encoding="utf-8") == gen.texto(), "config/paginas_publicas.json desatualizado: rode `python3 scripts/gen_sitemap.py`"


def test_toda_pagina_do_menu_esta_no_sitemap_e_e_rota_do_front():
    d = gen.dados()
    menu = {i["caminho"] for i in d["menu"]}
    assert menu and menu <= set(d["paginas"])
    rotas = set(re.findall(r'<Route path="([^"]+)"', (ROOT / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")))
    fixas = {u.split("?")[0].lstrip("/") for u in d["paginas"]} - {""}
    assert fixas <= rotas, sorted(fixas - rotas)
    assert {"uf/:uf", "municipio/:ibge"} <= rotas
    assert len(d["territorio"]) > 5000


def test_indice_e_sitemaps_usam_o_dominio_do_env():
    c, sitemap = _cliente()
    url = sitemap.SITE.url
    raiz = ET.fromstring(c.get("/sitemap.xml").text)
    locs = [e.text for e in raiz.findall("s:sitemap/s:loc", NS)]
    assert locs == [f"{url}/sitemap-paginas.xml", f"{url}/sitemap-territorio.xml", f"{url}/sitemap-entidades.xml"]
    for nome in ("/sitemap-paginas.xml", "/sitemap-territorio.xml"):
        r = c.get(nome)
        urls = [e.text for e in ET.fromstring(r.text).findall("s:url/s:loc", NS)]
        assert 10 < len(urls) <= 50_000 and len(set(urls)) == len(urls)
        assert all(u.startswith(url + "/") for u in urls)
    assert f"{url}/seguranca-de-roteamento" in c.get("/sitemap-paginas.xml").text


def _grupos(robots: str) -> dict[str, list[str]]:
    """User-agent → regras do grupo (RFC 9309: linhas `User-agent` seguidas formam um grupo)."""
    grupos, agentes, regras, ultimo_ua = {}, [], [], False
    for linha in robots.splitlines():
        linha = linha.split("#", 1)[0].strip()
        if not linha:
            continue
        campo, _, valor = linha.partition(":")
        if campo.lower() == "user-agent":
            if not ultimo_ua:
                agentes, regras = [], []
            agentes.append(valor.strip())
            for a in agentes:
                grupos[a] = regras
            ultimo_ua = True
        else:
            ultimo_ua = False
            if campo.lower() != "sitemap":
                regras.append(f"{campo}: {valor.strip()}")
    return grupos


def test_robots_libera_inferencia_barra_treino_e_o_llms_cita_as_paginas_de_uso():
    c, sitemap = _cliente()
    robots = c.get("/robots.txt").text
    assert f"Sitemap: {sitemap.SITE.url}/sitemap.xml" in robots
    g = _grupos(robots)
    sinal = "Content-Signal: search=yes, ai-input=yes, ai-train=no"
    # robôs em geral: páginas sim, a API não (só a descrição dela)
    assert sinal in g["*"] and "Disallow: /api/" in g["*"] and "Allow: /api/v1/openapi.json" in g["*"]
    # agentes a pedido de uma pessoa: API e MCP liberados, área de conta não
    for a in ("ChatGPT-User", "Claude-User"):
        assert sinal in g[a] and "Allow: /" in g[a] and not any(r.startswith("Disallow: /api") for r in g[a])
        assert "Disallow: /auth/" in g[a]
    # treino: barrado; os de busca não estão nessa lista
    for a in ("GPTBot", "ClaudeBot", "CCBot"):
        assert g[a] == ["Disallow: /"]
    assert "OAI-SearchBot" not in g and "Claude-SearchBot" not in g
    llms = c.get("/llms.txt").text
    for trecho in ("/dados", "/fontes", "/mcp", "/api/v1/openapi.json", "Para agentes de IA", "treino de modelos, não"):
        assert trecho in llms
    assert llms.startswith(f"# {sitemap.SITE.nome}")


def test_security_txt_rfc9116_com_o_contato_do_env():
    from datetime import datetime, timedelta, timezone
    c, sitemap = _cliente()
    r = c.get("/.well-known/security.txt")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")
    campos = dict(linha.split(": ", 1) for linha in r.text.strip().splitlines())
    assert campos["Contact"] == f"mailto:{sitemap.SITE.contato_seguranca}"
    assert campos["Canonical"] == f"{sitemap.SITE.url}/.well-known/security.txt"
    expira = datetime.strptime(campos["Expires"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    assert timedelta(days=30) < expira - datetime.now(timezone.utc) < timedelta(days=365)   # RFC 9116: menos de um ano


def test_nginx_serve_o_security_txt_e_404_no_resto_do_well_known():
    conf = (ROOT / "docker" / "nginx-frontend.conf").read_text(encoding="utf-8")
    assert "location = /.well-known/security.txt" in conf and "location ^~ /.well-known/ { return 404; }" in conf
    assert "location = /security.txt { return 301 /.well-known/security.txt; }" in conf


def test_catalogo_publico_cobre_todas_as_fontes():
    docs = {f["id"] for f in json.loads((ROOT / "docs" / "fontes.json").read_text(encoding="utf-8"))["fontes"]}
    pub = {f["id"] for f in json.loads((ROOT / "frontend" / "public" / "catalogo.json").read_text(encoding="utf-8"))["fontes"]}
    assert docs == pub
