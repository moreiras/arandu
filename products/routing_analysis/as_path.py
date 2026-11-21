# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estatísticas de AS_PATH das rotas BR: prepend, diversidade de upstreams, higiene e comunidades."""
from __future__ import annotations

from collections import defaultdict
from ipaddress import ip_network

from products.routing_analysis.util import _AS_TRANS, _NO_ADVERTISE, _NO_EXPORT, _is_blackhole_candidate, _is_private_as, _is_private_community, normalize_path


def _as_path_stats(br_routes: list[dict], afi: str) -> dict:
    """Estatísticas de AS_PATH a partir de br-routes-{afi}.json.gz."""
    if not br_routes:
        return {}

    raw_lens:  list[int] = []
    norm_lens: list[int] = []
    addr_weighted_total = 0
    addr_total = 0
    routes_with_prepend = 0
    private_as_path_count = 0
    private_as_origin_count = 0
    as_loop_count = 0
    as_trans_count = 0

    for r in br_routes:
        asp = r.get("a", [])
        if not asp:
            continue
        raw_len  = len(asp)
        norm     = normalize_path(asp)
        norm_len = len(norm)
        raw_lens.append(raw_len)
        norm_lens.append(norm_len)

        try:
            span = ip_network(r["p"], strict=False).num_addresses
        except ValueError:
            span = 0
        if span:
            addr_weighted_total += norm_len * span
            addr_total += span

        if raw_len > norm_len:
            routes_with_prepend += 1

        if any(_is_private_as(a) for a in asp[:-1]):
            private_as_path_count += 1
        if asp and _is_private_as(asp[-1]):
            private_as_origin_count += 1

        # AS loop: mesmo ASN não consecutivo
        seen_asns: set[int] = set()
        has_loop = False
        for a in norm:
            if a in seen_asns:
                has_loop = True
                break
            seen_asns.add(a)
        if has_loop:
            as_loop_count += 1

        if _AS_TRANS in asp:
            as_trans_count += 1

    n = len(raw_lens)
    sorted_norm = sorted(norm_lens)

    def _percentile(data: list[int], p: float) -> int:
        if not data:
            return 0
        idx = int(len(data) * p / 100)
        return data[min(idx, len(data) - 1)]

    return {
        "unique_paths_raw":     n,
        "unique_paths_norm":    n,
        "avg_len_raw":          round(sum(raw_lens) / n, 2) if n else 0.0,
        "avg_len_norm":         round(sum(norm_lens) / n, 2) if n else 0.0,
        "median_norm":          _percentile(sorted_norm, 50),
        "p95_norm":             _percentile(sorted_norm, 95),
        "addr_weighted_len":    round(addr_weighted_total / addr_total, 2) if addr_total else 0.0,
        "routes_with_prepend":  routes_with_prepend,
        "prepend_pct":          round(routes_with_prepend / n * 100, 1) if n else 0.0,
        "private_as_in_path":   private_as_path_count,
        "private_as_as_origin": private_as_origin_count,
        "as_loops":             as_loop_count,
        "as_trans_present":     as_trans_count,
    }


def _topo_de_cada_ordem(linhas: list[dict], chaves: tuple[str, ...], n: int, principal: str) -> list[dict]:
    """A união dos `n` primeiros e dos `n` últimos de cada coluna ordenável da tabela (AsPathSection.tsx), na ordem de `principal`.
    A página ordena o que recebe e mostra os `n` primeiros: com só o topo de UMA coluna, ordenar por outra reordenava esse corte e
    escondia quem lidera a outra coluna (o padrão da tabela de prepending, excesso médio, já caía nesse caso)."""
    vistos: dict[int, dict] = {}
    for chave in chaves:
        ordenadas = sorted(linhas, key=lambda x: (x[chave], -x["asn"]))
        for r in ordenadas[:n] + ordenadas[-n:]:
            vistos.setdefault(r["asn"], r)
    return sorted(vistos.values(), key=lambda x: (-x[principal], x["asn"]))


