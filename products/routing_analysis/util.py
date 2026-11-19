# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Utilitários da análise BGP: constantes de comunidades e AS privados, trie de prefixos, espaço de endereços e normalização de AS_PATH."""
from __future__ import annotations

from ipaddress import collapse_addresses, ip_network


_NO_EXPORT    = "65535:65281"


_NO_ADVERTISE = "65535:65282"


# 64512–65534 são privados (RFC 6996); 23456 = AS_TRANS (RFC 6793)
_PRIVATE_AS_RANGES = [range(64512, 65535), range(4200000000, 4294967295)]


_AS_TRANS = 23456


def _is_private_as(asn: int) -> bool:
    return any(asn in r for r in _PRIVATE_AS_RANGES)


def _is_blackhole_candidate(communities: list[str]) -> bool:
    return any(c.endswith(":666") or c.endswith(":9999") for c in communities)


def _is_private_community(c: str) -> bool:
    parts = c.split(":")
    if parts:
        try:
            return _is_private_as(int(parts[0]))
        except ValueError:
            pass
    return False


class _PrefixTrie:
    """Lookup de prefixos IP por hash dict com walk de supernets.

    Complexidade por lookup: O(prefixlen) — máx 32 para v4, 128 para v6 — em vez de O(n_trie).
    Para registros com ~12k entradas e 1M+ lookups, isso é ~400x mais rápido que scan linear.

    Suporta:
      insert(prefix_str, value)      — insere prefixo com valor arbitrário
      find_covering(prefix_str)      — retorna value do prefixo mais específico que cobre o argumento
      find_less_specific(prefix_str) — retorna value do prefixo mais específico MENOS específico
                                       que o argumento (parent imediato)
      find_all_inside(block_str)     — todos os (network, value) contidos no bloco
    """

    __slots__ = ("_index", "_nets")

    def __init__(self) -> None:
        self._index: dict = {}          # ip_network → value (para find_covering/find_less_specific)
        self._nets:  list[tuple] = []   # (net, val) para find_all_inside (scan linear, chamado poucas vezes)

    def insert(self, prefix_str: str, value) -> None:
        try:
            net = ip_network(prefix_str, strict=False)
        except ValueError:
            return
        self._index[net] = value
        self._nets.append((net, value))

    def _build(self) -> None:
        """Ordena _nets por prefixlen decrescente (usado só em find_all_inside)."""
        self._nets.sort(key=lambda x: -x[0].prefixlen)

    def find_covering(self, prefix_str: str):
        """Retorna value do prefixo mais longo (mais específico) que cobre prefix_str.

        Walk de supernets do target até /0: O(prefixlen).
        """
        try:
            target = ip_network(prefix_str, strict=False)
        except ValueError:
            return None
        net = target
        while True:
            val = self._index.get(net)
            if val is not None:
                return val
            if net.prefixlen == 0:
                break
            net = net.supernet()
        return None

    def find_less_specific(self, prefix_str: str):
        """Retorna value do prefixo mais específico MENOS específico que prefix_str.

        Walk de supernets do parent imediato até /0: O(prefixlen).
        """
        try:
            target = ip_network(prefix_str, strict=False)
        except ValueError:
            return None
        if target.prefixlen == 0:
            return None
        net = target.supernet()
        while True:
            val = self._index.get(net)
            if val is not None:
                return val
            if net.prefixlen == 0:
                break
            net = net.supernet()
        return None

    def find_all_inside(self, block_str: str) -> list:
        """Retorna todos os (network, value) cujo prefixo está dentro de block_str."""
        try:
            block = ip_network(block_str, strict=False)
        except ValueError:
            return []
        result = []
        for net, val in self._nets:
            if net.version == block.version and block.supernet_of(net):
                result.append((net, val))
        return result


def _net_span(prefix_str: str) -> int:
    """Número de endereços IP no prefixo."""
    try:
        return ip_network(prefix_str, strict=False).num_addresses
    except ValueError:
        return 0


def _union_span(prefixes: list[str]) -> int:
    """União de endereços (evita contar sobreposições duas vezes)."""
    nets = []
    for p in prefixes:
        try:
            nets.append(ip_network(p, strict=False))
        except ValueError:
            continue
    if not nets:
        return 0
    version = nets[0].version
    nets = [n for n in nets if n.version == version]
    collapsed = list(collapse_addresses(nets))
    return sum(n.num_addresses for n in collapsed)


def normalize_path(path: list[int]) -> list[int]:
    """Remove prepends consecutivos do AS_PATH."""
    result, prev = [], None
    for asn in path:
        if asn != prev:
            result.append(asn)
        prev = asn
    return result


def _safe_prefixlen(prefix: str) -> int:
    try:
        return ip_network(prefix, strict=False).prefixlen
    except ValueError:
        return 0
