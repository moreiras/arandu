# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Potencial de agregação de prefixos por origem e tabela de agregação."""
from __future__ import annotations

from collections import defaultdict
from ipaddress import collapse_addresses, ip_network


def _aggregation_savings_by_origin(routes: list[dict]) -> list[dict]:
    """Calcula potencial de agregação por ASN (agrupando por origin_as)."""
    groups: dict[int, list] = defaultdict(list)
    for r in routes:
        groups[r["origin_as"]].append(ip_network(r["prefix"], strict=False))

    results = []
    for asn, nets in groups.items():
        current   = len(nets)
        collapsed = len(list(collapse_addresses(nets)))
        results.append({
            "asn":            asn,
            "current":        current,
            "by_origin":      collapsed,
            "savings_origin": current - collapsed,
        })
    return sorted(results, key=lambda x: -x["savings_origin"])


def _aggregation_table(
    pbr_routes_v4: list[dict],
    pbr_routes_v6: list[dict],
    asn_names: dict[int, str],
) -> list[dict]:
    """Tabela de potencial de agregação por ASN (Fase 1: apenas por origin)."""
    results = []
    for afi, routes in [("v4", pbr_routes_v4), ("v6", pbr_routes_v6)]:
        savings = _aggregation_savings_by_origin(routes)
        for s in savings:
            if s["savings_origin"] == 0:
                continue
            results.append({
                "asn":             s["asn"],
                "name":            asn_names.get(s["asn"], ""),
                "afi":             afi,
                "current":         s["current"],
                "by_origin":       s["by_origin"],
                "savings_origin":  s["savings_origin"],
                "by_path":         s["by_origin"],    # Fase 1: igual a by_origin (sem path)
                "savings_path":    s["savings_origin"],
                "savings_path_pct": round(s["savings_origin"] / s["current"] * 100, 1)
                                    if s["current"] else 0.0,
            })
    results.sort(key=lambda x: -x["savings_origin"])
    return results
