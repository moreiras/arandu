# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tools de contatos do MCP: `asn_contatos` e `operadora_contatos`.

Só com chave de MCP (conta). A cobrança é da API (`POST /internal/contatos`, `api/contatos_cota.py`): mesmo custo (1 por AS revelado; a
operadora custa o número de ASNs do CNPJ), mesmos tetos por conta, por rede e global e o mesmo registro do site, de modo que a cota da conta
é uma só nos dois caminhos. O MCP não grava em `data/auth/`. Sem chave, a tool responde sem contato e diz como obter a chave.
"""
from __future__ import annotations

import os
from typing import Optional

import httpx

from mcp_server.contexto import _resolve, mcp

_SEM_CHAVE = ("Contatos exigem uma chave de MCP (gerada no perfil do site, com login) e seguem a mesma cota diária da conta no site. "
              "Sem chave, consulte a página do AS ou da operadora no site, com login.")


def _quem_chama() -> tuple[Optional[str], str]:
    """(conta_id da chave, IP do cliente). Sem pedido HTTP (chamada local, testes) ou sem chave, a conta é None."""
    try:
        req = mcp.get_context().request_context.request
    except (ValueError, LookupError, AttributeError):
        return None, ""
    if req is None:
        return None, ""
    estado = (getattr(req, "scope", None) or {}).get("state") or {}
    ip = (req.headers.get("x-real-ip") or (req.client.host if req.client else "")).split(",")[0].strip()
    return (estado.get("conta_id") if estado.get("access_tier") == "user" else None), ip


def _cliente() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=10.0)


async def _pedir(corpo: dict) -> dict:
    url = os.environ.get("MCP_API_URL", "http://api:8000").rstrip("/") + "/internal/contatos"
    async with _cliente() as http:
        r = await http.post(url, json=corpo, headers={"X-Internal-Token": os.environ.get("INTERNAL_API_TOKEN", "")})
    if r.status_code == 200:
        return r.json()
    try:
        detalhe = r.json().get("detail")
    except ValueError:
        detalhe = None
    if r.status_code == 429:
        raise ValueError(f"{detalhe or 'Cota de contatos da conta esgotada.'} Tente de novo depois de {r.headers.get('Retry-After', '?')} s.")
    raise ValueError(detalhe or f"Contatos indisponíveis no momento (HTTP {r.status_code}).")


async def _contatos(tipo: str, ident: str, servico: str, date: Optional[str]) -> dict:
    d = _resolve(date)
    conta, ip = _quem_chama()
    if not conta:
        return {"snapshot_date": d, "contatos_liberados": False, "motivo": _SEM_CHAVE}
    return await _pedir({"conta_id": conta, "ip": ip, "tipo": tipo, "id": ident, "servico": servico, "date": d})


@mcp.tool()
async def asn_contatos(asn: int, date: Optional[str] = None) -> dict:
    """Contatos de UM AS (PeeringDB, RDAP do Registro.br, Receita, Anatel), com origem e função. Só com chave de MCP; cada chamada gasta 1 da
    cota de contatos da conta, a mesma do site (tetos por 10 min, hora, dia e 30 dias). Nunca em lote: um AS por chamada.

    Args:
        asn: Número do AS.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    return await _contatos("asn", str(int(asn)), "fixa", date)


@mcp.tool()
async def operadora_contatos(cnpj: str, servico: str = "fixa", date: Optional[str] = None) -> dict:
    """Contatos de UMA operadora por CNPJ (PeeringDB dos ASNs do CNPJ, Receita, Anatel SCM ou SMP), com origem e função. Só com chave de
    MCP; custa o número de ASNs do CNPJ (mínimo 1) na cota de contatos da conta, a mesma do site.

    Args:
        cnpj: CNPJ de 14 dígitos, com ou sem formatação.
        servico: "fixa" (SCM, padrão) ou "movel" (SMP).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    if servico not in ("fixa", "movel"):
        raise ValueError('servico deve ser "fixa" ou "movel".')
    return await _contatos("operadora", cnpj, servico, date)
