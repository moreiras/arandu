# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Contexto comum das tools do MCP: o objeto `mcp`, o `Store` do processo, a resolução de data e os auxiliares das tools de visualização.

Contexto comum do MCP, separado de `app.py`; as tools ficam em `tools_*.py` e `app.py` só as monta.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from mcp_server.instrucoes import _INSTRUCTIONS
from core.site import SITE

_MCP_ALLOWED_HOSTS = [
    "127.0.0.1",
    "127.0.0.1:*",
    "localhost",
    "localhost:*",
    "[::1]",
    "[::1]:*",
]

_MCP_ALLOWED_ORIGINS = [
    "http://127.0.0.1",
    "http://127.0.0.1:*",
    "http://localhost",
    "http://localhost:*",
    "http://[::1]",
    "http://[::1]:*",
]



def _hosts_extras() -> list[str]:
    """Hosts além de localhost: o do `SITE_URL` e os de `MCP_HOSTS_EXTRAS` (vírgula), como o IP de um
    ambiente de teste. Sem isso a proteção contra DNS rebinding responde 421 a quem chama o MCP por outro nome."""
    do_site = urlparse(SITE.url).hostname or ""
    extras = [h.strip().lower() for h in os.environ.get("MCP_HOSTS_EXTRAS", "").split(",") if h.strip()]
    return list(dict.fromkeys(h for h in [do_site, f"www.{do_site}" if do_site else "", *extras] if h and h not in _MCP_ALLOWED_HOSTS))


for _h in _hosts_extras():
    _MCP_ALLOWED_HOSTS += [_h, f"{_h}:*"]
    _MCP_ALLOWED_ORIGINS += [f"{esq}://{_h}{porta}" for esq in ("http", "https") for porta in ("", ":*")]


def _snapshots() -> Optional[list[str]]:
    """Datas publicadas, ou None quando a Store não as lista (Stores falsas dos testes): aí a data não é conferida na entrada."""
    try:
        return _store.list_snapshots()
    except AttributeError:
        return None


_PTTS_CACHE: dict = {}


def _ptts_do_snapshot() -> Optional[dict[str, str]]:
    """{código: cidade} dos PTTs do IX.br no snapshot mais recente (o sintético dos testes tem os seus)."""
    try:
        d = _store.latest()
        if d not in _PTTS_CACHE:
            _PTTS_CACHE.clear()
            _PTTS_CACHE[d] = {e["code"]: e.get("name") or e["code"] for e in _store.ixp_index(d) if e.get("code")}
        return _PTTS_CACHE[d]
    except Exception:
        return None


# Toda tool só consulta o snapshot: nada escreve, repetir dá o mesmo resultado e nada sai do serviço. Os clientes que pedem confirmação
# antes de uma tool sem `readOnlyHint` (ou a tratam como ação de escrita) deixam de pedir.
SO_LEITURA = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)


class _Servidor(FastMCP):
    """FastMCP que não lista os aliases obsoletos (`ocultas`), mas continua atendendo a chamada por esses nomes, e que anota toda tool
    como só leitura (`SO_LEITURA`), inclusive as registradas por `add_tool` (aliases e tools geradas das capacidades)."""

    def __init__(self, *a, **kw):
        self.ocultas: set[str] = set()
        super().__init__(*a, **kw)

    def add_tool(self, fn, *a, annotations: Optional[ToolAnnotations] = None, **kw):
        return super().add_tool(fn, *a, annotations=annotations or SO_LEITURA, **kw)

    async def list_tools(self):
        return [t for t in await super().list_tools() if t.name not in self.ocultas]

    async def call_tool(self, name, arguments):
        """Normaliza os argumentos antes da validação e compacta a resposta (`mcp_server/entrada.py`).
        Todo ajuste volta em `ajustes`; valor sem leitura única vira erro com a instrução de conserto."""
        from mcp.server.fastmcp.exceptions import ToolError
        from mcp_server import entrada

        entrada.registrar_fonte_ptts(_ptts_do_snapshot)
        tool = self._tool_manager.get_tool(name)
        if tool is None:
            visiveis = [t for t in self._tool_manager._tools if t not in self.ocultas]
            raise ToolError(entrada.tool_desconhecida(name, visiveis))
        try:
            args, ajustes = entrada.normalizar(name, arguments, tool.parameters, _snapshots)
        except entrada.EntradaInvalida as exc:
            raise ToolError(f"Error executing tool {name}: {exc}") from exc
        return entrada.compactar(await super().call_tool(name, args), ajustes)


mcp = _Servidor(
    SITE.mcp_esquema,                                  # nome do servidor
    instructions=_INSTRUCTIONS,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_MCP_ALLOWED_HOSTS,
        allowed_origins=_MCP_ALLOWED_ORIGINS,
    ),
)

