# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Sitemaps, `robots.txt` e `llms.txt` com o domínio do `.env` (`SITE_URL`, `core/site.py`).

- `/sitemap.xml`: índice (`sitemapindex`) dos três abaixo;
- `/sitemap-paginas.xml`: as páginas do menu e as fixas (`config/paginas_publicas.json`, gerado por `scripts/gen_sitemap.py`);
- `/sitemap-territorio.xml`: as 27 UFs e os municípios;
- `/sitemap-entidades.xml`: ASNs brasileiros, PTTs do IX.br e externos, operadoras com acessos, grupos societários com mais de
  uma empresa e datacenters do Brasil, do snapshot mais recente.

Ficam fora de `/api/` (que o robots.txt proíbe) e do OpenAPI; o nginx do frontend encaminha estes caminhos para cá."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi import APIRouter, Request
from fastapi.responses import Response

from api.store import Store
from core.site import SITE

router = APIRouter()
LIMITE = 50_000          # protocolo de sitemaps
PAGINAS_PUBLICAS = Path(__file__).resolve().parents[2] / "config" / "paginas_publicas.json"
_CACHE = {"Cache-Control": "public, max-age=3600"}
_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


@lru_cache(maxsize=1)
def paginas_publicas() -> dict:
    return json.loads(PAGINAS_PUBLICAS.read_text(encoding="utf-8"))


def _urlset(caminhos: list[str]) -> str:
    corpo = "\n".join(f"  <url><loc>{escape(SITE.url + u)}</loc></url>" for u in caminhos[:LIMITE])
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="{_NS}">\n{corpo}\n</urlset>\n'


def _xml(texto: str) -> Response:
    return Response(texto, media_type="application/xml", headers=_CACHE)


def caminhos(store: Store, date_str: str) -> list[str]:
    asns = sorted(a["asn"] for a in store.asn_index(date_str) if a.get("is_br"))
    ptts = sorted(i["code"] for i in store.ixp_index(date_str) if i.get("code"))
    externos = sorted(x["code"] for x in ((store.external_ixp_index(date_str) or {}).get("ixps") or []) if x.get("code"))
    ops = sorted(o["cnpj"] for o in store.operadora_index(date_str) if o.get("ativo"))
    try:
        grupos = sorted(g["grupo_id"] for g in store.grupos_societarios_overview(date_str) or [] if len(g.get("cnpjs") or []) > 1)
    except Exception:                                   # snapshot sem o cruzamento societário
        grupos = []
    inst = store.instalacoes_doc(date_str) or {}
    dcs = sorted(str(f["id"]) for f in (inst.get("instalacoes") or {}).values() if f.get("pais") in (None, "BR") and f.get("id") is not None)
    return [*(f"/asn/{a}" for a in asns), *(f"/ixp/{c}" for c in ptts), *(f"/ixp-externo/{c}" for c in externos),
            *(f"/operadora/{c}" for c in ops), *(f"/grupo/{g}" for g in grupos), *(f"/instalacao/{i}" for i in dcs)][:LIMITE]


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap_indice() -> Response:
    corpo = "\n".join(f"  <sitemap><loc>{SITE.url}/{n}</loc></sitemap>" for n in ("sitemap-paginas.xml", "sitemap-territorio.xml", "sitemap-entidades.xml"))
    return _xml(f'<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="{_NS}">\n{corpo}\n</sitemapindex>\n')


@router.get("/sitemap-paginas.xml", include_in_schema=False)
def sitemap_paginas() -> Response:
    return _xml(_urlset(paginas_publicas()["paginas"]))


@router.get("/sitemap-territorio.xml", include_in_schema=False)
def sitemap_territorio() -> Response:
    return _xml(_urlset(paginas_publicas()["territorio"]))


@router.get("/sitemap-entidades.xml", include_in_schema=False)
def sitemap_entidades(request: Request) -> Response:
    store: Store = request.app.state.store
    date_str = store.latest()
    return _xml(_urlset(caminhos(store, date_str) if date_str else []))


def robots() -> str:
    return f"User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /auth/\nDisallow: /login\nDisallow: /meta/\n\nSitemap: {SITE.url}/sitemap.xml\n"


def llms() -> str:
    b = SITE.url
    paginas = ", ".join(f"[{i['rotulo']}]({b}{i['caminho']})" for i in paginas_publicas()["menu"])
    return f"""# {SITE.titulo}

> Mapa da Internet brasileira em snapshots semanais e imutáveis: BGP do IX.br e da tabela global, Registro.br/LACNIC, PeeringDB, RPKI, APNIC e dados abertos da Anatel (outorgas e acessos do SICI). Feito com o software livre {SITE.software} (AGPL-3.0-or-later).

Todo número tem fonte e data: o snapshot (data da coleta) e, quando a fonte tem calendário próprio (SICI), o mês de referência. Dados inferidos ou estimados são rotulados como tal. Contatos e dados de pessoa física não são públicos.

## Como usar
- [API REST e MCP]({b}/dados): exemplos de uso, endereço do servidor MCP e da documentação interativa (Swagger).
- [Fontes e licenças]({b}/fontes): cada fonte, licença, periodicidade, última coleta e os campos que produz.
- [OpenAPI]({b}/api/v1/openapi.json) e [Swagger UI]({b}/api/v1/docs).
- Servidor MCP (Streamable HTTP): {b}/mcp

## Páginas
- [Home]({b}/): perguntas prontas respondidas com o snapshot mais recente.
- {paginas}.
- Feed Atom do que mudou: {b}/api/v1/feed/mudancas.atom
- Entidades: `/asn/<número>`, `/ixp/<código>`, `/operadora/<cnpj>`, `/grupo/<id>`, `/municipio/<ibge>`, `/uf/<sigla>`, `/prefixo/<cidr>`.

## Sobre
- [Sobre e metodologia]({b}/sobre) · [Política de privacidade]({b}/privacidade) · [Uso aceitável]({b}/uso-aceitavel)
"""


@router.get("/robots.txt", include_in_schema=False)
def robots_txt() -> Response:
    return Response(robots(), media_type="text/plain; charset=utf-8", headers=_CACHE)


@router.get("/llms.txt", include_in_schema=False)
def llms_txt() -> Response:
    return Response(llms(), media_type="text/plain; charset=utf-8", headers=_CACHE)
