# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tools de visualização do MCP (blobs GeoJSON/Hilbert, avançadas): resumo por padrão, `full=true` sob demanda."""
from __future__ import annotations

from typing import Optional

from mcp_server.contexto import (
    _ASN_GEO_LAYERS, _IXP_GEO_LAYERS, _geojson_summary, _hilbert_v4_summary, _hilbert_v6_summary, _resolve, _store, adv_tool,
)

# ---------------------------------------------------------------------------
# Visualização (blobs GeoJSON / Hilbert) — avançadas, full=true sob demanda
# ---------------------------------------------------------------------------

@adv_tool
def asn_geo(asn: int, layer: str = "fulltable_v4", full: bool = False, date: Optional[str] = None) -> dict:
    """Distribuição geográfica dos prefixos de um AS (GeoJSON).

    Args:
        asn: Número do AS.
        layer: Um de fulltable_v4, fulltable_v6, ixp_v4, ixp_v6.
        full: Se true, retorna o GeoJSON completo; senão, resumo + amostra.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    if layer not in _ASN_GEO_LAYERS:
        raise ValueError(f"layer inválido: '{layer}'. Aceitos: {', '.join(sorted(_ASN_GEO_LAYERS))}")
    d = _resolve(date)
    gj = _store.asn_geo(d, asn, layer)
    if gj is None:
        raise ValueError(f"AS{asn} não encontrado no snapshot {d}.")
    enriched = {**gj, "snapshot_date": d, "asn": asn, "layer": layer,
                "layer_description": _ASN_GEO_LAYERS[layer]}
    return _geojson_summary(enriched, full)


@adv_tool
def ixp_geo(code: str, layer: str = "asns_members", full: bool = False, date: Optional[str] = None) -> dict:
    """Distribuição geográfica de ASNs ou prefixos de um IXP (GeoJSON).

    Args:
        code: Código do IXP (ex.: "sp").
        layer: Um de asns_members, asns_direct, asns_origin, prefixes_v4, prefixes_v6.
        full: Se true, retorna o GeoJSON completo; senão, resumo + amostra.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    if layer not in _IXP_GEO_LAYERS:
        raise ValueError(f"layer inválido: '{layer}'. Aceitos: {', '.join(sorted(_IXP_GEO_LAYERS))}")
    d = _resolve(date)
    code = code.lower()
    gj = _store.ixp_geo(d, code, layer)
    if gj is None:
        raise ValueError(f"IXP '{code}' não encontrado no snapshot {d}.")
    enriched = {**gj, "snapshot_date": d, "ixp_code": code, "layer": layer,
                "layer_description": _IXP_GEO_LAYERS[layer]}
    return _geojson_summary(enriched, full)


@adv_tool
def hilbert_v4(full: bool = False, date: Optional[str] = None) -> dict:
    """Mapas de densidade Hilbert IPv4 (/16) globais: rir_br, global_br, global_all, ixp_all.

    Args:
        full: Se true, arrays de 65536 ints por camada; senão, contagens.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    data = _store.hilbert_v4(d)
    if data is None:
        raise ValueError(f"Dados Hilbert v4 indisponíveis no snapshot {d}.")
    return _hilbert_v4_summary(data, full)


@adv_tool
def hilbert_v6(full: bool = False, date: Optional[str] = None) -> dict:
    """Mapas de presença Hilbert IPv6 (/32) por bloco RIR (esparsos).

    Args:
        full: Se true, índices de células ativas; senão, contagens por bloco/camada.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    data = _store.hilbert_v6(d)
    if data is None:
        raise ValueError(f"Dados Hilbert v6 indisponíveis no snapshot {d}.")
    return _hilbert_v6_summary(data, full)


@adv_tool
def hilbert_v4_detail(slash8: int, layer: str = "global_all", full: bool = False, date: Optional[str] = None) -> dict:
    """Blocos /24 dentro de um /8 para zoom do Hilbert IPv4 global.

    Args:
        slash8: Número do bloco /8 (0-255).
        layer: global_all | global_br | rir_br | rir_br_visible | ixp_all.
        full: Se true, retorna o detalhe completo; senão, resumo.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    result = _store.hilbert_v4_detail(d, slash8, layer)
    if result is None:
        raise ValueError(f"Dados indisponíveis para /8 {slash8} camada '{layer}' em {d}.")
    return _hilbert_v4_summary(result, full) if isinstance(result, dict) else result


@adv_tool
def ixp_hilbert_v4(code: str, peer: Optional[int] = None, full: bool = False, date: Optional[str] = None) -> dict:
    """Mapa de densidade Hilbert IPv4 (/16) de um IXP. Com peer, separa próprios vs. terceiros.

    Args:
        code: Código do IXP (ex.: "sp").
        peer: ASN do peer para filtrar (opcional).
        full: Se true, arrays completos; senão, contagens.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    data = _store.ixp_hilbert_v4(d, code.lower(), peer)
    if data is None:
        raise ValueError(f"Dados Hilbert v4 indisponíveis para IXP '{code}' em {d}.")
    return _hilbert_v4_summary(data, full)


