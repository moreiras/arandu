# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`/meta/{tipo}/{id}`: HTML mínimo com título, descrição e Open Graph de uma entidade (sem SSR completo).

A interface é uma SPA, e quem não executa JavaScript (rastreadores de busca, prévias de link, assistentes) só vê o `index.html` genérico.
O nginx desvia para cá os pedidos de entidade que vêm desses agentes (`map $http_user_agent`); o navegador comum continua recebendo a SPA.
Fora de `/api/` (como o sitemap), não entra no OpenAPI. **Só dado de pessoa jurídica ou do próprio recurso de rede**: sem contato, e-mail,
telefone nem nome de pessoa física; o texto é derivado só do índice do snapshot (nunca de um cadastro de pessoa)."""
from __future__ import annotations

import re
from html import escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from api.store import Store
from core.site import SITE

router = APIRouter()
BASE = SITE.url            # endereço canônico do .env
MARCA = SITE.nome
UFS = {"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
       "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
       "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
       "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins"}


def _data_br(d: str) -> str:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", d or "")
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else (d or "")


def dados_da_entidade(store: Store, tipo: str, ident: str, date_str: str) -> tuple[str, str] | None:
    """(título, descrição) ou None se a entidade não existe no snapshot. O texto só usa campos do índice."""
    quando = _data_br(date_str)
    if tipo == "asn":
        if not ident.isdigit() or not any(str(a.get("asn")) == ident for a in store.asn_index(date_str)):
            return None
        return (f"AS{ident}",
                f"AS{ident}: prefixos anunciados, ROAs, relações com outros ASes e presença em PTTs, no snapshot de {quando}. Cada número com fonte e data.")
    if tipo == "ixp":
        cod = ident.lower()
        achado = next((i for i in store.ixp_index(date_str) if str(i.get("code", "")).lower() == cod), None)
        if not achado:
            return None
        nome = achado.get("name") or achado.get("nome") or cod.upper()
        cidade = achado.get("city") or achado.get("cidade") or achado.get("uf")
        return (f"PTT {cod.upper()}",
                f"PTT {nome}{f' ({cidade})' if cidade else ''}: participantes, sessões com os route servers e cobertura, no snapshot de {quando}.")
    if tipo == "operadora":
        achado = next((o for o in store.operadora_index(date_str) if str(o.get("cnpj")) == ident), None)
        if not achado:
            return None
        nome = achado.get("nome") or achado.get("razao_social") or achado.get("name") or ident
        return (f"Operadora {nome}",
                f"{nome}: assinantes declarados à Anatel, outorgas, rede e qualidade, no snapshot de {quando}.")
    if tipo == "uf":
        uf = ident.upper()
        if uf not in UFS:
            return None
        return (f"{UFS[uf]} ({uf})",
                f"{UFS[uf]}: mercado de banda larga, rede, interconexão e municípios, no snapshot de {quando}.")
    return None


def html_meta(tipo: str, ident: str, titulo: str, descricao: str) -> str:
    url = f"{BASE}/{tipo}/{ident}"
    t, d, u = escape(f"{titulo} · {MARCA}"), escape(descricao), escape(url, quote=True)
    return (
        '<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="UTF-8" />\n'
        f"<title>{t}</title>\n<meta name=\"description\" content=\"{escape(descricao, quote=True)}\" />\n"
        f'<link rel="canonical" href="{u}" />\n'
        f'<meta property="og:title" content="{escape(titulo + " · " + MARCA, quote=True)}" />\n'
        f'<meta property="og:description" content="{escape(descricao, quote=True)}" />\n'
        f'<meta property="og:type" content="website" />\n<meta property="og:url" content="{u}" />\n'
        f'<meta property="og:site_name" content="{MARCA}" />\n<meta name="twitter:card" content="summary" />\n'
        f"</head>\n<body>\n<h1>{escape(titulo)}</h1>\n<p>{d}</p>\n<p><a href=\"{u}\">Abrir a página completa</a></p>\n</body>\n</html>\n"
    )


@router.get("/meta/{tipo}/{ident:path}", include_in_schema=False)
def meta_entidade(tipo: str, ident: str, request: Request) -> HTMLResponse:
    store: Store = request.app.state.store
    date_str = store.latest()
    achado = dados_da_entidade(store, tipo, ident, date_str) if date_str else None
    if not achado:
        raise HTTPException(status_code=404, detail="entidade não encontrada")
    return HTMLResponse(html_meta(tipo, ident, *achado), headers={"Cache-Control": "public, max-age=3600"})
