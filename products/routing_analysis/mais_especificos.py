# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Prefixos mais específicos que o convencional: classificação PBR, análise, ranking de ASNs e histograma de tamanhos."""
from __future__ import annotations

from collections import defaultdict
from ipaddress import ip_network

from products.routing_analysis.util import _PrefixTrie


def _classify_pbr(
    origin_prefixes_v4: dict,
    origin_prefixes_v6: dict,
    registro_br: dict,
) -> tuple[list[dict], list[dict]]:
    """Classifica as rotas com prefixo em bloco do Registro.br ou origem num ASN da lista do Registro.br.

    Retorna (rotas_v4, rotas_v6) — listas de dicts com campos:
      prefix, afi, origin_as, is_origin_br, is_prefix_br
    As rotas brasileiras (P_BR) são só as `is_prefix_br` (`separar_rota_br`); as de origem BR fora de bloco do Registro.br são
    contadas à parte.
    """
    br_asns = {a["asn"] for a in registro_br.get("asns", [])}

    # Trie de blocos alocados pelo Registro.br
    trie_v4 = _PrefixTrie()
    trie_v6 = _PrefixTrie()
    for asn_obj in registro_br.get("asns", []):
        asn = asn_obj["asn"]
        for p in asn_obj.get("prefixes_v4", []):
            trie_v4.insert(p, asn)
        for p in asn_obj.get("prefixes_v6", []):
            trie_v6.insert(p, asn)
    trie_v4._build()
    trie_v6._build()

    def _classify(origin_prefixes: dict, trie: _PrefixTrie, afi: str) -> list[dict]:
        routes = []
        for asn_str, prefixes in origin_prefixes.items():
            asn = int(asn_str)
            is_origin_br = asn in br_asns
            for prefix in prefixes:
                covering = trie.find_covering(prefix)
                is_prefix_br = covering is not None
                if is_origin_br or is_prefix_br:
                    routes.append({
                        "prefix":       prefix,
                        "afi":          afi,
                        "origin_as":    asn,
                        "is_origin_br": is_origin_br,
                        "is_prefix_br": is_prefix_br,
                    })
        return routes

    return (
        _classify(origin_prefixes_v4, trie_v4, "v4"),
        _classify(origin_prefixes_v6, trie_v6, "v6"),
    )


def separar_rota_br(rotas: list[dict]) -> tuple[list[dict], list[dict]]:
    """(P_BR, ASN BR fora de bloco). Rota brasileira = prefixo contido em bloco alocado pelo Registro.br; a origem não define (D4).
    A rota de ASN da lista do Registro.br em espaço de outro RIR (bloco legado ou transferido, ou rede estrangeira com CNPJ no Brasil,
    como o AS174 fora do `2804:5330::/32`) não é rota brasileira: fica numa contagem à parte, fora do total."""
    pbr = [r for r in rotas if r["is_prefix_br"]]
    fora = [r for r in rotas if not r["is_prefix_br"]]
    return pbr, fora