@adv_tool
def ixp_hilbert_v4_detail(code: str, slash8: int, peer: Optional[int] = None, full: bool = False, date: Optional[str] = None) -> dict:
    """Blocos /24 dentro de um /8 para zoom do Hilbert IPv4 de um IXP.

    Args:
        code: Código do IXP (ex.: "sp").
        slash8: Número do bloco /8 (0-255).
        peer: ASN do peer para filtrar (opcional).
        full: Se true, detalhe completo; senão, resumo.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    data = _store.ixp_hilbert_v4_detail(d, code.lower(), slash8, peer)
    if data is None:
        raise ValueError(f"Dados indisponíveis para IXP '{code}' /8 {slash8} em {d}.")
    return _hilbert_v4_summary(data, full) if isinstance(data, dict) else data


@adv_tool
def ixp_hilbert_v6(code: str, peer: Optional[int] = None, full: bool = False, date: Optional[str] = None) -> dict:
    """Mapa de presença Hilbert IPv6 (/32) de um IXP. Com peer, separa próprios vs. terceiros.

    Args:
        code: Código do IXP (ex.: "sp").
        peer: ASN do peer para filtrar (opcional).
        full: Se true, índices completos; senão, contagens.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    data = _store.ixp_hilbert_v6(d, code.lower(), peer)
    if data is None:
        raise ValueError(f"Dados Hilbert v6 indisponíveis para IXP '{code}' em {d}.")
    return _hilbert_v6_summary(data, full)


@adv_tool
def map_asns(uf: Optional[str] = None, full: bool = False, date: Optional[str] = None) -> dict:
    """Mapa (GeoJSON) dos ASNs BR geolocalizados pelo endereço da organização.

    Args:
        uf: Filtra por UF (2 letras).
        full: Se true, GeoJSON completo; senão, resumo + amostra.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    gj = _store.geo_map(d, "asns")
    if gj is None:
        raise ValueError(f"Geolocalização de ASNs indisponível no snapshot {d}.")
    if uf:
        u = uf.upper()
        gj = {**gj, "features": [f for f in gj.get("features", [])
                                 if ((f.get("properties") or {}).get("uf") or "").upper() == u]}
    return _geojson_summary(gj, full)


@adv_tool
def map_asns_overview(full: bool = False, date: Optional[str] = None) -> dict:
    """Mapa (GeoJSON) combinando ASNs BR (com visibilidade na FT) e os PIX dos PTTs.

    Args:
        full: Se true, GeoJSON completo; senão, resumo + amostra.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    gj = _store.asns_overview_map(d)
    if gj is None:
        raise ValueError(f"Geolocalização indisponível no snapshot {d}.")
    return _geojson_summary(gj, full)


@adv_tool
def map_pix(full: bool = False, date: Optional[str] = None) -> dict:
    """Mapa (GeoJSON) dos PIX (pontos físicos) do IX.br com localização conhecida.

    Args:
        full: Se true, GeoJSON completo; senão, resumo + amostra.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    return _geojson_summary(_store.pix_map(d), full)


@adv_tool
def map_prefixes(uf: Optional[str] = None, full: bool = False, date: Optional[str] = None) -> dict:
    """Mapa (GeoJSON) dos prefixos BR por ASN e município (base DB-IP City Lite).

    Agregado: cada feição é um (ASN originador, versão IP, município) com `prefix_count`; o ponto é o centroide do município. A posição
    individual de um prefixo não é servida.

    Args:
        uf: Filtra por UF (2 letras).
        full: Se true, GeoJSON completo; senão, resumo + amostra.
        date: Data do snapshot (YYYY-MM-DD). Omita para o mais recente.
    """
    d = _resolve(date)
    gj = _store.geo_map_prefixos_agregado(d)
    if gj is None:
        raise ValueError(f"Geolocalização de prefixos indisponível no snapshot {d}.")
    if uf:
        u = uf.upper()
        gj = {**gj, "features": [f for f in gj.get("features", [])
                                 if ((f.get("properties") or {}).get("uf") or "").upper() == u]}
    return _geojson_summary(gj, full)
