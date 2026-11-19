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


def test_robots_aponta_o_indice_e_barra_a_api_e_o_llms_cita_as_paginas_de_uso():
    c, sitemap = _cliente()
    robots = c.get("/robots.txt").text
    assert f"Sitemap: {sitemap.SITE.url}/sitemap.xml" in robots and "Disallow: /api/" in robots
    llms = c.get("/llms.txt").text
    for trecho in ("/dados", "/fontes", "/mcp", "/api/v1/openapi.json"):
        assert trecho in llms
    assert llms.startswith(f"# {sitemap.SITE.nome}")


def test_catalogo_publico_cobre_todas_as_fontes():
    docs = {f["id"] for f in json.loads((ROOT / "docs" / "fontes.json").read_text(encoding="utf-8"))["fontes"]}
    pub = {f["id"] for f in json.loads((ROOT / "frontend" / "public" / "catalogo.json").read_text(encoding="utf-8"))["fontes"]}
    assert docs == pub
