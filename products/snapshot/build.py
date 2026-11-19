# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Resumo (`summary.json`) e manifesto (`manifest.json`) do snapshot."""
from __future__ import annotations

import json
from pathlib import Path

from core import intermediarios
from core.common import app_version, normalized_path, now_iso, published_path, raw_existente, raw_path
from core.jsonio import carregar_json, carregar_json_gz
from products.ixp_docs.build import _ixp_raw_status

PIPELINE_VERSION = app_version()  # arquivo VERSION (fonte única)
_IPV6_48 = 2 ** 80  # addresses per /48 IPv6 block


def _load_global_metrics(base: Path, date_str: str, ixp_index: list[dict]) -> dict:
    """
    Lê métricas globais do primeiro IXP disponível.
    ft_space e br_prefix_declared_space são idênticos para todos os IXPs
    do mesmo snapshot (calculados uma vez pelas métricas de IXP).
    """
    result = {
        "ft_space_v4": 0,
        "ft_space_v6": 0,
        "m3_declared_space_v4": 0,
        "m3_declared_space_v6": 0,
    }
    pub_dir = published_path(base, date_str, "ixps")
    for entry in ixp_index:
        if entry.get("status") == "missing":
            continue
        doc = carregar_json(pub_dir / f"{entry['code']}.json")
        if doc is None:
            continue
        for afi, ft_key, m3_key in [
            ("v4", "ft_space_v4", "m3_declared_space_v4"),
            ("v6", "ft_space_v6", "m3_declared_space_v6"),
        ]:
            afi_data = doc.get(afi, {})
            if isinstance(afi_data, dict):
                if afi_data.get("ft_space", 0):
                    result[ft_key] = afi_data["ft_space"]
                if afi_data.get("br_prefix_declared_space", 0):
                    result[m3_key] = afi_data["br_prefix_declared_space"]
        if result["ft_space_v4"] and result["ft_space_v6"]:
            break
    return result


def _load_registro_br_stats(base: Path, date_str: str) -> dict:
    """Contagens do `registro_br`: total de ASNs e prefixos IPv4/IPv6 declarados."""
    path = normalized_path(base, date_str, "summary") / "registro_br.json.gz"
    data = carregar_json_gz(path)
    if not data:
        return {}
    asns = data.get("asns", [])
    return {
        "total_asns": len(asns),
        "total_prefixes_v4": sum(len(a.get("prefixes_v4", [])) for a in asns),
        "total_prefixes_v6": sum(len(a.get("prefixes_v6", [])) for a in asns),
    }


# ---------------------------------------------------------------------------
# Hilbert /16 density helpers
# ---------------------------------------------------------------------------

_IPV6_48 = 2 ** 80  # addresses per /48 IPv6 block


