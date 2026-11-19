# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoints de prefixos — GET /prefixes, GET /prefixes/{prefix} e GET /prefixes/lookup.

Serve os prefixos IPv6/IPv4 alocados ao Brasil (Registro.br) com UF e país. A posição individual (latitude, longitude e
cidade) de um prefixo ou IP não sai da API: ela só é usada por dentro, e o mapa traz posição agregada.
"""
from __future__ import annotations

import ipaddress
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.privacidade import geo_org_publico
from api.store import Store
from core.geoip import sem_posicao

router = APIRouter()


def _features_to_items(features: list[dict]) -> list[dict]:
    """Converte features GeoJSON em dicts planos para listagem, sem a posição individual do prefixo."""
    return [sem_posicao(f.get("properties") or {}) for f in features]


@router.get(
    "/prefixes",
    summary="Listar prefixos BR geolocalizados (paginado)",
    description="""
Retorna a lista paginada de prefixos BR declarados no Registro.br com a UF segundo a
base de geolocalização (DB-IP City Lite). Requer que a etapa `prefix_geo` tenha sido executada para o snapshot.

Campos retornados: `prefix`, `ip_version`, `origin_asn`, `uf`, `country`,
`geo_confidence`, `geo_source`. Latitude, longitude e cidade por prefixo não são servidas.

Use `?ip_version=4` ou `?ip_version=6` para filtrar por versão.
Use `?uf=SP` para filtrar por estado.
""",
)
def list_prefixes(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
    page: int = Query(1, ge=1, description="Número da página (começa em 1)"),
    limit: int = Query(100, ge=1, le=1000, description="Itens por página (máx 1000)"),
    ip_version: Optional[int] = Query(
        None,
        description="Filtrar por versão IP (4 ou 6).",
        ge=4,
        le=6,
    ),
    uf: Optional[str] = Query(
        None,
        description="Filtrar por UF (sigla de dois caracteres, ex: SP, RJ).",
        min_length=2,
        max_length=2,
    ),
    origin_asn: Optional[int] = Query(
        None,
        description="Filtrar por ASN originador.",
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    geojson = store.geo_map(date_str, "prefixes")
    if geojson is None:
        raise HTTPException(404, "Dados de geolocalização de prefixos não disponíveis para este snapshot")

    features = geojson.get("features", [])

    if ip_version is not None:
        features = [
            f for f in features
            if (f.get("properties") or {}).get("ip_version") == ip_version
        ]
    if uf is not None:
        uf_upper = uf.upper()
        features = [
            f for f in features
            if (f.get("properties") or {}).get("uf", "").upper() == uf_upper
        ]
    if origin_asn is not None:
        features = [
            f for f in features
            if (f.get("properties") or {}).get("origin_asn") == origin_asn
        ]

    total = len(features)
    start = (page - 1) * limit
    page_features = features[start: start + limit]

    return {
        "snapshot_date": date_str,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 0,
        "items": _features_to_items(page_features),
    }


_INDICE_LPM: dict[str, dict] = {}


def _indice_lpm(store: Store, date_str: str) -> Optional[dict]:
    """{(versão, tamanho): {rede como inteiro: prefixo}} dos prefixos geolocalizados da data; guarda só as 2 últimas datas."""
    if date_str in _INDICE_LPM:
        return _INDICE_LPM[date_str]
    geojson = store.geo_map(date_str, "prefixes")
    if geojson is None:
        return None
    indice: dict[tuple[int, int], dict[int, str]] = {}
    for f in geojson.get("features", []):
        pref = (f.get("properties") or {}).get("prefix")
        try:
            rede = ipaddress.ip_network(pref, strict=False)
        except (TypeError, ValueError):
            continue
        indice.setdefault((rede.version, rede.prefixlen), {})[int(rede.network_address)] = pref
    while len(_INDICE_LPM) >= 2:
        _INDICE_LPM.pop(next(iter(_INDICE_LPM)))
    _INDICE_LPM[date_str] = indice
    return indice


def prefixo_mais_especifico(store: Store, date_str: str, addr) -> str:
    """O prefixo BR geolocalizado mais específico que contém `addr` (longest-prefix match). Levanta `HTTPException` 404 se não há."""
    indice = _indice_lpm(store, date_str)
    if indice is None:
        raise HTTPException(404, "Dados de geolocalização de prefixos não disponíveis para este snapshot")
    bits = addr.max_prefixlen
    n = int(addr)
    for tam in range(bits, -1, -1):
        nivel = indice.get((addr.version, tam))
        if not nivel:
            continue
        pref = nivel.get(n >> (bits - tam) << (bits - tam))
        if pref:
            return pref
    raise HTTPException(404, f"Nenhum prefixo conhecido contém {addr} no snapshot '{date_str}'")


@router.get(
    "/prefixes/lookup",
    summary="Prefixo mais específico que contém um IP",
    description="""
Dado um endereço IPv6 ou IPv4 (`?ip=200.160.2.3`), devolve o **prefixo mais específico** (longest-prefix match) entre os
prefixos BR do snapshot e o ASN originador, mais o campo `consulta`. É uma consulta de roteamento: não traz posição
nenhuma (nem UF), para que a API não funcione como serviço de geolocalização de IP. O detalhe do prefixo está em
`GET /prefixes/{prefix}`. 404 se nenhum prefixo conhecido o contém.
""",
)
def lookup_prefix(
    request: Request,
    ip: str = Query(..., description="Endereço IPv6 ou IPv4 (sem máscara)."),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente."),
) -> dict:
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        raise HTTPException(422, f"'{ip}' não é um endereço IP válido")
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    pref = prefixo_mais_especifico(store, date_str, addr)
    detalhe = get_prefix(pref, request, date_str)
    return {"prefix": pref, "ip_version": detalhe.get("ip_version"), "origin_asn": detalhe.get("origin_asn"),
            "snapshot_date": date_str, "consulta": str(addr)}


@router.get(
    "/prefixes/{prefix:path}",
    summary="Detalhes de um prefixo",
    description="""
Retorna os dados de um prefixo específico (ex: `177.75.0.0/16` ou `2804::/32`): ASN originador, UF e país segundo a base
de geolocalização (DB-IP City Lite), confiança e fonte. Inclui `geo_org` do ASN originador (se disponível). Latitude,
longitude e cidade do prefixo não são servidas.

Nota: apenas prefixos declarados no Registro.br (`registro_br`) estão disponíveis.
""",
)
def get_prefix(
    prefix: str,
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    geojson = store.geo_map(date_str, "prefixes")
    if geojson is None:
        raise HTTPException(404, "Dados de geolocalização de prefixos não disponíveis para este snapshot")

    feature = next(
        (
            f for f in geojson.get("features", [])
            if (f.get("properties") or {}).get("prefix") == prefix
        ),
        None,
    )
    if feature is None:
        raise HTTPException(404, f"Prefixo '{prefix}' não encontrado no snapshot '{date_str}'")

    result = {
        **sem_posicao(feature.get("properties") or {}),
        "snapshot_date": date_str,
        "geo_org": None,
    }

    # Enriquece com geo_org do ASN originador, se disponível
    asn = result.get("origin_asn")
    if asn is not None:
        asn_doc = store.asn_detail(date_str, int(asn))
        if asn_doc:
            result["geo_org"] = geo_org_publico(asn_doc.get("geo_org"))      # sem contato, endereço nem coordenada

    return result
