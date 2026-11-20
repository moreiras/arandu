# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Camada de prefixos de um PTT no mapa: as rotas do looking glass, geolocalizadas pela base de IP e agregadas por cidade.

O mesmo cálculo serve o pipeline (`products.mapas_prefixos.ixp_prefixos` grava `maps/ixp_prefixes/{ptt}-{v4|v6}.json.gz`) e a
API, que lê o arquivo pronto e só calcula quando ele falta: no SP o IPv4 passa de 2 min, acima do limite de 100 s do proxy, e
segura o GIL enquanto isso."""
from __future__ import annotations

import gzip
import json
import os
from ipaddress import ip_network
from pathlib import Path
from typing import Optional

from core.common import codigo_valido, published_path
from core.geoip import extrair_geo

PASTA = "ixp_prefixes"
FAMILIAS = ("v4", "v6")
_VAZIO = {"type": "FeatureCollection", "features": []}


def slash20_blocks(prefix_str: str) -> list[str]:
    """Sub-blocos /20 que cobrem um prefixo IPv4. De /20 para cima, o /20 pai (1 elemento); /8–/19 expandidos (/8 → 4096);
    abaixo de /8, nada (não aparece em tabela de PTT)."""
    net = ip_network(prefix_str, strict=False)
    if net.prefixlen >= 20:
        addr_int = int(net.network_address) & (0xFFFFFFFF ^ ((1 << 12) - 1))
        return [str(ip_network((addr_int, 20), strict=False))]
    if net.prefixlen < 8:
        return []
    return [str(s) for s in net.subnets(new_prefix=20)]


def first_ip(prefix_str: str) -> str:
    return str(ip_network(prefix_str, strict=False).network_address)


def caminho(base: Path, date_str: str, code: str, afi: str) -> Optional[Path]:
    """`published/{data}/maps/ixp_prefixes/{ptt}-{afi}.json.gz`; None se o código ou a família não valem (viram nome de arquivo)."""
    if not codigo_valido(code) or afi not in FAMILIAS:
        return None
    return published_path(base, date_str, "maps", PASTA, f"{code}-{afi}.json.gz")


def arquivo_mmdb(base: Path) -> Optional[Path]:
    """A base mais recente: DB-IP City Lite; o GeoLite2 antigo só vale enquanto não houver DB-IP baixado."""
    achados = sorted((base / "raw" / "dbip").glob("dbip-city-lite-*.mmdb")) or \
        sorted((base / "raw" / "geolite2").glob("GeoLite2-City-*.mmdb"))
    return achados[-1] if achados else None


def rotas(doc: Optional[dict]) -> list[dict]:
    """Rotas de `routes-{afi}.json.gz` com o caminho sem prepends: `origin_asn` (último AS), `peer_asn` (o que anuncia ao
    route server) e `aspath_set` (para os filtros de AS no caminho)."""
    out: list[dict] = []
    for route in (doc or {}).get("routes", []):
        prefix = route.get("prefix")
        aspath = route.get("aspath") or []
        if not prefix or not aspath:
            continue
        dedup: list[int] = []
        for a in aspath:
            if not dedup or dedup[-1] != a:
                dedup.append(a)
        out.append({"prefix": prefix, "origin_asn": dedup[-1], "peer_asn": dedup[0], "aspath_set": frozenset(dedup)})
    return out


def prefixos_das_rotas(rs: list[dict], exclude_asns: Optional[frozenset] = None,
                       include_asns: Optional[frozenset] = None) -> dict[str, dict]:
    """prefixo → {origin_asns, peer_asns} somados de todas as rotas que passam pelos filtros de AS no caminho."""
    info: dict[str, dict] = {}
    for r in rs:
        if exclude_asns and r["aspath_set"] & exclude_asns:
            continue
        if include_asns and not include_asns.issubset(r["aspath_set"]):
            continue
        d = info.get(r["prefix"])
        if d is None:
            d = info[r["prefix"]] = {"origin_asns": set(), "peer_asns": set()}
        d["origin_asns"].add(r["origin_asn"])
        if r["peer_asn"] != r["origin_asn"]:
            d["peer_asns"].add(r["peer_asn"])
    return info


def geolocalizar(prefix_info: dict[str, dict], reader, afi: str, memo: Optional[dict] = None) -> dict:
    """FeatureCollection com um ponto por cidade: `block_count` (/20 no IPv4, prefixos no IPv6), `origin_asns` e `peer_asns`
    (até 20 cada). `memo` (bloco → geo) poupa consultas à base quando vários PTTs da mesma data são calculados juntos."""
    if reader is None or not prefix_info:
        return dict(_VAZIO, features=[])
    memo = {} if memo is None else memo
    city_agg: dict[tuple, dict] = {}
    for prefix, info in prefix_info.items():
        try:
            blocks = slash20_blocks(prefix) if afi == "v4" else [prefix]
        except ValueError:
            continue
        for block in blocks:
            if block in memo:
                geo = memo[block]
            else:
                try:
                    geo = extrair_geo(reader.get(first_ip(block)))
                except Exception:
                    geo = None
                memo[block] = geo
            if geo is None:
                continue
            key = (round(geo["lat"], 2), round(geo["lon"], 2))
            agg = city_agg.get(key)
            if agg is None:
                agg = city_agg[key] = {"lat": geo["lat"], "lon": geo["lon"], "city": geo["city"], "uf": geo["uf"],
                                       "country": geo["country"], "block_count": 0, "origin_asns": set(), "peer_asns": set()}
            agg["block_count"] += 1
            agg["origin_asns"].update(info["origin_asns"])
            agg["peer_asns"].update(info["peer_asns"])

    block_unit = "/20" if afi == "v4" else "prefix"
    features = []
    for agg in city_agg.values():
        props: dict = {"city": agg["city"], "uf": agg["uf"], "country": agg["country"], "block_count": agg["block_count"],
                       "block_unit": block_unit, "geo_confidence": "city_centroid"}
        if agg["origin_asns"]:
            props["origin_asns"] = sorted(agg["origin_asns"])[:20]
        if agg["peer_asns"]:
            props["peer_asns"] = sorted(agg["peer_asns"])[:20]
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [agg["lon"], agg["lat"]]},
                         "properties": props})
    return {"type": "FeatureCollection", "features": features}


def gravar(destino: Path, fc: dict, meta: dict) -> None:
    """Escrita atômica (temporário + rename): a API pode estar lendo a mesma data."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump({**meta, "type": "FeatureCollection", "features": fc.get("features", [])}, f, ensure_ascii=False)
    os.replace(tmp, destino)


def ler(base: Path, date_str: str, code: str, afi: str) -> Optional[dict]:
    """A camada pronta, só com `type` e `features` (o mesmo formato do cálculo na hora); None se o arquivo falta ou não abre."""
    p = caminho(base, date_str, code, afi)
    if p is None or not p.is_file():
        return None
    try:
        with gzip.open(p, "rt", encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("features"), list):
        return None
    return {"type": "FeatureCollection", "features": doc["features"]}
