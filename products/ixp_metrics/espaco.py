# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Espaço de endereços e cobertura por IXP e agregado."""
from __future__ import annotations

import bisect
from ipaddress import collapse_addresses, ip_network
from pathlib import Path

from products.ixp_metrics.entradas import _load_prefix_set, _load_rels


def _parse_nets(prefixes, version: int) -> list:
    """Converte strings de prefixo em objetos ip_network de uma versão IP."""
    nets = []
    for p in prefixes:
        try:
            n = ip_network(p, strict=False)
            if n.version == version:
                nets.append(n)
        except ValueError:
            continue
    return nets


def _total_space(nets) -> int:
    """Total de endereços cobertos por um conjunto de redes (colapsa sobreposições)."""
    if not nets:
        return 0
    return sum(n.num_addresses for n in collapse_addresses(nets))


def _covered_space(
    registro_nets: list,
    ixp_nets_sorted: list,
    ixp_str_set: set[str],
) -> int:
    """
    Espaço de endereços de registro_nets coberto pelo IXP.

    Um prefixo `registro_br` é coberto se o IXP possui:
      - o prefixo exato ou um supernet dele (cobertura total), ou
      - um ou mais subnets dentro dele (cobertura parcial).
    """
    covered = []
    ixp_addrs = [n.network_address for n in ixp_nets_sorted]

    for rede_reg in registro_nets:
        # Verifica se o IXP tem o prefixo ou algum de seus supernets
        check = rede_reg
        fully = False
        while True:
            if check.with_prefixlen in ixp_str_set:
                covered.append(rede_reg)
                fully = True
                break
            if check.prefixlen == 0:
                break
            check = check.supernet()

        if not fully:
            # Coleta subnets do IXP dentro deste prefixo `registro_br`
            lo = bisect.bisect_left(ixp_addrs, rede_reg.network_address)
            for i in range(lo, len(ixp_nets_sorted)):
                n = ixp_nets_sorted[i]
                if n.network_address > rede_reg.broadcast_address:
                    break
                if n.subnet_of(rede_reg):
                    covered.append(n)

    if not covered:
        return 0
    return sum(n.num_addresses for n in collapse_addresses(covered))


def _pct(num: int, den: int) -> float:
    """Percentual com 2 casas decimais (contagem); retorna 0.0 se denominador zero."""
    return round(num / den * 100, 2) if den > 0 else 0.0


def _pct_space(covered: int, total: int) -> float:
    """Percentual com 4 casas decimais para métricas de espaço de endereços."""
    return round(covered / total * 100, 4) if total > 0 else 0.0


def _compute_ixp_afi(
    ixp_code: str,
    date_str: str,
    base: Path,
    afi: str,
    ip_version: int,
    nicbr_asns: set[int],
    nicbr_nets: list,
    nicbr_space: int,
    br_asns_in_ft: set[int],
    ft_space: int,
) -> dict:
    """Calcula todas as métricas de um IXP para um AFI específico.

    Args:
        ixp_code:      Código do IXP (ex: "sp")
        date_str:      Data do snapshot (YYYY-MM-DD)
        base:          Diretório raiz dos dados
        afi:           "v4" ou "v6"
        ip_version:    4 ou 6 (para _parse_nets)
        nicbr_asns:    Conjunto de ASNs BR (LACNIC delegated ou nicbr_map keys)
        nicbr_nets:    Redes `registro_br` pré-convertidas em ip_network (calculadas em run_p2)
        nicbr_space:   Espaço total `registro_br` em endereços (denominador da cobertura `registro_br`)
        br_asns_in_ft: ASNs BR que originam prefixos na full table (denominador br_asns_pct)
        ft_space:      Espaço total da full table em endereços (denominador ixp_vs_ft)

    Returns:
        Dict com as seguintes chaves:
          total_routes, unique_prefixes, ixp_space — stats básicas do IXP
          asn_direct_count, asn_origin_count, asn_stub_count — contadores de ASNs
          asn_direct, asn_stub — listas de ASNs
          br_asns_direct, br_asns_direct_count, br_asns_direct_pct — ASNs BR como peer direto
          br_asns_origin, br_asns_origin_count, br_asns_origin_pct — ASNs BR como originadores
          br_prefix_covered_space, br_prefix_declared_space, br_prefix_coverage_pct — cobertura `registro_br`
          ft_space, ixp_vs_fulltable_space_pct — comparação com full table
        Ou {"status": "missing"} se o arquivo normalizado não existir.
    """
    rels = _load_rels(base, date_str, ixp_code, afi)
    if not rels:
        return {"status": "missing"}

    stats = rels.get("stats", {})
    rd = rels.get("relationships", {})
    ixp_prefix_set = _load_prefix_set(base, date_str, ixp_code, afi)

    asn_direct = set(rd.get("asn_direct", []))
    asn_origin = set(rd.get("asn_origin", []))
    asn_stub = set(rd.get("asn_stub", []))

    br_direct = sorted(asn_direct & nicbr_asns)
    br_origin = sorted(asn_origin & nicbr_asns)
    br_active_count = len(br_asns_in_ft)

    # Constrói estruturas do IXP para cálculo de cobertura por espaço de endereços
    ixp_nets_sorted = sorted(
        _parse_nets(ixp_prefix_set, ip_version),
        key=lambda n: n.network_address,
    )
    ixp_str_set = {n.with_prefixlen for n in ixp_nets_sorted}
    ixp_space = _total_space(ixp_nets_sorted)

    covered = _covered_space(nicbr_nets, ixp_nets_sorted, ixp_str_set)

    return {
        "total_routes": stats.get("total_routes", 0),
        "unique_prefixes": stats.get("unique_prefixes", 0),
        "ixp_space": ixp_space,
        "asn_direct_count": len(asn_direct),
        "asn_origin_count": len(asn_origin),
        "asn_stub_count": len(asn_stub),
        "asn_direct": sorted(asn_direct),
        "asn_stub": sorted(asn_stub),
        # só para a união IPv6 ∪ IPv4 do PTT (quem chama retira antes de gravar: a lista é grande e não vai ao documento)
        "_asn_origin": asn_origin,
        # Métricas de presença de ASNs brasileiros
        "br_asns_direct": br_direct,
        "br_asns_direct_count": len(br_direct),
        "br_asns_direct_pct": _pct(len(br_direct), br_active_count),
        "br_asns_origin": br_origin,
        "br_asns_origin_count": len(br_origin),
        "br_asns_origin_pct": _pct(len(br_origin), br_active_count),
        # Cobertura de espaço de endereços `registro_br` no IXP
        "br_prefix_covered_space": covered,
        "br_prefix_declared_space": nicbr_space,
        "br_prefix_coverage_pct": _pct_space(covered, nicbr_space),
        # Comparação com a full table global (por espaço de endereços)
        "ft_space": ft_space,
        "ixp_vs_fulltable_space_pct": _pct_space(ixp_space, ft_space),
    }


