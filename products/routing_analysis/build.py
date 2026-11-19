# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Análise da tabela BGP global com foco em ASNs e prefixos brasileiros (P_BR).

Inputs (normalized/{date}/summary/):
  origin-prefixes-{afi}.json.gz  — {str(asn): [prefixos]}
  registro_br.json.gz            — {asns: [{asn, name, cnpj, prefixes_v4, prefixes_v6}]}
  prefix-set-{afi}.json.gz       — [prefixo, ...]
  routes-{afi}.json.gz           — stats globais
  br-routes-{afi}.json.gz        — rotas BR com AS_PATH e communities (opcional, Fase 2)

Output:
  published/{date}/routing_analysis.json
  published/{date}/routing_analysis_resumo.json  — totais nacionais e estado RPKI das rotas BR (resumo.py)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional
from core.common import configure_logging, data_dir, normalized_path, now_iso, published_path, read_json_gz, today_str

from products.routing_analysis.agregacao import _aggregation_savings_by_origin, _aggregation_table  # noqa: F401
from products.routing_analysis.as_path import _as_path_stats, _community_stats, _hygiene_issues, _top_prependers, _upstream_diversity  # noqa: F401
from products.routing_analysis.cobertura import _global_comparison, _moas_analysis, _registro_br_coverage, _too_specific  # noqa: F401
from products.routing_analysis.mais_especificos import _analyze_more_specifics, _classify_pbr, _prefix_length_hist, _top_asns_more_specifics  # noqa: F401
from products.routing_analysis.rpki import _build_rpki_index, _rpki_status  # noqa: F401
from products.routing_analysis import resumo as resumo_rotas
from products.routing_analysis.util import _AS_TRANS, _NO_ADVERTISE, _NO_EXPORT, _PRIVATE_AS_RANGES, _PrefixTrie, _is_blackhole_candidate, _is_private_as, _is_private_community, _net_span, _safe_prefixlen, _union_span, normalize_path  # noqa: F401


