# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Índice de VRPs e estado RPKI de um (prefixo, origem)."""
from __future__ import annotations

from collections import defaultdict
from ipaddress import ip_network


def _build_rpki_index(vrp_list: list[dict]) -> dict:
    """Builds a lookup index {(vrp_len, net_int): [(asn, maxLength)]} from VRP list."""
    idx: dict[tuple, list] = defaultdict(list)
    for vrp in vrp_list:
        try:
            net = ip_network(vrp["prefix"], strict=False)
        except ValueError:
            continue
        idx[(net.prefixlen, int(net.network_address))].append((vrp["asn"], vrp["maxLength"]))
    return dict(idx)


def _rpki_status(prefix: str, asn: int, rpki_index: dict) -> str:
    """Returns 'valid', 'invalid', or 'not_found' for a prefix/ASN pair."""
    try:
        net = ip_network(prefix, strict=False)
    except ValueError:
        return "not_found"
    p_int = int(net.network_address)
    p_len = net.prefixlen
    covering: list[tuple[int, int]] = []
    if net.version == 4:
        masks = [0] + [(0xFFFFFFFF ^ ((1 << (32 - l)) - 1)) for l in range(1, 33)]
        for vrp_len in range(0, p_len + 1):
            p_masked = p_int & masks[vrp_len]
            entries = rpki_index.get((vrp_len, p_masked))
            if entries:
                covering.extend(entries)
    else:
        for vrp_len in range(0, p_len + 1):
            if vrp_len == 0:
                p_masked = 0
            else:
                shift = 128 - vrp_len
                p_masked = (p_int >> shift) << shift
            entries = rpki_index.get((vrp_len, p_masked))
            if entries:
                covering.extend(entries)
    if not covering:
        return "not_found"
    if any(v_asn == asn and p_len <= max_len for v_asn, max_len in covering):
        return "valid"
    return "invalid"