def _compute_aggregate_afi(
    date_str: str,
    base: Path,
    all_ixps: list[dict],
    afi: str,
    ip_version: int,
    nicbr_asns: set[int],
    nicbr_nets: list,
    nicbr_space: int,
    br_asns_in_ft: set[int],
    ft_space: int,
) -> dict:
    """Agrega todos os IXPs como um único IXP virtual, com union real dos conjuntos."""
    agg_direct: set[int] = set()
    agg_origin: set[int] = set()
    agg_prefix_set: set[str] = set()
    total_routes = 0

    for ixp in all_ixps:
        rels = _load_rels(base, date_str, ixp["code"], afi)
        if not rels:
            continue
        rd = rels.get("relationships", {})
        agg_direct |= set(rd.get("asn_direct", []))
        agg_origin |= set(rd.get("asn_origin", []))
        total_routes += rels.get("stats", {}).get("total_routes", 0)
        agg_prefix_set |= _load_prefix_set(base, date_str, ixp["code"], afi)

    if not agg_prefix_set and not agg_direct:
        return {"status": "missing"}

    br_direct = sorted(agg_direct & nicbr_asns)
    br_origin = sorted(agg_origin & nicbr_asns)
    br_active_count = len(br_asns_in_ft)

    ixp_nets_sorted = sorted(
        _parse_nets(agg_prefix_set, ip_version),
        key=lambda n: n.network_address,
    )
    ixp_str_set = {n.with_prefixlen for n in ixp_nets_sorted}
    ixp_space = _total_space(ixp_nets_sorted)
    covered = _covered_space(nicbr_nets, ixp_nets_sorted, ixp_str_set)

    return {
        "total_routes": total_routes,
        "unique_prefixes": len(agg_prefix_set),
        "ixp_space": ixp_space,
        "asn_direct_count": len(agg_direct),
        "asn_origin_count": len(agg_origin),
        "asn_stub_count": 0,
        "asn_direct": sorted(agg_direct),
        "asn_stub": [],
        "br_asns_direct": br_direct,
        "br_asns_direct_count": len(br_direct),
        "br_asns_direct_pct": _pct(len(br_direct), br_active_count),
        "br_asns_origin": br_origin,
        "br_asns_origin_count": len(br_origin),
        "br_asns_origin_pct": _pct(len(br_origin), br_active_count),
        "br_prefix_covered_space": covered,
        "br_prefix_declared_space": nicbr_space,
        "br_prefix_coverage_pct": _pct_space(covered, nicbr_space),
        "ft_space": ft_space,
        "ixp_vs_fulltable_space_pct": _pct_space(ixp_space, ft_space),
    }
