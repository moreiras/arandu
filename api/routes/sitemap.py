# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Sitemaps, `robots.txt`, `llms.txt` e `security.txt` com o domínio e os contatos do `.env` (`SITE_URL`, `SITE_CONTATO_SEGURANCA`, `core/site.py`).

- `/sitemap.xml`: índice (`sitemapindex`) dos três abaixo;
- `/sitemap-paginas.xml`: as páginas do menu e as fixas (`config/paginas_publicas.json`, gerado por `scripts/gen_sitemap.py`);
- `/sitemap-territorio.xml`: as 27 UFs e os municípios;
- `/sitemap-entidades.xml`: ASNs brasileiros, PTTs do IX.br e externos, operadoras com acessos, grupos societários com mais de
  uma empresa e datacenters do Brasil, do snapshot mais recente.

Política para robôs (`robots.txt`): páginas liberadas para busca e para uso na resposta de IA, sem treino (`Content-Signal`, proposta
da Cloudflare, e os robôs de treino conhecidos barrados pelo nome). A API e o MCP ficam para os agentes que buscam a pedido de uma
pessoa: o site é renderizado no navegador e, sem JavaScript, a página chega vazia.

Ficam fora de `/api/` e do OpenAPI; o nginx do frontend encaminha estes caminhos para cá."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
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


# Treino de modelos: barrados pelo nome (o `Content-Signal` sozinho é só declaração). Ficam de fora os de busca (OAI-SearchBot,
# Claude-SearchBot) e o Google-Extended, que no Gemini vale também para o uso na resposta.
ROBOS_DE_TREINO = ("GPTBot", "ClaudeBot", "CCBot", "Applebot-Extended", "meta-externalagent", "Bytespider")
# Agentes que buscam a pedido de uma pessoa, no momento da resposta: podem consultar a API e o MCP.
AGENTES_DO_USUARIO = ("ChatGPT-User", "Claude-User", "Perplexity-User", "MistralAI-User")
SINAL = "Content-Signal: search=yes, ai-input=yes, ai-train=no"
_PRIVADO = "Disallow: /auth/\nDisallow: /login\nDisallow: /meta/\n"


def robots() -> str:
    treino = "".join(f"User-agent: {r}\n" for r in ROBOS_DE_TREINO)
    agentes = "".join(f"User-agent: {r}\n" for r in AGENTES_DO_USUARIO)
    return (f"# Busca e uso na resposta de IA: sim; treino de modelos: não. Para dados, use a API ou o MCP: {SITE.url}/llms.txt\n\n"
            f"User-agent: *\n{SINAL}\nAllow: /\nAllow: /api/v1/openapi.json\nAllow: /api/v1/docs\nDisallow: /api/\n{_PRIVADO}\n"
            f"# Agentes que buscam a pedido de uma pessoa: as páginas vêm vazias sem JavaScript; a API e o MCP têm os dados.\n"
            f"{agentes}{SINAL}\nAllow: /\n{_PRIVADO}\n"
            f"# Treino de modelos\n{treino}Disallow: /\n\n"
            f"Sitemap: {SITE.url}/sitemap.xml\n")


def security_txt() -> str:
    """RFC 9116. `Expires` (obrigatório) a 180 dias de cada resposta: nunca vence enquanto o site responde."""
    expira = (datetime.now(timezone.utc) + timedelta(days=180)).strftime("%Y-%m-%dT00:00:00Z")
    return (f"Contact: mailto:{SITE.contato_seguranca}\nExpires: {expira}\nPreferred-Languages: pt, en\n"
            f"Canonical: {SITE.url}/.well-known/security.txt\n")


def llms() -> str:
    b = SITE.url
    paginas = ", ".join(f"[{i['rotulo']}]({b}{i['caminho']})" for i in paginas_publicas()["menu"])
    return f"""# {SITE.titulo}

> {SITE.nome_extenso} em snapshots semanais e imutáveis: BGP do IX.br e da tabela global, Registro.br/LACNIC, PeeringDB, RPKI, APNIC e dados abertos da Anatel (outorgas e acessos do SICI). Feito com o software livre {SITE.software} (AGPL-3.0-or-later).

Todo número tem fonte e data: o snapshot (data da coleta) e, quando a fonte tem calendário próprio (SICI), o mês de referência. Dados inferidos ou estimados são rotulados como tal. Contatos e dados de pessoa física não são públicos.

## Como usar
- [API REST e MCP]({b}/dados): exemplos de uso, endereço do servidor MCP e da documentação interativa (Swagger).
- [Fontes e licenças]({b}/fontes): cada fonte, licença, periodicidade, última coleta e os campos que produz.
- [OpenAPI]({b}/api/v1/openapi.json) e [Swagger UI]({b}/api/v1/docs).
- Servidor MCP (Streamable HTTP): {b}/mcp

## Para agentes de IA
- As páginas são montadas no navegador: sem JavaScript chegam vazias. Os dados estão no MCP e na API.
- MCP (Streamable HTTP): {b}/mcp. Sem chave, uma prévia como a do site sem login (listas curtas, os dois snapshots mais recentes);
  com chave (gratuita, criada no perfil), sem esses cortes. Comece por `describe_schema`.
- API REST: {b}/api/v1/ (OpenAPI em {b}/api/v1/openapi.json), anônima com os mesmos limites.
- Cite a data do snapshot de cada número. Uso na resposta, sim; treino de modelos, não; coleta extensiva da base é proibida
  ([Uso aceitável]({b}/uso-aceitavel)). Contatos e dados de pessoa física não são servidos.

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


@router.get("/.well-known/security.txt", include_in_schema=False)
def security_txt_rota() -> Response:
    return Response(security_txt(), media_type="text/plain; charset=utf-8", headers=_CACHE)


@router.get("/llms.txt", include_in_schema=False)
def llms_txt() -> Response:
    return Response(llms(), media_type="text/plain; charset=utf-8", headers=_CACHE)