def publicar_summary(
    base: Path,
    date_str: str,
    ixp_index: list[dict],
    asn_index: list[dict],
    all_ixps: list[dict],
    ixp_aggregate: dict,
    ixp_all_v4_prefixes: set[str],
    ixp_all_v6_prefixes: set[str],
    log,
    hilbert_v4: dict | None = None,
    hilbert_v6: dict | None = None,
) -> dict:
    """Gera summary.json com totais e estatísticas globais do snapshot."""
    ixp_ok = sum(1 for e in ixp_index if e.get("status") == "ok")
    ixp_partial = sum(1 for e in ixp_index if e.get("status") == "partial")
    ixp_missing = sum(1 for e in ixp_index if e.get("status") == "missing")
    ixps_failed = [e["code"] for e in ixp_index if e.get("status") in ("missing", "partial")]

    norm_summary = normalized_path(base, date_str, "summary")
    ft_v4_ok = (norm_summary / "prefix-set-v4.json.gz").exists()
    ft_v6_ok = (norm_summary / "prefix-set-v6.json.gz").exists()

    registro_br_path = normalized_path(base, date_str, "summary") / "registro_br.json.gz"
    registro_br_status = "ok" if registro_br_path.exists() else "missing"

    registro_br_stats = _load_registro_br_stats(base, date_str)
    global_metrics = _load_global_metrics(base, date_str, ixp_index)

    norm_sum = normalized_path(base, date_str, "summary")
    pdb_nets_data = carregar_json_gz(norm_sum / "peeringdb_networks.json.gz") or {}
    br_asns_peeringdb: int | None = pdb_nets_data.get("pdb_registered")
    geo_orgs_data = carregar_json_gz(norm_sum / "geo_orgs.json.gz") or {}
    br_asns_geolocalized: int | None = geo_orgs_data.get("geolocated")

    br_asns = [a for a in asn_index if a["is_br"]]
    total_asns_br = len(br_asns)
    br_with_ipv6 = sum(1 for a in br_asns if a["has_ipv6"])
    br_ipv6_pct = round(br_with_ipv6 / total_asns_br * 100, 2) if total_asns_br > 0 else 0.0

    # ASNs BR com pelo menos um prefixo visível na full table global
    br_asns_in_ft = sum(
        1 for a in br_asns
        if a.get("global_prefixes_v4_count", 0) > 0 or a.get("global_prefixes_v6_count", 0) > 0
    )

    ft_v4 = global_metrics["ft_space_v4"]
    ft_v6 = global_metrics["ft_space_v6"]

    # Contagens de prefixos da full table (prefix-set-v4/v6.json.gz)
    norm_dir = normalized_path(base, date_str, "summary")
    ft_v4_count = len(carregar_json_gz(norm_dir / "prefix-set-v4.json.gz") or [])
    ft_v6_count = len(carregar_json_gz(norm_dir / "prefix-set-v6.json.gz") or [])

    # % do espaço alocado ao BR (Registro.br) visível na full table global
    # Calculado a partir das densidades do mapa Hilbert IPv4 (rir_br vs rir_br_visible)
    v4_br_cov_pct: float | None = None
    v4_br_pct_of_ft: float | None = None
    if hilbert_v4:
        rir_br_total = sum(hilbert_v4.get("rir_br", []))
        rir_br_vis   = sum(hilbert_v4.get("rir_br_visible", []))
        global_all_total = sum(hilbert_v4.get("global_all", []))
        if rir_br_total > 0:
            v4_br_cov_pct = round(rir_br_vis / rir_br_total * 100, 2)
        if global_all_total > 0:
            v4_br_pct_of_ft = round(rir_br_vis / global_all_total * 100, 2)

    # Mesmo cálculo para IPv6 — dados esparsos por bloco RIR
    # Cada célula Hilbert v6 representa um bloco /32 = 2^16 /48s.
    # IMPORTANTE: v6_space_48 (soma bruta de endereços / 2^80) e v6_global_all × 65536
    # NÃO são equivalentes porque prefixos > /32 (ex: /48, /56) ocupam 1 célula mas
    # representam espaço menor que 1 /32. Por isso, o espaço BR visível na FT é
    # computado diretamente em células e convertido para /48s, sem cross-multiplicação
    # com v6_space_48.
    _V6_CELL_48 = 2**16  # /48s por célula Hilbert /32
    v6_br_cov_pct: float | None = None
    v6_br_pct_of_ft: float | None = None
    v6_rir_total_48: int | None = None
    v6_br_space_48: int | None = None
    if hilbert_v6:
        v6_rir_total      = sum(len(blk.get("rir_br", [])) for blk in hilbert_v6.values())
        v6_rir_vis        = sum(len(blk.get("rir_br_visible", [])) for blk in hilbert_v6.values())
        v6_global_all     = sum(len(blk.get("global_all", [])) for blk in hilbert_v6.values())
        if v6_rir_total > 0:
            v6_br_cov_pct = round(v6_rir_vis / v6_rir_total * 100, 2)
        if v6_global_all > 0:
            v6_br_pct_of_ft = round(v6_rir_vis / v6_global_all * 100, 2)
        # Espaço em /48s derivado de células — denominador consistente
        v6_rir_total_48 = v6_rir_total * _V6_CELL_48
        v6_br_space_48  = v6_rir_vis   * _V6_CELL_48

    global_table = {
        "v4_prefixes": ft_v4_count,
        "v4_space_24": ft_v4 // 256 if ft_v4 else 0,
        "v4_br_coverage_pct": v4_br_cov_pct,
        # % do espaço BR visível na FT em relação ao espaço total da FT
        "v4_br_pct_of_ft": v4_br_pct_of_ft,
        "v6_prefixes": ft_v6_count,
        "v6_space_48": round(float(ft_v6) / _IPV6_48, 2) if ft_v6 else 0.0,
        "v6_br_coverage_pct": v6_br_cov_pct,
        "v6_br_pct_of_ft": v6_br_pct_of_ft,
        # Espaço BR alocado (Registro.br) e visível na FT, em /48s — célula × 65536
        # Usar estes campos em vez de v6_space_48 × v6_br_pct_of_ft (denominadores incompatíveis)
        "v6_rir_total_48": v6_rir_total_48,
        "v6_br_space_48": v6_br_space_48,
        "total_asns": len(asn_index),
        "br_asns_in_ft": br_asns_in_ft,
    }

    # Agrega métricas reais do _aggregate.json (gerado por metrics.py)
    agg_v4 = ixp_aggregate.get("_v4", {}) or {}
    agg_v6 = ixp_aggregate.get("_v6", {}) or {}
    ixp_agg_final = {
        "asn_direct_union_count": ixp_aggregate.get("asn_direct_union_count", 0),
        "asn_origin_union_count": ixp_aggregate.get("asn_origin_union_count", 0),
        "br_asns_origin_union_count": ixp_aggregate.get("br_asns_origin_union_count", 0),
        # IPv4
        "v4_prefixes": agg_v4.get("unique_prefixes", len(ixp_all_v4_prefixes)),
        "v4_space_24": agg_v4.get("ixp_space", 0) // 256 if agg_v4.get("ixp_space") else len(ixp_all_v4_prefixes),
        "v4_coverage_pct": agg_v4.get("ixp_vs_fulltable_space_pct", 0.0),
        "v4_br_coverage_pct": agg_v4.get("br_prefix_coverage_pct", 0.0),
        # IPv6
        "v6_prefixes": agg_v6.get("unique_prefixes", len(ixp_all_v6_prefixes)),
        "v6_space_48": round(float(agg_v6.get("ixp_space", 0)) / _IPV6_48, 2) if agg_v6.get("ixp_space") else 0.0,
        "v6_coverage_pct": agg_v6.get("ixp_vs_fulltable_space_pct", 0.0),
        "v6_br_coverage_pct": agg_v6.get("br_prefix_coverage_pct", 0.0),
    }

    return {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "pipeline_version": PIPELINE_VERSION,
        "ixps_configured": len(all_ixps),
        "ixps_ok": ixp_ok,
        "ixps_partial": ixp_partial,
        "ixps_missing": ixp_missing,
        "ixps_failed": ixps_failed,
        "fulltable_v4_status": "ok" if ft_v4_ok else "missing",
        "fulltable_v6_status": "ok" if ft_v6_ok else "missing",
        "registro_br_status": registro_br_status,
        "total_asns_br": total_asns_br,
        "total_asns_global": len(asn_index),
        "br_asns_with_ipv6": br_with_ipv6,
        "br_ipv6_pct": br_ipv6_pct,
        "m3_asns": registro_br_stats.get("total_asns", 0),
        "m3_prefixes_v4": registro_br_stats.get("total_prefixes_v4", 0),
        "m3_prefixes_v6": registro_br_stats.get("total_prefixes_v6", 0),
        "m3_declared_space_v4": global_metrics["m3_declared_space_v4"],
        "m3_declared_space_v6": global_metrics["m3_declared_space_v6"],
        # mesmos números com o nome atual; os `m3_` seguem por compatibilidade (core/chaves_registro.py)
        "registro_br_asns": registro_br_stats.get("total_asns", 0),
        "registro_br_prefixes_v4": registro_br_stats.get("total_prefixes_v4", 0),
        "registro_br_prefixes_v6": registro_br_stats.get("total_prefixes_v6", 0),
        "registro_br_declared_space_v4": global_metrics["m3_declared_space_v4"],
        "registro_br_declared_space_v6": global_metrics["m3_declared_space_v6"],
        "ft_space_v4": ft_v4,
        "ft_space_v6": ft_v6,
        "br_asns_peeringdb": br_asns_peeringdb,
        "br_asns_geolocalized": br_asns_geolocalized,
        "global_table": global_table,
        "ixp_aggregate": ixp_agg_final,
    }