def _top_prependers(br_routes: list[dict], asn_names: dict[int, str], afi: str, top_n: int = 20) -> list[dict]:
    by_asn: dict[int, dict] = defaultdict(lambda: {"routes": 0, "prepend": 0, "excess": []})
    for r in br_routes:
        asp = r.get("a", [])
        if not asp:
            continue
        origin = asp[-1]
        norm   = normalize_path(asp)
        excess = len(asp) - len(norm)
        e = by_asn[origin]
        e["routes"] += 1
        if excess > 0:
            e["prepend"] += 1
            e["excess"].append(excess)

    results = []
    for asn, d in by_asn.items():
        if d["prepend"] == 0:
            continue
        avg_excess = round(sum(d["excess"]) / len(d["excess"]), 1) if d["excess"] else 0.0
        results.append({
            "asn":                asn,
            "name":               asn_names.get(asn, ""),
            "afi":                afi,
            "routes":             d["routes"],
            "routes_with_prepend": d["prepend"],
            "prepend_pct":        round(d["prepend"] / d["routes"] * 100, 1) if d["routes"] else 0.0,
            "avg_excess":         avg_excess,
            "max_excess":         max(d["excess"]) if d["excess"] else 0,
        })

    return _topo_de_cada_ordem(results, ("routes", "routes_with_prepend", "prepend_pct", "avg_excess"), top_n, "routes_with_prepend")


def _upstream_diversity(br_routes: list[dict], asn_names: dict[int, str], afi: str, top_n: int = 50) -> list[dict]:
    by_asn: dict[int, dict] = defaultdict(lambda: {"routes": 0, "upstreams": defaultdict(int)})
    for r in br_routes:
        asp  = r.get("a", [])
        norm = normalize_path(asp)
        if len(norm) < 2:
            continue
        origin   = norm[-1]
        upstream = norm[-2]
        e = by_asn[origin]
        e["routes"] += 1
        e["upstreams"][upstream] += 1

    results = []
    for asn, d in by_asn.items():
        ups = d["upstreams"]
        if not ups:
            continue
        main_up  = max(ups, key=ups.__getitem__)
        main_pct = round(ups[main_up] / d["routes"] * 100, 1) if d["routes"] else 0.0
        results.append({
            "asn":              asn,
            "name":             asn_names.get(asn, ""),
            "afi":              afi,
            "routes":           d["routes"],
            "upstream_count":   len(ups),
            "main_upstream":    main_up,
            "main_upstream_pct": main_pct,
        })

    return _topo_de_cada_ordem(results, ("routes", "upstream_count", "main_upstream_pct"), top_n, "upstream_count")


def _hygiene_issues(br_routes: list[dict], afi: str, max_entries: int = 200) -> list[dict]:
    issues = []
    for r in br_routes:
        asp = r.get("a", [])
        if not asp:
            continue
        origin = asp[-1]
        norm   = normalize_path(asp)

        if _is_private_as(origin):
            issues.append({"prefix": r["p"], "afi": afi, "origin_as": origin,
                            "issue": "private_as_origin", "as_path": asp})
        elif any(_is_private_as(a) for a in norm[:-1]):
            issues.append({"prefix": r["p"], "afi": afi, "origin_as": origin,
                            "issue": "private_as_path", "as_path": asp})

        seen: set[int] = set()
        loop = False
        for a in norm:
            if a in seen:
                loop = True
                break
            seen.add(a)
        if loop:
            issues.append({"prefix": r["p"], "afi": afi, "origin_as": origin,
                            "issue": "as_loop", "as_path": asp})

        if _AS_TRANS in asp:
            issues.append({"prefix": r["p"], "afi": afi, "origin_as": origin,
                            "issue": "as_trans", "as_path": asp})

    return issues[:max_entries]


def _community_stats(br_routes: list[dict], afi: str) -> dict:
    n = len(br_routes)
    if not n:
        return {}

    with_comms       = 0
    with_large       = 0
    no_export        = 0
    no_advertise     = 0
    blackhole        = 0
    private_leak     = 0
    comm_freq: dict[str, dict] = defaultdict(lambda: {"count": 0, "asns": set()})

    for r in br_routes:
        comms = r.get("c", [])
        large = r.get("lc", [])
        origin = r.get("a", [None])[-1]

        if comms:
            with_comms += 1
        if large:
            with_large += 1

        for c in comms:
            if c == _NO_EXPORT:
                no_export += 1
            if c == _NO_ADVERTISE:
                no_advertise += 1
            if _is_blackhole_candidate(comms):
                blackhole += 1
            if _is_private_community(c):
                private_leak += 1
            e = comm_freq[c]
            e["count"] += 1
            if origin:
                e["asns"].add(origin)

    top_comms = sorted(
        [{"community": c, "count": d["count"], "asns": sorted(d["asns"])[:50]}
         for c, d in comm_freq.items()],
        key=lambda x: -x["count"],
    )[:20]

    return {
        "routes_with_communities":       with_comms,
        "community_pct":                 round(with_comms / n * 100, 1) if n else 0.0,
        "routes_with_large_communities": with_large,
        "no_export_count":               no_export,
        "no_advertise_count":            no_advertise,
        "blackhole_candidates":          blackhole,
        "private_community_leak_count":  private_leak,
        "top_communities":               top_comms,
    }