def _analyze_more_specifics(pbr_routes: list[dict]) -> tuple[dict, list[dict]]:
    """Detecta root prefixes e more specifics dentro de P_BR.

    Retorna (stats_dict, routes_com_campos_adicionais).
    """
    trie = _PrefixTrie()
    for r in pbr_routes:
        trie.insert(r["prefix"], r)
    trie._build()

    # Profundidade: 0 na raiz, 1 num sub-bloco da raiz, 2 num sub-bloco de um mais específico... Calculada do menos para o mais
    # específico, pela profundidade já conhecida do pai imediato (o valor guardado na trie é a rota original, sem `depth`).
    def _rede(p: str):
        try:
            return ip_network(p, strict=False)
        except ValueError:
            return None

    profundidade: dict = {}
    pais: dict[int, dict | None] = {}
    for i in sorted(range(len(pbr_routes)), key=lambda i: getattr(_rede(pbr_routes[i]["prefix"]), "prefixlen", 0)):
        r = pbr_routes[i]
        parent = trie.find_less_specific(r["prefix"])
        pais[i] = parent
        rede = _rede(r["prefix"])
        if rede is not None and rede not in profundidade:
            profundidade[rede] = 0 if parent is None else profundidade.get(_rede(parent["prefix"]), 0) + 1

    annotated = []
    for i, r in enumerate(pbr_routes):
        parent = pais[i]
        r2 = dict(r)
        r2["is_root"]      = parent is None
        r2["is_more_spec"] = parent is not None
        r2["same_origin"]  = (parent is not None and
                               r["origin_as"] == parent["origin_as"])
        r2["depth"]        = profundidade.get(_rede(r["prefix"]), 0)
        annotated.append(r2)

    n_root      = sum(1 for r in annotated if r["is_root"])
    n_more_spec = sum(1 for r in annotated if r["is_more_spec"])
    same_origin = sum(1 for r in annotated if r["same_origin"])
    diff_origin = sum(1 for r in annotated if r["is_more_spec"] and not r["same_origin"])
    depths      = [r["depth"] for r in annotated]
    max_depth   = max(depths) if depths else 0
    avg_depth   = round(sum(depths) / len(depths), 2) if depths else 0.0

    stats = {
        "pbr_root":         n_root,
        "pbr_more_specific": n_more_spec,
        "same_origin":      same_origin,
        "diff_origin":      diff_origin,
        "max_depth":        max_depth,
        "avg_depth":        avg_depth,
    }
    return stats, annotated


def _top_asns_more_specifics(
    annotated_v4: list[dict],
    annotated_v6: list[dict],
    asn_names: dict[int, str],
    top_n: int = 30,
) -> list[dict]:
    v4_by_asn: dict[int, dict] = defaultdict(lambda: {"routes": 0, "root": 0, "more_spec": 0})
    for r in annotated_v4:
        e = v4_by_asn[r["origin_as"]]
        e["routes"] += 1
        if r["is_root"]:
            e["root"] += 1
        if r["is_more_spec"]:
            e["more_spec"] += 1

    v6_by_asn: dict[int, dict] = defaultdict(lambda: {"routes": 0, "root": 0, "more_spec": 0})
    for r in annotated_v6:
        e = v6_by_asn[r["origin_as"]]
        e["routes"] += 1
        if r["is_root"]:
            e["root"] += 1
        if r["is_more_spec"]:
            e["more_spec"] += 1

    all_asns = set(v4_by_asn.keys()) | set(v6_by_asn.keys())
    results = []
    for asn in all_asns:
        v4 = v4_by_asn.get(asn, {"routes": 0, "root": 0, "more_spec": 0})
        v6 = v6_by_asn.get(asn, {"routes": 0, "root": 0, "more_spec": 0})
        results.append({
            "asn":          asn,
            "name":         asn_names.get(asn, ""),
            "v4_routes":    v4["routes"],
            "v4_root":      v4["root"],
            "v4_more_spec": v4["more_spec"],
            "v6_routes":    v6["routes"],
            "v6_root":      v6["root"],
            "v6_more_spec": v6["more_spec"],
        })

    results.sort(key=lambda x: -(x["v4_more_spec"] + x["v6_more_spec"]))
    return results[:top_n]


def _prefix_length_hist(routes: list[dict], afi: str) -> list[dict]:
    counts: dict[int, int] = defaultdict(int)
    spans:  dict[int, int] = defaultdict(int)
    total = len(routes)
    for r in routes:
        try:
            net = ip_network(r["prefix"], strict=False)
            pl = net.prefixlen
            counts[pl] += 1
            spans[pl]  += net.num_addresses
        except ValueError:
            continue
    total_span = sum(spans.values()) or 1
    result = []
    for pl in sorted(counts.keys()):
        result.append({
            "length":     pl,
            "count":      counts[pl],
            "span":       spans[pl],
            "pct_routes": round(counts[pl] / total * 100, 2) if total else 0.0,
            "pct_span":   round(spans[pl] / total_span * 100, 2),
        })
    return result
