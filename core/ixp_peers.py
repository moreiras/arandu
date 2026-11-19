# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estatísticas por peer direto de um PTT.

Para cada primeiro ASN do AS_PATH das rotas de um PTT: prefixos próprios (originados por ele) e de terceiros, ASNs originadores
distintos e o espaço em /24 (IPv4) ou /48 (IPv6). O `bgp_ixp` grava o resultado ao lado das rotas (`peers-{afi}.json.gz`); a API lê esse
arquivo em vez de reler as rotas do PTT inteiro (segundos por PTT e AFI) para extrair a linha de um AS. Sem o arquivo, a API
recalcula com esta mesma função, então os dois caminhos dão o mesmo número.
"""
from __future__ import annotations

from ipaddress import ip_network


def espaco(prefixos, afi: str) -> int:
    """Espaço em /24 (v4) ou /48 (v6) coberto pelos prefixos; prefixo mais específico que isso não conta."""
    versao, limite = (6, 48) if afi == "v6" else (4, 24)
    total = 0
    for p in prefixos:
        try:
            net = ip_network(p, strict=False)
        except ValueError:
            continue
        if net.version == versao and net.prefixlen <= limite:
            total += 1 << (limite - net.prefixlen)
    return total


def estatisticas_por_peer(routes: list[dict], afi: str) -> dict[str, dict]:
    """`{str(asn_do_peer): {total_prefixes, own_prefixes, third_prefixes, origin_asns, own_space_24, third_space_24}}`."""
    peers: dict[int, dict] = {}
    for route in routes:
        aspath = route.get("aspath", [])
        prefix = route.get("prefix", "")
        if not aspath or not prefix:
            continue
        first, last = aspath[0], aspath[-1]
        d = peers.setdefault(first, {"own": set(), "third": set(), "origins": set()})
        d["own" if first == last else "third"].add(prefix)
        d["origins"].add(last)
    return {
        str(asn): {
            "total_prefixes": len(d["own"]) + len(d["third"]),
            "own_prefixes": len(d["own"]),
            "third_prefixes": len(d["third"]),
            "origin_asns": len(d["origins"]),
            "own_space_24": espaco(d["own"], afi),
            "third_space_24": espaco(d["third"], afi),
        }
        for asn, d in peers.items()
    }
