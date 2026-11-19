# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Detalhe de um snapshot (`GET /api/v1/snapshots/{date}`): resumo enriquecido + metadados do manifesto.

O resumo enriquecido exige várias passagens sobre índices grandes (ASNs, IXPs, SICI, SCM). Calculado a cada
data consultada, custaria de 130 a 530 MiB de RSS por data na API, que não voltam ao SO (medido). Por isso o PIPELINE o
calcula uma vez e grava `snapshot_detail.json` ao lado dos demais artefatos; a API só lê esse arquivo (alguns KiB). Sem o
arquivo, a API recalcula.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from core.chaves_registro import com_os_dois_nomes

SIDECAR = "snapshot_detail.json"
SIDECAR_VERSION = 1


def compute_detail(store: Any, date_str: str) -> Optional[dict]:
    """{"date", "summary", "manifest"} do snapshot, ou None se não houver summary.json."""
    base_summary = store.summary(date_str)
    if base_summary is None:
        return None
    summary = dict(base_summary)          # não polui o cache do Store com os campos derivados

    # Augment summary with computed fields not pre-calculated in snapshot_builder
    try:
        asn_index = store.asn_index(date_str)
        br_asns = [a for a in asn_index if a.get("is_br")]
        summary["br_asns_ft_v4"] = sum(
            1 for a in br_asns if a.get("global_prefixes_v4_count", 0) > 0
        )
        summary["br_asns_ft_v6"] = sum(
            1 for a in br_asns if a.get("global_prefixes_v6_count", 0) > 0
        )
        # Soma de usuários finais estimados pelo APNIC entre os ASNs BR
        summary["br_apnic_users_total"] = sum(
            a.get("apnic_users") or 0 for a in br_asns
        )
    except Exception:
        pass

    # BR ASNs no IX.br por AFI (só v4, só v6, ambos)
    try:
        summary.update(store.ixp_br_origin_sets(date_str))
    except Exception:
        pass

    # Usuários estimados (IPv4) visíveis no IX.br como um todo: mesma metodologia
    # de /ixps/{code}/estimated-users (fração do espaço anunciado do AS visível ×
    # usuários APNIC), mas unindo os prefixos de cada AS em todos os IXPs antes de
    # calcular a fração — evita contar o mesmo espaço/usuários uma vez por IXP.
    try:
        summary["ixp_estimated_users_v4"] = store.ixp_estimated_users_aggregate(date_str)["estimated_users"]
    except Exception:
        pass

    # ASNs BR distintos presentes em IXPs externos (PeeringDB) — união deduplicada
    # entre todos os IXPs externos, evitando contar o mesmo AS uma vez por IXP.
    try:
        summary["external_ixps_br_asn_union_count"] = len(
            store.external_ixps_br_asn_union(date_str)
        )
    except Exception:
        pass

    # Pre-divide large IPv6 space (Python handles BigInt; JS would lose precision)
    try:
        m3_v4 = int(summary.get("m3_declared_space_v4", 0))
        m3_v6 = int(summary.get("m3_declared_space_v6", 0))
        summary["m3_declared_space_v4_24"] = m3_v4 // 256
        summary["m3_declared_space_v6_48"] = m3_v6 // (2**80)
        summary["registro_br_declared_space_v4_24"] = summary["m3_declared_space_v4_24"]
        summary["registro_br_declared_space_v6_48"] = summary["m3_declared_space_v6_48"]
    except Exception:
        pass

    # Provedores fixos/móveis ativos (SCM/SMP com ASN ou que informaram acessos ao
    # SICI) e assinantes B2B/B2C (pessoa jurídica/física) declarados ao SICI.
    try:
        operadoras = store.operadora_index(date_str)
        summary["provedores_fixos_ativos"] = sum(
            1 for r in operadoras if r.get("com_asn") or r.get("ativo")
        )
        summary["assinantes_b2b_fixos"] = sum(r.get("acessos_pj") or 0 for r in operadoras)
        summary["assinantes_b2c_fixos"] = sum(r.get("acessos_pf") or 0 for r in operadoras)
    except Exception:
        pass

    try:
        operadoras_movel = store.operadora_movel_index(date_str)
        summary["provedores_moveis_ativos"] = sum(
            1 for r in operadoras_movel if r.get("com_asn") or r.get("ativo")
        )
        summary["assinantes_b2b_moveis"] = sum(r.get("acessos_pj") or 0 for r in operadoras_movel)
        summary["assinantes_b2c_moveis"] = sum(r.get("acessos_pf") or 0 for r in operadoras_movel)
    except Exception:
        pass

    detail = {"date": date_str, "summary": summary, "manifest": manifest_meta(store.manifest(date_str), store.base, date_str)}
    return detail


def manifest_meta(manifest: Optional[dict], base: Optional[Path] = None, date_str: Optional[str] = None) -> Optional[dict]:
    if not manifest:
        return None
    fontes = manifest.get("sources")
    if fontes is None and base is not None and date_str:          # snapshot sem o campo: índice lateral
        try:
            from core.store import fontes_do_legado

            fontes = fontes_do_legado(Path(base), date_str)
        except Exception:  # noqa: BLE001
            fontes = None
    return {
        "layout_version": manifest.get("layout_version", 1),
        "sources": fontes,
        "pipeline_version": manifest.get("pipeline_version"),
        "generated_at": manifest.get("generated_at"),
        "ixps_configured": manifest.get("ixps_configured", []),
        "ixps_collected": manifest.get("ixps_collected", []),
        "ixps_failed": manifest.get("ixps_failed", []),
        "coleta": manifest.get("coleta"),
        "coleta_ok": manifest.get("coleta_ok"),
        "checks": manifest.get("checks"),
    }


def read_sidecar(base: Path, date_str: str) -> Optional[dict]:
    try:
        d = json.loads((Path(base) / "published" / date_str / SIDECAR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not (isinstance(d, dict) and d.get("versao") == SIDECAR_VERSION and "summary" in d):
        return None
    d["summary"] = com_os_dois_nomes(d["summary"])     # detalhe gravado antes dos nomes `registro_br_` só tem os `m3_`
    return d


def write_sidecar(base: Path, date_str: str, detail: dict) -> Path:
    path = Path(base) / "published" / date_str / SIDECAR
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"versao": SIDECAR_VERSION, **detail}, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
    return path


def build_sidecar(base: Path, date_str: str, log=None) -> Optional[Path]:
    """Calcula e grava o detalhe (usa o Store como a API; exige os artefatos do `snapshot_completo` já publicados)."""
    from api.store import Store

    store = Store(Path(base))
    detail = compute_detail(store, date_str)
    if detail is None:
        return None
    path = write_sidecar(base, date_str, detail)
    if log:
        log.info("snapshot detail written", path=str(path), campos=len(detail["summary"]))
    return path


def refresh_manifest_meta(base: Path, date_str: str) -> bool:
    """Atualiza só o bloco `manifest` do detalhe (a sanidade de coleta muda o manifesto depois do `snapshot_completo`)."""
    side = read_sidecar(base, date_str)
    if side is None:
        return False
    try:
        manifest = json.loads((Path(base) / "published" / date_str / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    side["manifest"] = manifest_meta(manifest, base, date_str)
    side.pop("versao", None)
    write_sidecar(base, date_str, side)
    return True