def run(date_str: str, base: Path, log) -> bool:
    norm = normalized_path(base, date_str, "summary")
    pub  = published_path(base, date_str)

    # ---- Carregamento de inputs ----
    log.info("loading inputs", date=date_str)

    registro_br = _safe_load(norm / "registro_br.json.gz", log, "registro_br")
    if not registro_br:
        log.error("registro_br.json.gz não encontrado — abortando")
        return False

    op_v4 = _safe_load(norm / "origin-prefixes-v4.json.gz", log, "origin-prefixes-v4") or {}
    op_v6 = _safe_load(norm / "origin-prefixes-v6.json.gz", log, "origin-prefixes-v6") or {}
    ps_v4 = _safe_load(norm / "prefix-set-v4.json.gz",      log, "prefix-set-v4")  or []
    ps_v6 = _safe_load(norm / "prefix-set-v6.json.gz",      log, "prefix-set-v6")  or []
    rt_v4 = _safe_load(norm / "routes-v4.json.gz",          log, "routes-v4")       or {}
    rt_v6 = _safe_load(norm / "routes-v6.json.gz",          log, "routes-v6")       or {}

    br_routes_v4 = _safe_load(norm / "br-routes-v4.json.gz", log, "br-routes-v4")
    br_routes_v6 = _safe_load(norm / "br-routes-v6.json.gz", log, "br-routes-v6")
    has_path_data = br_routes_v4 is not None or br_routes_v6 is not None
    br_routes_v4 = br_routes_v4 or []
    br_routes_v6 = br_routes_v6 or []

    # Índice de nomes de ASN (published/{date}/asns/index.json se disponível)
    asn_names = _load_asn_names(pub, log)

    br_asns = {a["asn"] for a in registro_br.get("asns", [])}

    log.info("inputs loaded",
             origin_asns_v4=len(op_v4), origin_asns_v6=len(op_v6),
             prefixes_v4=len(ps_v4), prefixes_v6=len(ps_v6),
             has_path_data=has_path_data)

    # ---- Classificação P_BR ----
    log.info("classifying pbr routes")
    pbr_v4, pbr_v6 = _classify_pbr(op_v4, op_v6, registro_br)
    log.info("pbr classified", pbr_v4=len(pbr_v4), pbr_v6=len(pbr_v6))

    # ---- Sumário ----
    def _summary(pbr: list[dict], prefix_set: list, routes_stats: dict, afi: str) -> dict:
        origin_asns = {r["origin_as"] for r in pbr}
        br_origin   = {r["origin_as"] for r in pbr if r["is_origin_br"]}
        total_global = routes_stats.get("stats", {}).get("total_routes", len(prefix_set))
        pbr_count = len(pbr)
        return {
            "total_routes_global": total_global,
            "total_prefixes_global": len(prefix_set),
            "total_asns_global": routes_stats.get("stats", {}).get("asn_origin_count", 0),
            "pbr_routes": pbr_count,
            "pbr_pct": round(pbr_count / total_global * 100, 2) if total_global else 0.0,
            "br_origin_asns": len(br_origin),
            "pbr_asns": len(origin_asns),
        }

    summary = {
        "v4": _summary(pbr_v4, ps_v4, rt_v4, "v4"),
        "v6": _summary(pbr_v6, ps_v6, rt_v6, "v6"),
    }

    # ASNs BR visíveis (união IPv4+IPv6, sem dupla contagem) vs. total registrado
    br_origin_v4 = {r["origin_as"] for r in pbr_v4 if r["is_origin_br"]}
    br_origin_v6 = {r["origin_as"] for r in pbr_v6 if r["is_origin_br"]}
    br_asns_visible    = len(br_origin_v4 | br_origin_v6)
    br_asns_registered = len(br_asns)

    # ---- Composição P_BR ----
    def _composition(pbr: list[dict]) -> dict:
        strict      = [r for r in pbr if r["is_origin_br"] and r["is_prefix_br"]]
        origin_only = [r for r in pbr if r["is_origin_br"] and not r["is_prefix_br"]]
        prefix_only = [r for r in pbr if not r["is_origin_br"] and r["is_prefix_br"]]
        return {
            "strict_br":      {"routes": len(strict),      "asns": len({r["origin_as"] for r in strict})},
            "origin_only_br": {"routes": len(origin_only), "asns": len({r["origin_as"] for r in origin_only})},
            "prefix_only_br": {"routes": len(prefix_only), "asns": len({r["origin_as"] for r in prefix_only})},
        }

    pbr_composition = {
        "v4": _composition(pbr_v4),
        "v6": _composition(pbr_v6),
    }

    # ---- Histograma prefix length ----
    log.info("computing prefix length histograms")
    pl_dist = {
        "v4": _prefix_length_hist(pbr_v4, "v4"),
        "v6": _prefix_length_hist(pbr_v6, "v6"),
    }

    # ---- More specifics ----
    log.info("computing more specifics")
    ms_stats_v4, ann_v4 = _analyze_more_specifics(pbr_v4)
    ms_stats_v6, ann_v6 = _analyze_more_specifics(pbr_v6)

    # Complementa com stats globais aproximadas (não temos trie global)
    ms_stats_v4.update({
        "global_root":          rt_v4.get("stats", {}).get("total_routes", 0),
        "global_more_specific": 0,
    })
    ms_stats_v6.update({
        "global_root":          rt_v6.get("stats", {}).get("total_routes", 0),
        "global_more_specific": 0,
    })
    more_specifics = {"v4": ms_stats_v4, "v6": ms_stats_v6}

    # ---- Top ASNs more specifics ----
    top_ms = _top_asns_more_specifics(ann_v4, ann_v6, asn_names)

    # ---- Potencial de agregação ----
    log.info("computing aggregation potential")
    agg_table = _aggregation_table(pbr_v4, pbr_v6, asn_names)

    # ---- Cobertura Registro.br ----
    log.info("computing registro_br coverage")
    cnpj_by_asn = {a["asn"]: a.get("cnpj", "") for a in registro_br.get("asns", [])}
    vrp_list = _safe_load(pub / "rpki" / "vrp_list.json.gz", log, "vrp_list") or []
    rpki_index = _build_rpki_index(vrp_list)
    reg_coverage = _registro_br_coverage(pbr_v4, pbr_v6, registro_br, asn_names, cnpj_by_asn, rpki_index)

    # ---- MOAS ----
    log.info("computing moas")
    reg_trie_v4 = _PrefixTrie()
    reg_trie_v6 = _PrefixTrie()
    for asn_obj in registro_br.get("asns", []):
        for p in asn_obj.get("prefixes_v4", []):
            reg_trie_v4.insert(p, asn_obj["asn"])
        for p in asn_obj.get("prefixes_v6", []):
            reg_trie_v6.insert(p, asn_obj["asn"])
    reg_trie_v4._build()
    reg_trie_v6._build()

    moas = _moas_analysis(op_v4, op_v6, br_asns, reg_trie_v4, reg_trie_v6)

    # ---- Too specific ----
    log.info("computing too-specific prefixes")
    ann_trie_v4 = _PrefixTrie()
    ann_trie_v6 = _PrefixTrie()
    for r in ann_v4:
        ann_trie_v4.insert(r["prefix"], r)
    for r in ann_v6:
        ann_trie_v6.insert(r["prefix"], r)
    ann_trie_v4._build()
    ann_trie_v6._build()

    too_specific = {
        "v4": _too_specific(pbr_v4, "v4", ann_trie_v4, reg_trie_v4, asn_names),
        "v6": _too_specific(pbr_v6, "v6", ann_trie_v6, reg_trie_v6, asn_names),
    }

    # ---- Comparativo global ----
    global_comparison = {
        "v4": _global_comparison(pbr_v4, ps_v4, ms_stats_v4, rt_v4, "v4"),
        "v6": _global_comparison(pbr_v6, ps_v6, ms_stats_v6, rt_v6, "v6"),
    }

    # ---- Fase 2: AS_PATH e communities ----
    as_path_stats_out: Optional[dict] = None
    if has_path_data:
        log.info("computing phase-2 as_path stats")
        stats_v4   = _as_path_stats(br_routes_v4, "v4")
        stats_v6   = _as_path_stats(br_routes_v6, "v6")
        prepend_v4 = _top_prependers(br_routes_v4, asn_names, "v4")
        prepend_v6 = _top_prependers(br_routes_v6, asn_names, "v6")
        up_div_v4  = _upstream_diversity(br_routes_v4, asn_names, "v4")
        up_div_v6  = _upstream_diversity(br_routes_v6, asn_names, "v6")
        hygiene_v4 = _hygiene_issues(br_routes_v4, "v4")
        hygiene_v6 = _hygiene_issues(br_routes_v6, "v6")
        comm_v4    = _community_stats(br_routes_v4, "v4")
        comm_v6    = _community_stats(br_routes_v6, "v6")

        as_path_stats_out = {
            "v4":               stats_v4,
            "v6":               stats_v6,
            "top_prependers":   prepend_v4 + prepend_v6,
            "upstream_diversity": up_div_v4 + up_div_v6,
            "hygiene_issues":   hygiene_v4 + hygiene_v6,
            "community_stats":  {"v4": comm_v4, "v6": comm_v6},
        }

    # ---- Montagem do output ----
    output = {
        "snapshot_date":        date_str,
        "generated_at":         now_iso(),
        "has_path_data":        has_path_data,
        "br_asns_visible":      br_asns_visible,
        "br_asns_registered":   br_asns_registered,
        "summary":              summary,
        "pbr_composition":      pbr_composition,
        "prefix_length_dist":   pl_dist,
        "more_specifics":       more_specifics,
        "top_asns_more_specifics": top_ms,
        "aggregation_by_asn":  agg_table,
        "registro_br_coverage": reg_coverage,
        "moas":                 moas,
        "too_specific":         too_specific,
        "global_comparison":    global_comparison,
        "as_path_stats":        as_path_stats_out,
    }

    pub.mkdir(parents=True, exist_ok=True)
    out_path = pub / "routing_analysis.json"
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    # Resumo de poucos KB para o Panorama técnico (a API não carrega os ~14 MB para servir os totais).
    resumo_rotas.gravar(pub, resumo_rotas.montar(
        date_str, pbr_v4, pbr_v6, rpki_index, summary=summary, more_specifics=more_specifics,
        too_specific=too_specific, moas=moas, vrps=len(vrp_list)))
    log.info("routing_analysis written", path=str(out_path),
             pbr_v4=len(pbr_v4), pbr_v6=len(pbr_v6),
             has_path_data=has_path_data)
    return True