class _LojaAtual:
    """O `Store` do processo, lido de `mcp_server.app._store` a cada uso: há uma só por processo (cache lazy de snapshot, seguro para
    leitura concorrente) e os testes a trocam por uma sobre o dataset sintético depois do import."""

    def __getattr__(self, nome):
        import sys
        return getattr(sys.modules["mcp_server.app"]._store, nome)


_store = _LojaAtual()

# Campos de listas grandes de membros — servidos por ixp_members, fora do doc slim
# (mesma convenção de api/routes/ixps.py).
_MEMBER_LIST_FIELDS = frozenset(
    {"asn_direct", "asn_stub", "br_asns_direct", "br_asns_origin"}
)

# Campos de ordenação aceitos por list_asns (espelha api/routes/asns.py).
_SORT_FIELDS = frozenset({
    "asn", "name",
    "apnic_users", "apnic_v6_users", "pct_v6",
    "ixps_direct_count", "ixps_origin_v4_count", "ixps_origin_v6_count",
    "has_rpki", "has_aspa", "external_ixps_count",
})


def _resolve(date: Optional[str]) -> str:
    """Resolve a data informada ou o snapshot mais recente; erro claro se não houver."""
    resolved = _store.resolve_date(date)
    if resolved is None:
        raise ValueError("Nenhum snapshot publicado disponível no servidor.")
    return resolved


# Camadas das tools de geo (espelham api/routes/asn_geo.py e ixp_geo.py).
_ASN_GEO_LAYERS = {
    "fulltable_v4": "Prefixos IPv4 na full table global — próprios e de clientes",
    "fulltable_v6": "Prefixos IPv6 na full table global — próprios e de clientes",
    "ixp_v4": "Prefixos IPv4 por PTT — direto (próprios+clientes) e indireto (próprios)",
    "ixp_v6": "Prefixos IPv6 por PTT — direto (próprios+clientes) e indireto (próprios)",
}
_IXP_GEO_LAYERS = {
    "asns_members": "ASNs membros do IXP (lista do IX.br)",
    "asns_direct": "ASNs com prefixos anunciados diretamente no IXP (lidos do LG)",
    "asns_origin": "ASNs brasileiros de origem dos prefixos no IXP (lidos do LG)",
    "prefixes_v4": "Prefixos IPv4 anunciados no IXP (agregados por cidade, blocos /20)",
    "prefixes_v6": "Prefixos IPv6 anunciados no IXP (agregados por cidade)",
}

# Prefixo de docstring das tools de visualização (blobs).
_ADV = (
    "[AVANÇADA — blob de visualização (GeoJSON/Hilbert)]. Por padrão devolve um "
    "resumo (contagens + amostra). Use full=true só se precisar do blob completo "
    "para render/coordenadas; para localização textual prefira geo_coords.\n\n"
)


def adv_tool(fn):
    """Registra uma tool de visualização prefixando _ADV no docstring antes do registro.

    O FastMCP captura a descrição (docstring) no momento da decoração, então o prefixo
    precisa ser aplicado aqui, e não por reatribuição posterior de __doc__.
    """
    fn.__doc__ = _ADV + (fn.__doc__ or "")
    return mcp.tool()(fn)


def _geojson_summary(gj: dict, full: bool, sample: int = 5) -> dict:
    """GeoJSON completo se full; senão metadados + contagem + amostra de features."""
    if full:
        return gj
    feats = gj.get("features", []) or []
    out = {k: v for k, v in gj.items() if k != "features"}
    out["feature_count"] = len(feats)
    out["features_sample"] = feats[:sample]
    out["_note"] = "Resumo. Use full=true para o GeoJSON completo (pode ser grande)."
    return out


def _hilbert_v4_summary(data: dict, full: bool) -> dict:
    """Arrays /16 completos se full; senão contagem de células não-nulas por camada."""
    if full:
        return data
    out: dict = {}
    for layer, arr in data.items():
        if isinstance(arr, list):
            out[layer] = {
                "cells": len(arr),
                "nonzero_cells": sum(1 for x in arr if x),
                "sum": sum(arr),
            }
        else:
            out[layer] = arr
    out["_note"] = "Resumo por camada. Use full=true para os arrays /16 (65536 ints)."
    return out


def _hilbert_v6_summary(data: dict, full: bool) -> dict:
    """Índices /32 completos se full; senão contagem de células ativas por bloco/camada."""
    if full:
        return data
    out: dict = {}
    for block, layers in data.items():
        if isinstance(layers, dict):
            out[block] = {
                lyr: (len(v) if isinstance(v, list) else v) for lyr, v in layers.items()
            }
        else:
            out[block] = layers
    out["_note"] = "Contagem de células /32 ativas. Use full=true para os índices."
    return out
