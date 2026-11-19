# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Índice de ASNs por IXP e visão global usado pelas métricas de IXP e pelos documentos de ASN."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from core.common import normalized_path

from products.ixp_metrics.entradas import _load_aspath_adj, _load_gz_json, _load_origin_prefixes, _load_rels


def _build_asn_index(
    date_str: str,
    base: Path,
    all_ixps: list[dict],
    log,
) -> dict[int, dict]:
    """Constrói índice global de ASNs a partir de todos os arquivos normalizados.

    Combina dados de 4 fontes distintas:
      1. relationships de cada IXP  → ixps_direct, ixps_origin
      2. origin-prefixes de cada IXP → prefixes_ixp (por IXP, por AFI)
      3. origin-prefixes da full table → prefixes_ft (visão global)
      4. routes de cada IXP          → upstreams_{afi}, downstreams_{afi}
      5. aspath-adj-{afi}.json.gz    → upstreams_global_{afi}, downstreams_global_{afi}

    Carrega e descarta cada arquivo sequencialmente para manter o pico de memória baixo;
    os sets de inteiros por ASN são mantidos em memória mas ocupam muito menos que as rotas.

    Args:
        date_str: Data do snapshot (YYYY-MM-DD)
        base:     Diretório raiz dos dados
        all_ixps: Lista de dicts com "code" dos IXPs a processar
        log:      Logger estruturado

    Returns: {asn: {
        "ixps_direct":        set(ixp_code),
        "ixps_origin":        set(ixp_code),
        "prefixes_ixp":       {ixp_code: {"v4": [...], "v6": [...]}},
        "prefixes_ft":        {"v4": [...], "v6": [...]},
        "upstreams_v4":       set(asn),  # vizinhos à esquerda nos IXPs (IPv4)
        "upstreams_v6":       set(asn),  # vizinhos à esquerda nos IXPs (IPv6)
        "downstreams_v4":     set(asn),  # vizinhos à direita nos IXPs (IPv4)
        "downstreams_v6":     set(asn),  # vizinhos à direita nos IXPs (IPv6)
        "upstreams_global_v4":   set(asn),  # vizinhos à esquerda no RouteViews (IPv4)
        "upstreams_global_v6":   set(asn),  # vizinhos à esquerda no RouteViews (IPv6)
        "downstreams_global_v4": set(asn),  # vizinhos à direita no RouteViews (IPv4)
        "downstreams_global_v6": set(asn),  # vizinhos à direita no RouteViews (IPv6)
    }}
    """
    idx: dict[int, dict] = defaultdict(lambda: {
        "ixps_direct":  set(),
        "ixps_origin":  set(),
        "prefixes_ixp": {},
        "prefixes_ft":  {"v4": [], "v6": []},
        "upstreams_v4":       set(),
        "upstreams_v6":       set(),
        "downstreams_v4":     set(),
        "downstreams_v6":     set(),
        "upstreams_global_v4":   set(),
        "upstreams_global_v6":   set(),
        "downstreams_global_v4": set(),
        "downstreams_global_v6": set(),
    })

    # Presença por IXP — carrega apenas relationships (compacto)
    for ixp in all_ixps:
        code = ixp["code"]
        for afi in ("v4", "v6"):
            rels = _load_rels(base, date_str, code, afi)
            if not rels:
                continue
            rd = rels.get("relationships", {})
            for asn in rd.get("asn_direct", []):
                idx[asn]["ixps_direct"].add(code)
            for asn in rd.get("asn_origin", []):
                idx[asn]["ixps_origin"].add(code)

    # Prefixos por IXP por ASN — do índice de origens (compacto)
    for ixp in all_ixps:
        code = ixp["code"]
        for afi in ("v4", "v6"):
            op = _load_origin_prefixes(base, date_str, code, afi)
            for asn_str, prefixes in op.items():
                asn = int(asn_str)
                entry = idx[asn]
                if code not in entry["prefixes_ixp"]:
                    entry["prefixes_ixp"][code] = {"v4": [], "v6": []}
                entry["prefixes_ixp"][code][afi] = prefixes

    # Prefixos na full table por ASN — do índice de origens da full table
    for afi in ("v4", "v6"):
        op = _load_origin_prefixes(base, date_str, "summary", afi)
        for asn_str, prefixes in op.items():
            idx[int(asn_str)]["prefixes_ft"][afi] = prefixes

    # Upstreams/downstreams por AFI — dos arquivos de rotas dos IXPs (sequencial)
    for ixp in all_ixps:
        code = ixp["code"]
        for afi in ("v4", "v6"):
            route_file = normalized_path(base, date_str, code) / f"routes-{afi}.json.gz"
            if not route_file.exists():
                continue
            log.debug("aspath index", ixp=code, afi=afi)
            up_key = f"upstreams_{afi}"
            dn_key = f"downstreams_{afi}"
            routes = _load_gz_json(route_file, {}).get("routes", [])
            for route in routes:
                aspath = route.get("aspath", [])
                for i, asn in enumerate(aspath):
                    if i > 0:
                        idx[asn][up_key].add(aspath[i - 1])
                    if i < len(aspath) - 1:
                        idx[asn][dn_key].add(aspath[i + 1])
            del routes  # libera memória antes do próximo arquivo

    # Upstreams/downstreams globais — do grafo de adjacências do RouteViews
    # Enriquece apenas ASNs já presentes no índice (BR + participantes de IXPs).
    log.info("enriching index from global adj graph")
    for afi in ("v4", "v6"):
        adj = _load_aspath_adj(base, date_str, afi)
        if not adj:
            log.warning("global adj graph not available", afi=afi)
            continue
        up_key = f"upstreams_global_{afi}"
        dn_key = f"downstreams_global_{afi}"
        for asn in list(idx.keys()):
            nb = adj.get(str(asn))
            if nb:
                idx[asn][up_key] = set(nb.get("up", []))
                idx[asn][dn_key] = set(nb.get("down", []))
        log.info("global adj enriched", afi=afi, adj_asns=len(adj))
        del adj  # libera memória

    return dict(idx)