def _safe_load(path: Path, log, label: str) -> Optional[dict | list]:
    if not path.exists():
        log.debug("file not found", label=label, path=str(path))
        return None
    try:
        return read_json_gz(path)
    except Exception as exc:
        log.warning("failed loading", label=label, path=str(path), error=str(exc))
        return None


def _load_asn_names(pub: Path, log) -> dict[int, str]:
    """Carrega nomes de ASN do índice publicado."""
    index_path = pub / "asns" / "index.json"
    if not index_path.exists():
        return {}
    try:
        with index_path.open(encoding="utf-8") as f:
            data = json.load(f)
        return {
            a["asn"]: a.get("name", "")
            for a in data
            if isinstance(a, dict) and "asn" in a
        }
    except Exception as exc:
        log.warning("failed loading asn names", error=str(exc))
        return {}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Análise da tabela BGP global com foco em prefixos brasileiros"
    )
    p.add_argument("--date",  default=today_str(),
                   help="data do snapshot (YYYY-MM-DD, padrão: hoje)")
    p.add_argument("--force", action="store_true",
                   help="reprocessa mesmo se routing_analysis.json já existir")
    args = p.parse_args(argv)

    log  = configure_logging()
    base = data_dir()

    pub      = published_path(base, args.date)
    out_path = pub / "routing_analysis.json"
    if not args.force and out_path.exists():
        log.info("already exists, skipping", date=args.date, path=str(out_path))
        return 0

    ok = run(date_str=args.date, base=base, log=log)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
