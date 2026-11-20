# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Mapas de prefixos e de ASNs e densidade Hilbert: `hilbert_v4.json`, `hilbert_v6.json`,
`maps/prefixes.geojson`, `maps/global_prefixes.geojson` e `maps/asns.geojson`."""
from __future__ import annotations

import ipaddress
import json
import re
from pathlib import Path

from core import intermediarios
from core.common import normalized_path, now_iso, published_path
from core.jsonio import carregar_json, carregar_json_gz


def _prefix_to_16_density(prefix: str) -> list[tuple[int, int]]:
    """Retorna lista de (bloco_idx, count_/24) para um prefixo IPv4 CIDR."""
    try:
        net = ipaddress.ip_network(prefix, strict=False)
    except ValueError:
        return []
    if net.version != 4:
        return []
    pl = net.prefixlen
    first = int(net.network_address)
    a = (first >> 24) & 0xFF
    b = (first >> 16) & 0xFF
    if pl >= 24:
        return [(a * 256 + b, 1)]
    if pl >= 16:
        return [(a * 256 + b, 2 ** (24 - pl))]
    # Spans multiple /16 blocks
    n16 = 2 ** (16 - pl)
    base = a * 256 + b
    return [(base + i, 256) for i in range(n16) if base + i < 65536]


def compute_density(prefixes) -> list[int]:
    """Retorna lista de 65536 inteiros (0-256): /24s por bloco /16."""
    density = [0] * 65536
    for prefix in prefixes:
        for idx, count in _prefix_to_16_density(prefix):
            density[idx] = min(256, density[idx] + count)
    return density


def _slash24_set(prefixes) -> set[int]:
    """Conjunto de índices de blocos /24 cobertos pelos prefixos (para sets pequenos)."""
    covered: set[int] = set()
    for pstr in prefixes:
        try:
            net = ipaddress.ip_network(pstr, strict=False)
        except ValueError:
            continue
        if net.version != 4 or net.prefixlen < 8:
            continue
        if net.prefixlen >= 24:
            covered.add(int(net.network_address) >> 8)
        else:
            n24 = 1 << (24 - net.prefixlen)
            base = int(net.network_address) >> 8
            covered.update(range(base, base + n24))
    return covered


def _slash24_bitset(prefixes) -> bytearray:
    """Bitset de 2MB cobrindo todos os /24 dos prefixos (para listas grandes)."""
    bits = bytearray(1 << 21)  # 2^24 bits / 8 = 2MB
    for pstr in prefixes:
        try:
            net = ipaddress.ip_network(pstr, strict=False)
        except ValueError:
            continue
        if net.version != 4 or net.prefixlen < 8:
            continue
        if net.prefixlen >= 24:
            idx = int(net.network_address) >> 8
            bits[idx >> 3] |= 1 << (idx & 7)
        else:
            n24 = 1 << (24 - net.prefixlen)
            base = int(net.network_address) >> 8
            for i in range(n24):
                idx = base + i
                bits[idx >> 3] |= 1 << (idx & 7)
    return bits


def _density_from_slash24_intersection(rir_24s: set[int], global_bits: bytearray) -> list[int]:
    """Densidade: /24s alocados ao BR que estão presentes na full table."""
    density = [0] * 65536
    for idx24 in rir_24s:
        if global_bits[idx24 >> 3] & (1 << (idx24 & 7)):
            block16 = idx24 >> 8
            if block16 < 65536:
                density[block16] = min(256, density[block16] + 1)
    return density


def build_hilbert_v4(
    base: Path,
    date_str: str,
    global_br_prefixes: set[str],
    ixp_all_prefixes: set[str],
    log,
) -> dict:
    """
    Computa 5 mapas de densidade /16 para o mapa de Hilbert.
    Retorna dict com chaves: rir_br, global_br, global_all, ixp_all, rir_br_visible.
    Cada valor é uma lista de 65536 inteiros (0-256 = /24s no bloco /16).
    """
    norm_dir = normalized_path(base, date_str, "summary")

    # rir_br — prefixos atribuídos pelo Registro.br
    log.info("hilbert: computing rir_br density")
    rir_prefixes: list[str] = []
    registro_br_path = norm_dir / "registro_br.json.gz"
    if registro_br_path.exists():
        reg = carregar_json_gz(registro_br_path)
        if reg:
            for asn in reg.get("asns", []):
                rir_prefixes.extend(asn.get("prefixes_v4", []))
    rir_br = compute_density(rir_prefixes)
    log.info("hilbert: rir_br done", total_prefixes=len(rir_prefixes))

    # global_all — todos os prefixos da full table
    log.info("hilbert: computing global_all density")
    global_all_prefixes: list[str] = []
    ft_path = norm_dir / "prefix-set-v4.json.gz"
    if ft_path.exists():
        global_all_prefixes = carregar_json_gz(ft_path) or []
    global_all = compute_density(global_all_prefixes)
    log.info("hilbert: global_all done", total_prefixes=len(global_all_prefixes))

    # global_br — prefixos de ASNs BR na full table (coletados durante build_asn_index)
    log.info("hilbert: computing global_br density", prefixes=len(global_br_prefixes))
    global_br = compute_density(global_br_prefixes)

    # ixp_all — prefixos presentes em qualquer IXP (coletados durante build_asn_index)
    log.info("hilbert: computing ixp_all density", prefixes=len(ixp_all_prefixes))
    ixp_all = compute_density(ixp_all_prefixes)

    # rir_br_visible — interseção: alocado ao BR E visível na full table (precisão /24)
    log.info("hilbert: computing rir_br_visible (intersection at /24 level)")
    rir_24s = _slash24_set(rir_prefixes)
    global_bits = _slash24_bitset(global_all_prefixes)
    rir_br_visible = _density_from_slash24_intersection(rir_24s, global_bits)
    log.info("hilbert: rir_br_visible done",
             rir_slash24s=len(rir_24s),
             visible_slash24s=sum(1 for idx in rir_24s
                                  if global_bits[idx >> 3] & (1 << (idx & 7))))

    return {
        "rir_br": rir_br,
        "global_br": global_br,
        "global_all": global_all,
        "ixp_all": ixp_all,
        "rir_br_visible": rir_br_visible,
    }


# ---------------------------------------------------------------------------
# Hilbert IPv6 — presença /32 por bloco RIR (índices esparsos)
# ---------------------------------------------------------------------------

_V6_UNIT = 32
_V6_UNIT_SHIFT = 128 - _V6_UNIT  # 96

# Os 6 blocos RIR exibidos no mapa IPv6: (base_addr, base_prefix_len)
_V6_BLOCKS: dict[str, tuple[str, int]] = {
    "legacy":  ("2001::", 16),   # 2001::/16 → 2^16 = 65536 células /32
    "lacnic":  ("2800::", 12),   # 2800::/12 → 2^20 = 1048576 células /32
    "arin":    ("2600::", 12),
    "ripe":    ("2a00::", 12),
    "apnic":   ("2400::", 12),
    "afrinic": ("2c00::", 12),
}

# Metadados de cada bloco pré-computados para evitar re-parsing a cada prefixo
_V6_BLOCK_META: dict[str, tuple[int, int, int]] = {
    name: (
        int(ipaddress.ip_address(base_str)),
        1 << (128 - base_len),      # tamanho do bloco em espaço de endereços
        1 << (_V6_UNIT - base_len), # total de células (2^16 ou 2^20)
    )
    for name, (base_str, base_len) in _V6_BLOCKS.items()
}


def _v6_prefix_to_cells(net: "ipaddress.IPv6Network") -> dict[str, range]:
    """
    Projeta uma rede IPv6 nos 6 blocos RIR.
    Retorna dict block_name → range de índices de células /32 (exclusivo superior).
    """
    net_int = int(net.network_address)
    net_end = net_int + (1 << (128 - net.prefixlen))
    result: dict[str, range] = {}
    for block_name, (base_int, block_addr_size, block_cells) in _V6_BLOCK_META.items():
        block_end = base_int + block_addr_size
        start = max(net_int, base_int)
        end = min(net_end, block_end)
        if start >= end:
            continue
        cell_start = (start - base_int) >> _V6_UNIT_SHIFT
        if net.prefixlen >= _V6_UNIT:
            cell_end = cell_start + 1          # prefixo mais específico que /32
        else:
            cell_end = min((end - base_int) >> _V6_UNIT_SHIFT, block_cells)
        if cell_start < cell_end:
            result[block_name] = range(cell_start, cell_end)
    return result


def _compute_v6_sparse(prefixes) -> dict[str, list[int]]:
    """
    Dado um iterável de prefixos IPv6, retorna índices de /32 ativos por bloco.
    Resultado: dict block_name → lista ordenada de índices de células ativas.
    """
    cells: dict[str, set[int]] = {name: set() for name in _V6_BLOCKS}
    for prefix_str in prefixes:
        try:
            net = ipaddress.ip_network(prefix_str, strict=False)
        except ValueError:
            continue
        if net.version != 6:
            continue
        for block_name, r in _v6_prefix_to_cells(net).items():
            cells[block_name].update(r)
    return {name: sorted(s) for name, s in cells.items()}


def build_hilbert_v6(
    base: Path,
    date_str: str,
    ixp_all_v6: set[str],
    global_br_v6: set[str],
    log,
) -> dict:
    """
    Computa mapas de presença /32 IPv6 (índices esparsos) para 6 blocos RIR.
    5 camadas: rir_br, global_br, global_all, ixp_all, rir_br_visible.
    Retorna dict com chaves legacy/lacnic/arin/ripe/apnic/afrinic.
    """
    norm_dir = normalized_path(base, date_str, "summary")

    # rir_br — prefixos IPv6 atribuídos ao Brasil pelo Registro.br
    log.info("hilbert_v6: loading rir_br (registro_br prefixes_v6)")
    rir_br_prefixes: list[str] = []
    registro_br_path = norm_dir / "registro_br.json.gz"
    if registro_br_path.exists():
        reg = carregar_json_gz(registro_br_path)
        if reg:
            for asn in reg.get("asns", []):
                rir_br_prefixes.extend(asn.get("prefixes_v6", []))
    log.info("hilbert_v6: rir_br loaded", prefixes=len(rir_br_prefixes))

    # global_all — todos os prefixos IPv6 da full table
    log.info("hilbert_v6: loading global IPv6 prefix set")
    global_all_prefixes: list[str] = []
    ft_path = norm_dir / "prefix-set-v6.json.gz"
    if ft_path.exists():
        global_all_prefixes = carregar_json_gz(ft_path) or []
    log.info("hilbert_v6: global_all loaded", prefixes=len(global_all_prefixes))

    rir_cells   = _compute_v6_sparse(rir_br_prefixes)
    log.info("hilbert_v6: rir_br computed",
             cells={k: len(v) for k, v in rir_cells.items()})

    global_br_cells = _compute_v6_sparse(global_br_v6)
    log.info("hilbert_v6: global_br computed",
             prefixes=len(global_br_v6),
             cells={k: len(v) for k, v in global_br_cells.items()})

    ixp_cells = _compute_v6_sparse(ixp_all_v6)
    log.info("hilbert_v6: ixp_all computed",
             prefixes=len(ixp_all_v6),
             cells={k: len(v) for k, v in ixp_cells.items()})

    global_cells = _compute_v6_sparse(global_all_prefixes)
    log.info("hilbert_v6: global_all computed",
             cells={k: len(v) for k, v in global_cells.items()})

    # rir_br_visible — interseção: alocado ao BR E visível na full table
    rir_visible_cells: dict[str, list[int]] = {}
    for block in _V6_BLOCKS:
        rir_set    = set(rir_cells[block])
        global_set = set(global_cells[block])
        rir_visible_cells[block] = sorted(rir_set & global_set)
    log.info("hilbert_v6: rir_br_visible computed",
             cells={k: len(v) for k, v in rir_visible_cells.items()})

    return {
        block: {
            "rir_br":         rir_cells[block],
            "global_br":      global_br_cells[block],
            "global_all":     global_cells[block],
            "ixp_all":        ixp_cells[block],
            "rir_br_visible": rir_visible_cells[block],
        }
        for block in _V6_BLOCKS
    }


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------



CAMPOS_GLOBAL_PREFIXES = ("prefix", "ip_version", "origin_asn", "ixps_seen", "city", "country", "geo_confidence", "geo_source")


def escrever_global_prefixes_colunar(features: list[dict], destino: Path) -> int:
    """`maps/global_prefixes.col`: as mesmas linhas que `query_table` montaria do GeoJSON, em colunas.
    Ordem das chaves e valores idênticos ao dicionário `{**properties, lon, lat}`; é o que `/query` e o MCP leem."""
    from core import colunar

    cols: dict[str, list] = {k: [] for k in (*CAMPOS_GLOBAL_PREFIXES, "lon", "lat")}
    for ft in features:
        props = ft.get("properties") or {}
        coords = (ft.get("geometry") or {}).get("coordinates") or [None, None]
        for k in CAMPOS_GLOBAL_PREFIXES:
            cols[k].append(props.get(k))
        cols["lon"].append(coords[0])
        cols["lat"].append(coords[1] if len(coords) > 1 else None)
    return colunar.escrever(destino, cols, {"colecao": "global_prefixes"})


def build_global_prefixes_map(base: Path, date_str: str, log) -> int:
    """
    Gera maps/global_prefixes.geojson a partir de geo_global_prefixes.json.gz (`global_prefix_geo`).
    Retorna número de features escritas (0 se `global_prefix_geo` não rodou).
    """
    norm_dir = normalized_path(base, date_str, "summary")
    data = carregar_json_gz(norm_dir / "geo_global_prefixes.json.gz")
    if not data:
        log.info("geo_global_prefixes not found, skipping global_prefixes.geojson")
        return 0

    features: list[dict] = []
    for prefix, geo in data.get("prefixes", {}).items():
        lat = geo.get("lat")
        lon = geo.get("lon")
        if lat is None or lon is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "prefix": prefix,
                "ip_version": geo.get("ip_version"),
                "origin_asn": geo.get("origin_asn"),
                "ixps_seen": geo.get("ixps_seen", []),
                "city": geo.get("city", ""),
                "country": geo.get("country", ""),
                "geo_confidence": geo.get("geo_confidence", ""),
                "geo_source": geo.get("geo_source", ""),
            },
        })

    if not features:
        log.info("global_prefixes: no geolocated prefixes, skipping")
        return 0

    maps_dir = published_path(base, date_str, "maps")
    maps_dir.mkdir(parents=True, exist_ok=True)
    geojson = {
        "type": "FeatureCollection",
        "snapshot_date": date_str,
        "features": features,
    }
    (maps_dir / "global_prefixes.geojson").write_text(
        json.dumps(geojson, ensure_ascii=False), encoding="utf-8"
    )
    log.info("global_prefixes.geojson written", features=len(features))
    escrever_global_prefixes_colunar(features, maps_dir / "global_prefixes.col")
    log.info("global_prefixes.col written", rows=len(features))
    return len(features)


def build_geojson_maps(base: Path, date_str: str, log) -> dict:
    """
    Gera maps/asns.geojson, maps/prefixes.geojson e maps/global_prefixes.geojson.

    asns.geojson           — ASNs BR com coordenadas (fonte: geo_orgs.json.gz + orgs.json.gz)
    prefixes.geojson       — Prefixos BR geolocalizados (fonte: geo_prefixes.json.gz + registro_br)
    global_prefixes.geojson — Todos prefixos IX.br geolocalizados (fonte: geo_global_prefixes.json.gz)

    Ambos os arquivos são gerados apenas se os dados geo estiverem disponíveis.
    Retorna {"asns": int, "prefixes": int, "global_prefixes": int} com contagem de features.
    """
    norm_dir = normalized_path(base, date_str, "summary")

    # --- ASN GeoJSON ---
    asn_features: list[dict] = []

    # ASNs BR via CNPJ (geo_orgs.json.gz)
    geo_orgs_data = carregar_json_gz(norm_dir / "geo_orgs.json.gz")
    if geo_orgs_data:
        for asn_str, org in geo_orgs_data.get("orgs", {}).items():
            lat = org.get("lat")
            lon = org.get("lon")
            if lat is None or lon is None:
                continue
            asn_features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "asn": int(asn_str),
                    "name": org.get("name", ""),
                    "cnpj": org.get("cnpj", ""),
                    "razao_social": org.get("razao_social", ""),
                    "nome_fantasia": org.get("nome_fantasia", ""),
                    "uf": org.get("uf", ""),
                    "city": org.get("city", ""),
                    "country": "BR",
                    "geo_confidence": org.get("geo_confidence", ""),
                    "geo_source": org.get("geo_source", ""),
                },
            })
        log.info("asn geojson: br asns", features=len(asn_features))
    else:
        log.info("geo_orgs not found, skipping BR asns in asns.geojson")

    # ASNs internacionais via PeeringDB (geo_intl_asns.json.gz)
    geo_intl_data = carregar_json_gz(norm_dir / "geo_intl_asns.json.gz")
    intl_count = 0
    if geo_intl_data:
        for asn_str, org in geo_intl_data.get("asns", {}).items():
            lat = org.get("lat")
            lon = org.get("lon")
            if lat is None or lon is None:
                continue
            asn_features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "asn": int(asn_str),
                    "name": org.get("name", ""),
                    "uf": "",
                    "city": org.get("city", ""),
                    "country": org.get("country", ""),
                    "geo_confidence": org.get("geo_confidence", ""),
                    "geo_source": org.get("geo_source", ""),
                },
            })
            intl_count += 1
        log.info("asn geojson: intl asns", features=intl_count)
    else:
        log.info("geo_intl_asns not found, skipping intl asns in asns.geojson")

    # Melhoria de coordenadas via SCM: quando a outorga Anatel tem geo_confidence maior
    # que o endereço do Registro.br, usa as coordenadas do SCM para o marcador de sede.
    # Resolve divergências onde o endereço do CNPJ no Registro.br é menos preciso que
    # o endereço de sede da outorga SCM (ex: city_centroid → exact_address).
    _CONF_RANK = {
        "exact_address": 4,
        "cep_centroid":  3,
        "cnpj_cache":    3,
        "city_centroid": 2,
        "org_coords":    2,
    }
    scm_geo_data = carregar_json_gz(norm_dir / "anatel_scm_geo.json.gz")
    if scm_geo_data and asn_features:
        # Índice CNPJ → melhor registro SCM por confiança
        scm_by_cnpj: dict[str, dict] = {}
        for rec in scm_geo_data.get("scms", []):
            cnpj = rec.get("cnpj", "")
            if not cnpj or rec.get("lat") is None:
                continue
            conf = _CONF_RANK.get(rec.get("geo_confidence", ""), 1)
            existing = scm_by_cnpj.get(cnpj)
            if existing is None or conf > _CONF_RANK.get(existing.get("geo_confidence", ""), 1):
                scm_by_cnpj[cnpj] = rec

        improved = 0
        for feat in asn_features:
            cnpj = feat["properties"].get("cnpj", "")
            if not cnpj:
                continue
            scm = scm_by_cnpj.get(cnpj)
            if not scm:
                continue
            asn_conf = _CONF_RANK.get(feat["properties"].get("geo_confidence", ""), 1)
            scm_conf = _CONF_RANK.get(scm.get("geo_confidence", ""), 1)
            if scm_conf >= asn_conf:
                feat["geometry"]["coordinates"] = [scm["lon"], scm["lat"]]
                feat["properties"]["geo_confidence"] = scm["geo_confidence"]
                feat["properties"]["geo_source"] = f"scm/{scm.get('geo_source', 'nominatim')}"
                improved += 1
        log.info("asn geojson: scm coordinate improvement", improved=improved,
                 scm_cnpjs=len(scm_by_cnpj))

    if asn_features:
        log.info("asn geojson built", features=len(asn_features))
    else:
        log.info("no asn features, skipping asns.geojson")

    # --- Prefix GeoJSON ---
    geo_pfx_data = carregar_json_gz(norm_dir / "geo_prefixes.json.gz")
    prefix_features: list[dict] = []
    if geo_pfx_data:
        geo_prefixes = geo_pfx_data.get("prefixes", {})

        # Constrói reverse map prefix → asn a partir do `registro_br`
        registro_br_data = carregar_json_gz(norm_dir / "registro_br.json.gz") or {}
        prefix_to_asn: dict[str, int] = {}
        for asn_entry in registro_br_data.get("asns", []):
            asn = asn_entry["asn"]
            for p in asn_entry.get("prefixes_v4", []):
                prefix_to_asn[p] = asn
            for p in asn_entry.get("prefixes_v6", []):
                prefix_to_asn[p] = asn

        for prefix, geo in geo_prefixes.items():
            lat = geo.get("lat")
            lon = geo.get("lon")
            if lat is None or lon is None:
                continue
            try:
                ip_version = ipaddress.ip_network(prefix, strict=False).version
            except ValueError:
                continue
            prefix_features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "prefix": prefix,
                    "ip_version": ip_version,
                    "origin_asn": prefix_to_asn.get(prefix),
                    "city": geo.get("city", ""),
                    "uf": geo.get("uf", ""),
                    "country": geo.get("country", ""),
                    "geo_confidence": geo.get("geo_confidence", ""),
                    "geo_source": geo.get("geo_source", ""),
                },
            })
        log.info("prefix geojson built", features=len(prefix_features))
    else:
        log.info("geo_prefixes not found, skipping prefixes.geojson")

    if not asn_features and not prefix_features:
        global_count = build_global_prefixes_map(base, date_str, log)
        return {"asns": 0, "prefixes": 0, "global_prefixes": global_count}

    maps_dir = published_path(base, date_str, "maps")
    maps_dir.mkdir(parents=True, exist_ok=True)

    if asn_features:
        asns_geojson = {
            "type": "FeatureCollection",
            "snapshot_date": date_str,
            "features": asn_features,
        }
        (maps_dir / "asns.geojson").write_text(
            json.dumps(asns_geojson, ensure_ascii=False), encoding="utf-8"
        )

    if prefix_features:
        prefixes_geojson = {
            "type": "FeatureCollection",
            "snapshot_date": date_str,
            "features": prefix_features,
        }
        (maps_dir / "prefixes.geojson").write_text(
            json.dumps(prefixes_geojson, ensure_ascii=False), encoding="utf-8"
        )

    global_count = build_global_prefixes_map(base, date_str, log)
    return {"asns": len(asn_features), "prefixes": len(prefix_features), "global_prefixes": global_count}


def executar_hilbert(base: Path, date_str: str, log) -> dict:
    """Produto `mapas_prefixos`, parte 1: `hilbert_v4.json` e `hilbert_v6.json` (os conjuntos de prefixos vêm do índice de ASNs, em `build/`)."""
    conj = intermediarios.ler_conjuntos(base, date_str)
    pub = published_path(base, date_str)
    log.info("building hilbert density maps")
    v4 = build_hilbert_v4(base, date_str, conj["global_br_v4"], conj["ixp_all_v4"], log)
    (pub / "hilbert_v4.json").write_text(json.dumps(v4, ensure_ascii=False), encoding="utf-8")
    log.info("hilbert_v4.json written")
    v6 = build_hilbert_v6(base, date_str, conj["ixp_all_v6"], conj["global_br_v6"], log)
    (pub / "hilbert_v6.json").write_text(json.dumps(v6, ensure_ascii=False), encoding="utf-8")
    log.info("hilbert_v6.json written")
    return {}


def executar_mapas(base: Path, date_str: str, log) -> dict:
    """Produto `mapas_prefixos`, parte 2: `maps/prefixes.geojson`, `global_prefixes.geojson`, `asns.geojson` e `maps/ixp_prefixes/`."""
    from products.mapas_prefixos import ixp_prefixos
    log.info("building geojson maps")
    c = build_geojson_maps(base, date_str, log)
    n_ixp = ixp_prefixos.publicar(base, date_str, log)            # camadas de prefixos dos PTTs: na API, o SP passa de 2 min
    return {"geo_asns": c["asns"], "geo_prefixes": c["prefixes"], "geo_global_prefixes": c.get("global_prefixes", 0),
            "geo_ixp_prefixes": n_ixp}
