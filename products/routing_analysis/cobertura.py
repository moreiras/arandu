# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cobertura do Registro.br, MOAS, prefixos específicos demais e comparação global."""
from __future__ import annotations

from collections import defaultdict
from ipaddress import ip_network

from products.routing_analysis.rpki import _rpki_status
from products.routing_analysis.util import _PrefixTrie, _safe_prefixlen, _union_span


def _registro_br_coverage(
    pbr_routes_v4: list[dict],
    pbr_routes_v6: list[dict],
    registro_br: dict,
    asn_names: dict[int, str],
    cnpj_by_asn: dict[int, str],
    rpki_index: dict,
) -> list[dict]:
    """Cobertura de cada bloco alocado pelo Registro.br na tabela de roteamento.

    Algoritmo O(n × prefixlen) em vez de O(n × m):
    Uma passagem sobre as rotas P_BR usa find_covering (O(32) para v4) para agrupar
    rotas por bloco Registro.br, eliminando o find_all_inside O(n) por bloco.
    """
    # Trie dos blocos Registro.br — value é a string do próprio bloco
    reg_trie_v4 = _PrefixTrie()
    reg_trie_v6 = _PrefixTrie()
    block_meta: dict[str, dict] = {}  # block_str → {asn, name, cnpj, afi}

    for asn_obj in registro_br.get("asns", []):
        asn  = asn_obj["asn"]
        name = asn_names.get(asn, asn_obj.get("name", ""))
        cnpj = asn_obj.get("cnpj", "")
        for p in asn_obj.get("prefixes_v4", []):
            reg_trie_v4.insert(p, p)
            block_meta[p] = {"asn": asn, "name": name, "cnpj": cnpj, "afi": "v4"}
        for p in asn_obj.get("prefixes_v6", []):
            reg_trie_v6.insert(p, p)
            block_meta[p] = {"asn": asn, "name": name, "cnpj": cnpj, "afi": "v6"}
    reg_trie_v4._build()
    reg_trie_v6._build()

    # Passo único: acumula rotas por bloco usando find_covering O(prefixlen)
    block_routes: dict[str, list[dict]] = defaultdict(list)
    for r in pbr_routes_v4:
        blk = reg_trie_v4.find_covering(r["prefix"])
        if blk:
            block_routes[blk].append(r)
    for r in pbr_routes_v6:
        blk = reg_trie_v6.find_covering(r["prefix"])
        if blk:
            block_routes[blk].append(r)

    results = []
    for block, meta in block_meta.items():
        asn  = meta["asn"]
        name = meta["name"]
        cnpj = meta["cnpj"]
        afi  = meta["afi"]
        inside = block_routes.get(block, [])

        if not inside:
            results.append({
                "block":               block,
                "afi":                 afi,
                "asn":                 asn,
                "name":                name,
                "cnpj":                cnpj,
                "routes_inside":       0,
                "coverage_pct":        0.0,
                "has_exact_aggregate": False,
                "origin_count":        0,
                "origins":             [],
                "origins_detail":      [],
                "category":            "not_announced",
            })
            continue

        try:
            block_net = ip_network(block, strict=False)
        except ValueError:
            continue

        prefixes_inside = [r["prefix"] for r in inside]
        union            = _union_span(prefixes_inside)
        block_span       = block_net.num_addresses
        coverage_pct     = round(union / block_span * 100, 2) if block_span else 0.0
        has_exact        = any(r["prefix"] == block for r in inside)
        origin_set       = sorted({r["origin_as"] for r in inside})

        if coverage_pct == 0:
            category = "not_announced"
        elif coverage_pct < 100:
            category = "partial"
        elif has_exact:
            category = "full_with_agg"
        elif len(origin_set) == 1:
            category = "full_without_agg"
        else:
            category = "multi_origin"

        # Per-origin detail: routes with RPKI status
        routes_by_origin: dict[int, list[str]] = defaultdict(list)
        for r in inside:
            routes_by_origin[r["origin_as"]].append(r["prefix"])

        origins_detail = []
        for o_asn in origin_set:
            o_routes = sorted(routes_by_origin[o_asn])
            o_routes_detail = [
                {"prefix": p, "rpki": _rpki_status(p, o_asn, rpki_index)}
                for p in o_routes
            ]
            origins_detail.append({
                "asn":   o_asn,
                "name":  asn_names.get(o_asn, ""),
                "cnpj":  cnpj_by_asn.get(o_asn, ""),
                "routes": o_routes_detail,
            })

        results.append({
            "block":               block,
            "afi":                 afi,
            "asn":                 asn,
            "name":                name,
            "cnpj":                cnpj,
            "routes_inside":       len(inside),
            "coverage_pct":        coverage_pct,
            "has_exact_aggregate": has_exact,
            "origin_count":        len(origin_set),
            "origins":             origin_set,
            "origins_detail":      origins_detail,
            "category":            category,
        })

    return results


