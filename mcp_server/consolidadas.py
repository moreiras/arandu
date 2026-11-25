# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tools consolidadas: uma tool por assunto, com o recorte escolhido por argumento.

Cada função só escolhe a tool de origem correspondente e repassa os argumentos; a lógica e as respostas são as dela (as de origem
seguem registradas, ocultas, como aliases). Não há `from __future__ import annotations` aqui de propósito: o FastMCP lê as anotações
da assinatura e elas precisam ser tipos, não texto.
"""
import inspect
from typing import Optional

from mcp_server import tools_bgp, tools_entidades, tools_visualizacao


def _repassa(alvo, **dados):
    """Chama `alvo` só com os argumentos que ele aceita e que o chamador informou (None = omitido); falta de obrigatório vira erro claro."""
    params = inspect.signature(alvo).parameters
    kwargs = {k: v for k, v in dados.items() if k in params and v is not None}
    faltam = [k for k, p in params.items() if p.default is inspect.Parameter.empty and k not in kwargs]
    if faltam:
        raise ValueError(f"faltam argumentos: {', '.join(faltam)}")
    return alvo(**kwargs)


_VIZ = {
    "asn_geo": tools_visualizacao.asn_geo,
    "ixp_geo": tools_visualizacao.ixp_geo,
    "hilbert_v4": tools_visualizacao.hilbert_v4,
    "hilbert_v6": tools_visualizacao.hilbert_v6,
    "hilbert_v4_detail": tools_visualizacao.hilbert_v4_detail,
    "ixp_hilbert_v4": tools_visualizacao.ixp_hilbert_v4,
    "ixp_hilbert_v4_detail": tools_visualizacao.ixp_hilbert_v4_detail,
    "ixp_hilbert_v6": tools_visualizacao.ixp_hilbert_v6,
    "map_asns": tools_visualizacao.map_asns,
    "map_asns_overview": tools_visualizacao.map_asns_overview,
    "map_pix": tools_visualizacao.map_pix,
    "map_prefixes": tools_visualizacao.map_prefixes,
}


def viz(kind: str, asn: Optional[int] = None, code: Optional[str] = None, layer: Optional[str] = None, slash8: Optional[int] = None,
        peer: Optional[int] = None, uf: Optional[str] = None, full: bool = False, date: Optional[str] = None) -> dict:
    """[AVANÇADA — blobs de visualização GeoJSON/Hilbert] Dados prontos para desenhar mapas; por padrão devolve resumo (contagens + amostra).

    `kind` escolhe o blob e quais argumentos valem:
    - asn_geo(asn, layer=fulltable_v4|fulltable_v6|ixp_v4|ixp_v6) · ixp_geo(code, layer=asns_members|asns_direct|asns_origin|prefixes_v4|prefixes_v6)
    - hilbert_v4 · hilbert_v6 · hilbert_v4_detail(slash8, layer)
    - ixp_hilbert_v4(code, peer) · ixp_hilbert_v4_detail(code, slash8, peer) · ixp_hilbert_v6(code, peer)
    - map_asns(uf) · map_asns_overview · map_pix · map_prefixes(uf)
    Use full=true só para o blob completo (pode ter MBs). Para localização em texto, prefira geo_localizar.

    Args:
        kind: Um dos nomes acima.
        full: Se true, o blob completo; senão, resumo + amostra.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    alvo = _VIZ.get(kind)
    if alvo is None:
        raise ValueError(f"kind inválido: '{kind}'. Aceitos: {', '.join(_VIZ)}")
    return _repassa(alvo, asn=asn, code=code, layer=layer, slash8=slash8, peer=peer, uf=uf, full=full, date=date)


def historico_snapshots(date: Optional[str] = None) -> dict:
    """Snapshots disponíveis ou o resumo de um deles.

    Sem `date`: as datas disponíveis e a mais recente (cada snapshot é imutável; as demais tools usam o mais recente por padrão).
    Com `date`: totais de ASNs, cobertura IPv6/IPv4, espaço de endereçamento e o status de coleta de cada fonte.

    Args:
        date: Data do snapshot (YYYY-MM-DD). Omita para listar.
    """
    return tools_entidades.get_snapshot(date) if date else tools_entidades.list_snapshots()


