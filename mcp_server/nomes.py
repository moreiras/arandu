# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Nomes por domínio das tools do MCP e os aliases dos nomes antigos.

Nome novo = `<domínio>_<ação>` (`asn_`, `ixp_`, `rota_`, `operadora_`, `municipio_`, `uf_`, `outorga_`, `infra_`, `historico_`, `geo_`, `cdn_`, `grupo_`),
mais `query`, `describe_schema` e `viz`. As tools continuam definidas com o nome antigo em `tools_*.py`; `aplicar` registra a de nome novo
(com o envelope padrão) e transforma a antiga em **alias oculto**: some da listagem (`tools/list`), segue chamável, leva `[obsoleta]` na
descrição e devolve `aviso_obsoleta` na resposta. Remover um alias é apagar a linha daqui, depois de duas versões.
"""
from __future__ import annotations

import functools
import inspect
import re

from mcp_server import consolidadas

# novo nome → tool de origem (função registrada com o nome antigo)
RENOMEADAS = {
    "asn_detalhe": "get_asn", "asn_lista": "list_asns", "asn_lote": "get_asns", "geo_localizar": "geo_coords",
    "ixp_detalhe": "get_ixp", "ixp_lista": "list_ixps", "ixp_potencial": "ixp_potential", "ixp_proximos": "ixp_nearby",
    "ixp_assinantes": "ixp_assinantes", "cdn_presenca": "cdn_presence",
    "rota_prefixos": "list_prefixes", "rota_prefixo": "get_prefix", "rota_analise": "routing_analysis", "rota_estabilidade": "bgp_stability",
    "operadora_detalhe": "get_operator", "operadora_alcance": "operator_reach", "operadora_resolver": "resolve_operator",
    "operadora_acessos": "operator_accesses", "operadora_ranking": "top_operators", "operadora_divergencia": "access_divergence",
    "operadora_grupo": "economic_group", "historico_acessos": "access_history",
    "municipio_detalhe": "get_municipio", "municipio_banda_larga": "municipality_broadband", "municipio_resolver": "resolve_place",
    "uf_detalhe": "get_uf", "outorga_lista": "list_outorgas", "outorga_detalhe": "get_outorgas", "infra_proximos": "infra_nearby",
}
RENOMEADAS = {n: o for n, o in RENOMEADAS.items() if n != o}      # `ixp_assinantes` já nasceu com nome de domínio

# nova tool consolidada (função em `consolidadas`) → nomes antigos que ela substitui, com a chamada equivalente
CONSOLIDADAS = {
    "viz": {k: f'viz(kind="{k}", …)' for k in consolidadas._VIZ},
    "historico_snapshots": {"list_snapshots": "historico_snapshots()", "get_snapshot": "historico_snapshots(date=…)"},
    "asn_rede": {"get_asn_paths": 'asn_rede(visao="caminhos")', "get_asn_ixp_peers": 'asn_rede(visao="ixp_peers")'},
    "ixp_participantes": {"ixp_members": 'ixp_participantes(visao="membros")', "ixp_peers": 'ixp_participantes(visao="peers")'},
    "ixp_usuarios": {"ixp_estimated_users": "ixp_usuarios(code=…)", "all_ixp_estimated_users": "ixp_usuarios()"},
    "ixp_externo": {"list_external_ixps": "ixp_externo()", "get_external_ixp": "ixp_externo(code=…)"},
    "rota_rpki": {"rpki_summary": "rota_rpki()", "rpki_prefix": "rota_rpki(prefix=…)"},
}

# sem substituta com o mesmo formato: ficam ocultas e a descrição aponta o caminho
SO_OCULTAS = {
    "list_scms": "outorga_lista(servico=…) ou query(collection=\"scms\")",
    "get_scm": "outorga_detalhe(cnpj=…, servico=…)",
    "asn_names": "asn_lista(q=…) ou query(collection=\"asns\")",
    "asn_ix_presence": "asn_detalhe(asn=…) (campo ixp_presence) ou query(collection=\"asns\")",
}

# `get_asns` etc. não colidem: o regex só troca o nome inteiro, entre fronteiras de palavra
_ANTIGO_PARA_NOVO = {o: n for n, o in RENOMEADAS.items()}
for _novo, _olds in CONSOLIDADAS.items():
    for _o, _chamada in _olds.items():
        _ANTIGO_PARA_NOVO.setdefault(_o, _chamada.split("(")[0])
_PADRAO = re.compile(r"(?<![\w])(" + "|".join(sorted(map(re.escape, _ANTIGO_PARA_NOVO), key=len, reverse=True)) + r")(?![\w])")


def renomeia_citacoes(texto: str, preservar: frozenset = frozenset()) -> str:
    """Troca nos textos das tools novas as citações de tools pelo nome novo (a descrição vem do docstring, escrito com os nomes antigos).
    `preservar`: nomes que no texto são VALORES de parâmetro, não citações de tool (o `kind` de `viz`, a `visao` de `asn_rede`). Sem isso a
    descrição de `viz` saía "viz · viz · viz(slash8, layer)" e a de `asn_rede` oferecia `visao="ixp_participantes"`, que a tool recusa."""
    return _PADRAO.sub(lambda m: m.group(1) if m.group(1) in preservar else _ANTIGO_PARA_NOVO[m.group(1)], texto or "")


# valores de parâmetro das tools consolidadas que coincidem com nomes antigos de tool
PRESERVAR = {"viz": frozenset(consolidadas._VIZ), "asn_rede": frozenset({"ixp_peers"})}


def _assinatura(fn):
    return inspect.signature(fn, eval_str=True)


def _com_envelope(fn):
    """Envelope padrão das tools novas: toda resposta objeto traz `snapshot_date` (as que não traziam ganham a data resolvida)."""
    sig = _assinatura(fn)

    @functools.wraps(fn)
    def wrapper(*a, **kw):
        r = fn(*a, **kw)
        if isinstance(r, dict) and "snapshot_date" not in r and "date" in sig.parameters:
            from mcp_server.contexto import _resolve
            r = {"snapshot_date": _resolve(kw.get("date")), **r}
        return r

    wrapper.__signature__ = sig
    return wrapper


def _como_alias(fn, substituta: str):
    sig = _assinatura(fn)
    aviso = f"Nome obsoleto: use {substituta}."

    @functools.wraps(fn)
    def wrapper(*a, **kw):
        r = fn(*a, **kw)
        return {**r, "aviso_obsoleta": aviso} if isinstance(r, dict) else r

    wrapper.__signature__ = sig
    return wrapper


def _oculta(mcp, nome: str, substituta: str) -> None:
    tool = mcp._tool_manager._tools[nome]
    tool.fn = _como_alias(tool.fn, substituta)
    tool.description = f"[obsoleta — use {substituta}] " + (tool.description or "")
    mcp.ocultas.add(nome)


def aplicar(mcp) -> dict:
    """Registra as tools de nome novo e oculta as antigas. Devolve {antigo: substituto} (o mapa de aliases)."""
    tools = mcp._tool_manager._tools
    aliases: dict[str, str] = {}
    for novo, antigo in RENOMEADAS.items():
        origem = tools[antigo]
        mcp.add_tool(_com_envelope(origem.fn), name=novo, description=renomeia_citacoes(origem.description))
        aliases[antigo] = f"`{novo}`"
    for novo, olds in CONSOLIDADAS.items():
        fn = getattr(consolidadas, novo)
        mcp.add_tool(_com_envelope(fn), name=novo, description=renomeia_citacoes(inspect.getdoc(fn), PRESERVAR.get(novo, frozenset())))
        for antigo, chamada in olds.items():
            aliases[antigo] = f"`{chamada}`"
    aliases.update({o: f"`{s}`" for o, s in SO_OCULTAS.items()})
    for antigo, substituta in aliases.items():
        _oculta(mcp, antigo, substituta)
    return aliases
