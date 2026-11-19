# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Métricas de IXP: documento de cada IXP e agregado."""
from __future__ import annotations

import json
from pathlib import Path
from core.common import now_iso, published_path

from products.ixp_metrics.entradas import _load_origin_prefixes, _load_prefix_set, _load_rels
from products.ixp_metrics.espaco import _compute_aggregate_afi, _compute_ixp_afi, _parse_nets, _total_space


def gerar_metricas_ixp(
    date_str: str,
    base: Path,
    all_ixps: list[dict],
    nicbr_map: dict[int, dict],
    log,
    lacnic_br_asns: set[int] | None = None,
) -> list[dict]:
    """Gera published/{date}/ixps/{code}.json para cada IXP e um _aggregate.json.

    Fluxo:
      1. Pré-calcula espaço `registro_br` (nicbr_nets/nicbr_space) — reutilizado por todos os IXPs
      2. Pré-calcula espaço da full table (ft_space) — idem
      3. Identifica br_asns_in_ft — denominador para br_asns_pct (ver docstring do módulo)
      4. Para cada IXP: chama _compute_ixp_afi(v4) + _compute_ixp_afi(v6) e grava JSON
      5. Computa _aggregate: union real de todos os IXPs (não soma de contagens)

    Args:
        date_str:       Data do snapshot (YYYY-MM-DD)
        base:           Diretório raiz dos dados
        all_ixps:       Lista de dicts com "code", "name", "uf" dos IXPs
        nicbr_map:      {asn: {"prefixes_v4": [...], "prefixes_v6": [...]}} (`registro_br`)
        log:            Logger estruturado
        lacnic_br_asns: Set de ASNs BR (`lacnic_delegated`); se None, usa nicbr_map.keys()

    Returns:
        Lista de {"ixp": code, "status": "ok"|"error", ...} por IXP processado.
    """
    # ASNs brasileiros: usa LACNIC delegated se disponível, fallback para nicbr_map
    nicbr_asns = lacnic_br_asns if lacnic_br_asns else set(nicbr_map.keys())
    ip_versions = {"v4": 4, "v6": 6}

    # Pré-calcula redes `registro_br` e espaço total — reutilizado por todos os IXPs
    log.info("computing registro_br address space")
    nicbr_nets: dict[str, list] = {}
    nicbr_space: dict[str, int] = {}
    for afi, ver in ip_versions.items():
        pfx = {p for info in nicbr_map.values() for p in info[f"prefixes_{afi}"]}
        nets = sorted(_parse_nets(pfx, ver), key=lambda n: n.network_address)
        nicbr_nets[afi] = nets
        nicbr_space[afi] = _total_space(nets)
        log.info("registro_br space computed", afi=afi, prefixes=len(nets), space=nicbr_space[afi])

    # Pré-calcula espaço da full table — reutilizado por todos os IXPs
    log.info("computing fulltable address space")
    ft_space: dict[str, int] = {}
    for afi, ver in ip_versions.items():
        ft_prefix_set = _load_prefix_set(base, date_str, "summary", afi)
        ft_nets = _parse_nets(ft_prefix_set, ver)
        ft_space[afi] = _total_space(ft_nets)
        del ft_nets
        log.info("ft space computed", afi=afi, space=ft_space[afi])

    # ASNs BR presentes na full table como originadores (= "ativos")
    br_asns_in_ft: dict[str, set[int]] = {"v4": set(), "v6": set()}
    for afi in ("v4", "v6"):
        ft_origins = _load_origin_prefixes(base, date_str, "summary", afi)
        for asn_str in ft_origins:
            try:
                asn = int(asn_str)
            except ValueError:
                continue
            if asn in nicbr_asns:
                br_asns_in_ft[afi].add(asn)

    results = []
    pub_dir = published_path(base, date_str, "ixps")
    pub_dir.mkdir(parents=True, exist_ok=True)

    for ixp in all_ixps:
        code = ixp["code"]
        log.info("computing p2", ixp=code)
        try:
            doc = {
                "ixp": code,
                "name": ixp.get("name", ""),
                "uf": ixp.get("uf", ""),
                "snapshot_date": date_str,
                "generated_at": now_iso(),
            }
            for afi, ver in ip_versions.items():
                doc[afi] = _compute_ixp_afi(
                    code, date_str, base, afi, ver,
                    nicbr_asns,
                    nicbr_nets[afi],
                    nicbr_space[afi],
                    br_asns_in_ft[afi],
                    ft_space[afi],
                )

            out_file = pub_dir / f"{code}.json"
            out_file.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            log.info("p2 written", ixp=code, path=str(out_file))
            results.append({"ixp": code, "status": "ok", "path": str(out_file)})
        except Exception as exc:
            log.error("p2 error", ixp=code, error=str(exc))
            results.append({"ixp": code, "status": "error", "error": str(exc)})

    # Agrega todos os IXPs como um IXP virtual com métricas reais (union dos conjuntos)
    log.info("computing aggregate (union of all IXPs)")
    agg_v4 = _compute_aggregate_afi(
        date_str, base, all_ixps, "v4", 4,
        nicbr_asns, nicbr_nets["v4"], nicbr_space["v4"],
        br_asns_in_ft["v4"], ft_space["v4"],
    )
    agg_v6 = _compute_aggregate_afi(
        date_str, base, all_ixps, "v6", 6,
        nicbr_asns, nicbr_nets["v6"], nicbr_space["v6"],
        br_asns_in_ft["v6"], ft_space["v6"],
    )
    # União v4∪v6 real — passa extra por todos os IXPs (arquivos em cache do SO)
    log.info("computing cross-afi union counts")
    all_direct: set[int] = set()
    all_origin: set[int] = set()
    all_br_origin: set[int] = set()
    for ixp in all_ixps:
        for afi in ("v4", "v6"):
            rels = _load_rels(base, date_str, ixp["code"], afi)
            if not rels:
                continue
            rd = rels.get("relationships", {})
            all_direct |= set(rd.get("asn_direct", []))
            all_origin |= set(rd.get("asn_origin", []))
    v4_origin_br = set(agg_v4.get("br_asns_origin", [])) if isinstance(agg_v4, dict) else set()
    v6_origin_br = set(agg_v6.get("br_asns_origin", [])) if isinstance(agg_v6, dict) else set()
    all_br_origin = v4_origin_br | v6_origin_br

    agg_doc = {
        "ixp": "_aggregate",
        "name": "Agregado IX.br",
        "uf": "BR",
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "ixp_count": len(all_ixps),
        "asn_direct_union_count": len(all_direct),
        "asn_origin_union_count": len(all_origin),
        "br_asns_origin_union_count": len(all_br_origin),
        "v4": agg_v4,
        "v6": agg_v6,
    }
    agg_file = pub_dir / "_aggregate.json"
    agg_file.write_text(json.dumps(agg_doc, ensure_ascii=False), encoding="utf-8")
    log.info("aggregate written", path=str(agg_file),
             asn_direct=agg_doc["asn_direct_union_count"],
             asn_origin=agg_doc["asn_origin_union_count"],
             br_origin=agg_doc["br_asns_origin_union_count"])

    return results
