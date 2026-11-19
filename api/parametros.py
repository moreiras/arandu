# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Parâmetros de consulta não declarados nas rotas GET da API.

A chave do cache (nginx e Cloudflare) inclui a query string inteira, e a API ignora parâmetros que não conhece: `?x=<aleatório>` faz toda
requisição passar pelo cache e chegar à API. Este middleware compara os parâmetros com os que a rota declara (mais os globais: `date`, `v`,
`opcional`) e, conforme `API_PARAMETROS_DESCONHECIDOS`:
- `registrar` (padrão): anota no log (`parametro_desconhecido`, com a rota e os nomes, nunca os valores) e segue;
- `rejeitar`: responde 400 barato, antes de qualquer cálculo;
- `off`: nada.
Ligar `rejeitar` só depois de o log mostrar que nenhum cliente legítimo (o próprio site, a documentação) manda parâmetro não declarado.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional
from urllib.parse import parse_qsl

import structlog

_log = structlog.get_logger("arandurape.parametros")
GLOBAIS = frozenset({"date", "v", "opcional"})


def _modo() -> str:
    m = os.environ.get("API_PARAMETROS_DESCONHECIDOS", "registrar").strip().lower()
    return m if m in ("registrar", "rejeitar", "off") else "registrar"


def tabela_do_openapi(esquema: dict) -> list[tuple[re.Pattern, str, frozenset]]:
    """(regex do caminho, caminho, parâmetros de consulta aceitos) de cada GET do OpenAPI. Caminhos fixos antes dos com variável, para
    `/asns/summary` não cair em `/asns/{asn}`. Rotas fora do esquema não são conferidas."""
    linhas = []
    for caminho, ops in (esquema.get("paths") or {}).items():
        op = ops.get("get")
        if not op or not caminho.startswith("/api/v1/"):
            continue
        nomes = frozenset(p["name"] for p in op.get("parameters") or [] if p.get("in") == "query") | GLOBAIS
        rx = re.compile("^" + re.sub(r"\\\{[^/]+?\\\}", "[^/]+", re.escape(caminho)) + "$")
        linhas.append((rx, caminho, nomes))
    linhas.sort(key=lambda x: (x[1].count("{"), -len(x[1])))
    return linhas


class ParametrosMiddleware:
    def __init__(self, app):
        self.app = app
        self._tabela: Optional[list] = None

    def _da_rota(self, scope) -> Optional[tuple[str, frozenset]]:
        if self._tabela is None:
            self._tabela = tabela_do_openapi(scope["app"].openapi())
        for rx, caminho, nomes in self._tabela:
            if rx.match(scope["path"]):
                return caminho, nomes
        return None

    async def __call__(self, scope, receive, send):
        modo = _modo()
        if (modo == "off" or scope["type"] != "http" or scope.get("method") != "GET" or not scope["path"].startswith("/api/v1/")
                or not scope.get("query_string")):
            return await self.app(scope, receive, send)
        nomes = {k for k, _ in parse_qsl(scope["query_string"].decode("latin-1"), keep_blank_values=True)}
        achou = self._da_rota(scope)
        if achou is None:
            return await self.app(scope, receive, send)
        rota, permitidos = achou
        extras = sorted(nomes - permitidos)
        if not extras:
            return await self.app(scope, receive, send)
        _log.warning("parametro_desconhecido", rota=rota, parametros=extras[:10], modo=modo)
        if modo == "registrar":
            return await self.app(scope, receive, send)
        corpo = json.dumps({"detail": f"Parâmetro não reconhecido nesta rota: {', '.join(extras[:10])}."}, ensure_ascii=False).encode()
        await send({"type": "http.response.start", "status": 400, "headers": [
            (b"content-type", b"application/json; charset=utf-8"), (b"content-length", str(len(corpo)).encode()),
            (b"cache-control", b"no-store")]})
        await send({"type": "http.response.body", "body": corpo})