def montar_manifesto(
    date_str: str,
    all_ixps: list[dict],
    ixp_index: list[dict],
    summary: dict,
    checksums: dict[str, str],
    geolite2_version: str | None = None,
) -> dict:
    """Monta manifest.json com metadados do pipeline e checksums de todos os artefatos."""
    ixps_collected = [e["code"] for e in ixp_index if e.get("status") in ("ok", "partial")]
    ixps_failed = [e["code"] for e in ixp_index if e.get("status") not in ("ok", "partial")]

    return {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "pipeline_version": PIPELINE_VERSION,
        "ixps_configured": [ix["code"] for ix in all_ixps],
        "ixps_collected": ixps_collected,
        "ixps_failed": ixps_failed,
        "fulltable_v4_status": summary.get("fulltable_v4_status", "unknown"),
        "fulltable_v6_status": summary.get("fulltable_v6_status", "unknown"),
        "registro_br_status": summary.get("registro_br_status", "unknown"),
        "total_asns_br": summary.get("total_asns_br", 0),
        "total_asns_global": summary.get("total_asns_global", 0),
        "m3_prefixes_v4": summary.get("m3_prefixes_v4", 0),
        "m3_prefixes_v6": summary.get("m3_prefixes_v6", 0),
        "registro_br_prefixes_v4": summary.get("registro_br_prefixes_v4", summary.get("m3_prefixes_v4", 0)),
        "registro_br_prefixes_v6": summary.get("registro_br_prefixes_v6", summary.get("m3_prefixes_v6", 0)),
        "ft_space_v4": summary.get("ft_space_v4", 0),
        "ft_space_v6": summary.get("ft_space_v6", 0),
        "geolite2_version": geolite2_version,
        "checksums": checksums,
    }


def executar_resumo(base: Path, date_str: str, log, all_ixps: list[dict]) -> dict:
    """Produto `snapshot`, resumo: `summary.json`. Lê os índices e os Hilbert já publicados e os conjuntos de prefixos de `build/` (entregas dos
    produtos anteriores); o agregado de IXPs é recalculado por `publicar_ixp_index` (puro)."""
    from products.ixp_docs.build import publicar_ixp_index

    pub = published_path(base, date_str)
    ixp_index, ixp_aggregate = publicar_ixp_index(base, date_str, all_ixps, log)
    asn_index = carregar_json(pub / "asns" / "index.json") or []
    conj = intermediarios.ler_conjuntos(base, date_str)
    log.info("building summary")
    summary = publicar_summary(
        base, date_str, ixp_index, asn_index, all_ixps, ixp_aggregate, conj["ixp_all_v4"], conj["ixp_all_v6"], log,
        hilbert_v4=carregar_json(pub / "hilbert_v4.json"), hilbert_v6=carregar_json(pub / "hilbert_v6.json"))
    (pub / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("summary written")
    return summary
