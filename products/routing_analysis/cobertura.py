# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cobertura do Registro.br, MOAS, prefixos específicos demais e comparação global."""
from __future__ import annotations

from collections import defaultdict
from ipaddress import ip_network

from core import moas as moas_textos
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
    origens_multi: dict[str, dict | None],
    registry_trie_v4: _PrefixTrie,
    registry_trie_v6: _PrefixTrie,
    br_asns: set[int],
    asn_names: dict[int, str] | None = None,
    max_entries: int = 2000,
) -> tuple[list[dict] | None, dict | None]:
    """MOAS a partir de `origins-multi-{afi}` (todas as origens por prefixo e por coletor).

    `origens_multi` = {"v6": documento ou None, "v4": ...}; None quer dizer família sem o artefato (coleta antiga), e sem nenhuma
    das duas devolve (None, None). A contagem global inclui todo prefixo com 2+ origens; a lista, só os brasileiros (rota
    brasileira = prefixo contido em bloco do Registro.br, D4), com cada origem e o número de coletores que a viram. Nada de causa:
    só o que foi observado.
    """
    if all(origens_multi.get(afi) is None for afi in ("v6", "v4")):
        return None, None
    asn_names = asn_names or {}
    lista: list[dict] = []
    prefixos: dict[str, dict | None] = {}
    coletores: dict[str, list[str] | None] = {}
    for afi, trie in (("v6", registry_trie_v6), ("v4", registry_trie_v4)):
        doc = origens_multi.get(afi)
        if doc is None:
            prefixos[afi] = coletores[afi] = None
            continue
        por_prefixo = doc.get("prefixos") or {}
        n_br = 0
        for prefix, origens in por_prefixo.items():
            if len(origens) < 2 or trie.find_covering(prefix) is None:
                continue
            n_br += 1
            detalhe = sorted(({"asn": int(a), "name": asn_names.get(int(a), ""), "coletores": len(cs), "coletores_nomes": list(cs),
                               "asn_br": int(a) in br_asns} for a, cs in origens.items()),
                             key=lambda o: (-o["coletores"], o["asn"]))
            asns = sorted(o["asn"] for o in detalhe)
            lista.append({
                "prefix":       prefix,
                "afi":          afi,
                "origins":      asns,
                "br_origins":   [a for a in asns if a in br_asns],
                "is_prefix_br": True,
                "origens":      detalhe,
            })
        prefixos[afi] = {"global": sum(1 for o in por_prefixo.values() if len(o) >= 2), "br": n_br}
        coletores[afi] = list(doc.get("coletores") or [])

    lista.sort(key=lambda x: (x["afi"] != "v6", -len(x["origins"]), x["prefix"]))      # IPv6 antes de IPv4
    resumo = {
        "prefixos": prefixos,
        "coletores": coletores,
        "lista": "prefixos brasileiros (contidos em bloco alocado pelo Registro.br)",
        "lista_truncada": len(lista) > max_entries,
        "lista_limite": max_entries,
        "definicao": moas_textos.DEFINICAO,
        "como_ler": moas_textos.COMO_LER,
        "limites": moas_textos.LIMITES,
    }
    return lista[:max_entries], resumo


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