def _moas_analysis(
    origin_prefixes_v4: dict,
    origin_prefixes_v6: dict,
    br_asns: set[int],
    registry_trie_v4: _PrefixTrie,
    registry_trie_v6: _PrefixTrie,
    max_entries: int = 500,
) -> list[dict]:
    """Detecta MOAS (Multiple-Origin AS) — prefixos anunciados por múltiplos ASes."""
    # Inverte o índice: {prefix → set(origin_as)}
    inv_v4: dict[str, set[int]] = defaultdict(set)
    for asn_str, prefixes in origin_prefixes_v4.items():
        for p in prefixes:
            inv_v4[p].add(int(asn_str))

    inv_v6: dict[str, set[int]] = defaultdict(set)
    for asn_str, prefixes in origin_prefixes_v6.items():
        for p in prefixes:
            inv_v6[p].add(int(asn_str))

    results = []
    for afi, inv, trie in [("v4", inv_v4, registry_trie_v4), ("v6", inv_v6, registry_trie_v6)]:
        for prefix, origins in inv.items():
            if len(origins) < 2:
                continue
            br_origins    = sorted(o for o in origins if o in br_asns)
            is_prefix_br  = trie.find_covering(prefix) is not None
            # Filtra apenas MOAS com pelo menos um ASN BR ou prefixo BR
            if not br_origins and not is_prefix_br:
                continue
            results.append({
                "prefix":       prefix,
                "afi":          afi,
                "origins":      sorted(origins),
                "br_origins":   br_origins,
                "is_prefix_br": is_prefix_br,
            })

    results.sort(key=lambda x: (x["afi"], -len(x["origins"]), x["prefix"]))
    return results[:max_entries]


def _too_specific(
    pbr_routes: list[dict],
    afi: str,
    annotated_trie: _PrefixTrie,
    registry_trie: _PrefixTrie,
    asn_names: dict[int, str] | None = None,
    max_len: int = 500,
) -> list[dict]:
    """Prefixos potencialmente filtráveis (>24 v4, >48 v6)."""
    threshold = 24 if afi == "v4" else 48
    asn_names = asn_names or {}
    results = []
    for r in pbr_routes:
        try:
            net = ip_network(r["prefix"], strict=False)
        except ValueError:
            continue
        if net.prefixlen <= threshold:
            continue
        has_covering = annotated_trie.find_less_specific(r["prefix"]) is not None
        is_prefix_br = registry_trie.find_covering(r["prefix"]) is not None
        results.append({
            "prefix":       r["prefix"],
            "origin_as":    r["origin_as"],
            "name":         asn_names.get(r["origin_as"], ""),
            "has_covering": has_covering,
            "is_prefix_br": is_prefix_br,
        })
    results.sort(key=lambda x: x["prefix"])
    return results[:max_len]


def _global_comparison(
    pbr_routes: list[dict],
    all_prefix_set: list[str],
    pbr_more_spec_stats: dict,
    global_stats: dict,
    afi: str,
) -> dict:
    """Comparativo de métricas P_BR vs. global."""
    pbr_total  = len(pbr_routes)
    glob_total = global_stats.get("stats", {}).get("total_routes", 0) or 1

    threshold = 24 if afi == "v4" else 48
    pbr_at   = sum(1 for r in pbr_routes
                   if ip_network(r["prefix"], strict=False).prefixlen == threshold)
    pbr_gt   = sum(1 for r in pbr_routes
                   if ip_network(r["prefix"], strict=False).prefixlen > threshold)

    # Global (approx de prefix-set, sem aspath por rota)
    glob_at  = sum(1 for p in all_prefix_set if _safe_prefixlen(p) == threshold)
    glob_gt  = sum(1 for p in all_prefix_set if _safe_prefixlen(p) > threshold)

    pbr_ms_pct  = round(pbr_more_spec_stats.get("pbr_more_specific", 0) / pbr_total * 100, 1) \
                  if pbr_total else 0.0

    # Global more-specifics aproximado: não temos trie global, simplificamos
    glob_ms_pct = 0.0  # preenchido externamente ou deixado em 0

    return {
        f"pct_{threshold}_global":      round(glob_at / glob_total * 100, 1),
        f"pct_{threshold}_pbr":         round(pbr_at / pbr_total * 100, 1) if pbr_total else 0.0,
        f"pct_gt{threshold}_global":    round(glob_gt / glob_total * 100, 1),
        f"pct_gt{threshold}_pbr":       round(pbr_gt / pbr_total * 100, 1) if pbr_total else 0.0,
        "pct_more_spec_global":         glob_ms_pct,
        "pct_more_spec_pbr":            pbr_ms_pct,
    }
