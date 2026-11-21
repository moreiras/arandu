# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Identidade pública do site: nome, URL, esquema de URI do MCP, prefixo dos arquivos baixados, endereço do código-fonte e contatos.

Fonte única no Python; os valores vêm do ambiente (`.env`), com os padrões abaixo. O frontend recebe os mesmos valores na compilação
(`VITE_SITE_*`, ver `Dockerfile.frontend`). Nomes internos (pastas, módulos, cookies, chaves de armazenamento) não dependem disto.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

PADROES = {
    "SITE_NOME": "Arandurapé",
    "SITE_NOME_EXTENSO": "Mapa da Internet brasileira",
    "SITE_URL": "http://localhost",
    "SITE_MCP_ESQUEMA": "arandurape",
    "SITE_PREFIXO_ARQUIVOS": "arandurape",
    "SITE_SOFTWARE": "Arandurapé",
    # Onde está o código-fonte que esta instância roda (AGPL §13): quem modifica e serve o software aponta para o próprio código.
    "SITE_CODIGO_FONTE": "https://github.com/moreiras/arandu",
    # Contato geral (o mesmo padrão de `frontend/src/lib/site.ts`); o de segurança (`security.txt`, RFC 9116) cai no geral se vazio.
    "SITE_CONTATO": "arandurape@internetbitabit.com.br",
    "SITE_CONTATO_SEGURANCA": "",
}


@dataclass(frozen=True)
class Site:
    nome: str
    nome_extenso: str
    url: str
    mcp_esquema: str
    prefixo_arquivos: str
    software: str
    codigo_fonte: str = PADROES["SITE_CODIGO_FONTE"]
    contato: str = PADROES["SITE_CONTATO"]
    contato_seguranca: str = PADROES["SITE_CONTATO"]

    @property
    def titulo(self) -> str:
        """"Arandurapé — Mapa da Internet brasileira": título da home e do OpenAPI."""
        return f"{self.nome} — {self.nome_extenso}"

    def uri(self, caminho: str) -> str:
        """URI de recurso do MCP: `uri("glossario")` → `arandurape://glossario`."""
        return f"{self.mcp_esquema}://{caminho.lstrip('/')}"


def carregar(env: dict | None = None) -> Site:
    e = os.environ if env is None else env
    v = {k: (e.get(k) or "").strip() or padrao for k, padrao in PADROES.items()}
    return Site(nome=v["SITE_NOME"], nome_extenso=v["SITE_NOME_EXTENSO"], url=v["SITE_URL"].rstrip("/"),
                mcp_esquema=v["SITE_MCP_ESQUEMA"].removesuffix("://"), prefixo_arquivos=v["SITE_PREFIXO_ARQUIVOS"], software=v["SITE_SOFTWARE"],
                codigo_fonte=v["SITE_CODIGO_FONTE"].rstrip("/"), contato=v["SITE_CONTATO"],
                contato_seguranca=v["SITE_CONTATO_SEGURANCA"] or v["SITE_CONTATO"])


SITE = carregar()


#: Chave de MCP: `<esquema>_mcp_<id>_<segredo>` (id de 8 e segredo de 52 caracteres em base32). O esquema é só um rótulo legível, que
#: diz ao usuário de qual instância é a chave; quem autentica é o id com o HMAC do segredo. Por isso a verificação aceita qualquer
#: esquema: mudar `SITE_MCP_ESQUEMA` não invalida as chaves já emitidas (inclusive as antigas `arandu_mcp_…`).
FORMATO_CHAVE_MCP = re.compile(r"([a-z0-9][a-z0-9-]{0,30})_mcp_([A-Z2-7]{8})_([A-Z2-7]{40,})")


def prefixo_chave_mcp(site: Site | None = None) -> str:
    """Prefixo das chaves novas: `obint_mcp_` com `SITE_MCP_ESQUEMA=obint`."""
    esquema = re.sub(r"[^a-z0-9-]", "-", (site or SITE).mcp_esquema.lower()).strip("-")[:31] or "mcp"
    return f"{esquema}_mcp_"


def user_agent(site: Site | None = None) -> str:
    """User-Agent identificado das coletas: `arandurape/<VERSION> (+<SITE_URL>)`. O contato é a instância que coleta, por isso
    vem do `.env`: em produção `SITE_URL` precisa apontar para o endereço público."""
    from core.common import app_version   # import tardio: core.common é mais pesado e não depende deste módulo

    return f"arandurape/{app_version()} (+{(site or SITE).url})"


USER_AGENT = user_agent()


_NOME_ANTIGO = re.compile(r"\bARANDURAP[ÉE]\b|\bArandurap[ée]\b")


def _tem_nome_do_software(texto: str) -> bool:
    return "randurap" in texto or "RANDURAP" in texto


def com_identidade_nos_dados(valor, site: Site | None = None):
    """`com_identidade` aplicado aos valores de uma resposta (tool do MCP): os artefatos do pipeline dizem "o Arandurapé coletou" e a
    resposta tem de dizer o nome do site. Só os valores de texto mudam, nunca as chaves; sem nada a trocar devolve o mesmo objeto."""
    if isinstance(valor, str):
        return com_identidade(valor, site) if _tem_nome_do_software(valor) else valor
    if isinstance(valor, dict):
        novo = {k: com_identidade_nos_dados(v, site) for k, v in valor.items()}
        return valor if all(novo[k] is valor[k] for k in valor) else novo
    if isinstance(valor, (list, tuple)):
        novo_l = [com_identidade_nos_dados(v, site) for v in valor]
        if all(a is b for a, b in zip(novo_l, valor)):
            return valor
        return type(valor)(novo_l) if isinstance(valor, tuple) else novo_l
    return valor


def com_identidade_json(texto: str, site: Site | None = None) -> str:
    """O mesmo sobre um JSON já serializado (corpo de resposta da API). O nome entra escapado como string JSON; o teste barato vem antes."""
    if not _tem_nome_do_software(texto):
        return texto
    s = site or SITE
    nome = json.dumps(s.nome, ensure_ascii=False)[1:-1]
    return _NOME_ANTIGO.sub(lambda _m: nome, texto.replace("arandurape://", f"{s.mcp_esquema}://"))


def com_identidade(texto, site: Site | None = None):
    """Textos de saída (OpenAPI, catálogo de consulta, instruções e descrições do MCP) com o nome e o esquema de URI do `.env`:
    `arandurape://x` → `<SITE_MCP_ESQUEMA>://x` e "Arandurapé" → `SITE_NOME`. Recebe também dict e lista (percorre os valores). Os docstrings
    seguem escritos com o nome do software, que serve de marcador; nomes internos (módulos, chaves) não passam por aqui."""
    s = site or SITE
    if isinstance(texto, str):
        return _NOME_ANTIGO.sub(s.nome, texto.replace("arandurape://", f"{s.mcp_esquema}://"))
    if isinstance(texto, dict):
        return {k: com_identidade(v, s) for k, v in texto.items()}
    if isinstance(texto, list):
        return [com_identidade(v, s) for v in texto]
    return texto