def asn_rede(asn: int, visao: str = "caminhos", date: Optional[str] = None) -> dict:
    """Como um AS aparece nos IXPs: caminhos AS_PATH ou estatísticas de peering.

    visao="caminhos": cadeias AS_PATH em cada IXP onde o AS é originador (não direto), com metadados dos nós.
    visao="ixp_peers": estatísticas de peering em cada IXP com sessão RS (prefixos próprios/de terceiros, espaço /24).

    Args:
        asn: Número do AS.
        visao: caminhos | ixp_peers.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    if visao == "caminhos":
        return tools_entidades.get_asn_paths(asn, date)
    if visao in ("ixp_peers", "ixp_participantes", "peers"):           # o texto já ofereceu "ixp_participantes": aceito como sinônimo
        return tools_entidades.get_asn_ixp_peers(asn, date)
    raise ValueError(f"visao inválida: '{visao}'. Aceitas: caminhos, ixp_peers")


def ixp_participantes(code: str, visao: str = "membros", afi: str = "v4", date: Optional[str] = None) -> dict:
    """Quem participa de um IXP: listas de membros ou estatísticas por peer (sessão RS).

    visao="membros": listas por família (asn_direct, asn_stub, br_asns_direct, br_asns_origin); volumosa nos IXPs grandes.
    visao="peers": por peer (sessão RS), total/próprios/de terceiros, ASes de origem e espaço /24 (usa `afi`).

    Args:
        code: Código do IXP (ex.: "sp").
        visao: membros | peers.
        afi: v4 ou v6 (só para visao="peers").
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    if visao == "membros":
        return tools_entidades.ixp_members(code, date)
    if visao == "peers":
        return tools_entidades.ixp_peers(code, afi, date)
    raise ValueError(f"visao inválida: '{visao}'. Aceitas: membros, peers")


def ixp_usuarios(code: Optional[str] = None, date: Optional[str] = None) -> dict:
    """Usuários finais BR estimados (IPv4) visíveis via os prefixos originados num IXP.

    Soma, por AS BR originador, usuários APNIC × (espaço IPv4 visível no IXP / espaço IPv4 total do AS). Com `code`: o IXP
    (estimated_users, contributing_asns). Sem `code`: {código: usuários} de todos.

    Args:
        code: Código do IXP (ex.: "sp"). Omita para todos.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    return tools_entidades.ixp_estimated_users(code, date) if code else tools_entidades.all_ixp_estimated_users(date)


def ixp_externo(code: Optional[str] = None, country: Optional[str] = None, br_only: bool = False, date: Optional[str] = None) -> dict:
    """IXPs externos ao IX.br (PeeringDB): a lista, ou os membros de um deles com os ASNs brasileiros marcados.

    Args:
        code: Código do IXP externo (ex.: "amsix", "decix-fra"). Omita para listar.
        country: Filtro ISO de país na lista (ex.: BR, NL, US).
        br_only: Com `code`, só membros brasileiros.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    if code:
        return tools_entidades.get_external_ixp(code, br_only, date)
    return tools_entidades.list_external_ixps(country, date)


def rota_rpki(prefix: Optional[str] = None, asn: Optional[int] = None, date: Optional[str] = None) -> dict:
    """RPKI: adoção de ROA/ASPA nos ASNs BR ou a validade de um prefixo.

    Sem `prefix`: resumo da adoção. Com `prefix` (e opcionalmente o `asn` de origem): validade ROA do prefixo.

    Args:
        prefix: Prefixo CIDR (ex.: "200.160.0.0/20").
        asn: AS de origem a validar (padrão: o observado).
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    return tools_bgp.rpki_prefix(prefix, asn, date) if prefix else tools_bgp.rpki_summary(date)
