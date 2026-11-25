# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Documentos dos IXPs externos: `external-ixps/index.json` e `{code}.json`.
`load_config` entrega a lista de IXPs externos do PeeringDB (`core.common.load_peeringdb_ixps_config`; injetada para os testes)."""
from __future__ import annotations

import json
from pathlib import Path

from core.ixp_coleta import marcar_ptt
from core.common import load_ixps, normalized_path, published_path, raw_bgp_ixp, raw_existente, raw_path
from core.jsonio import carregar_json, carregar_json_gz

_IPV6_48 = 2 ** 80  # endereços por bloco /48 IPv6


def publicar_external_ixps(base: Path, date_str: str, br_asns: set[int], log, load_config) -> int:
    """
    Gera published/{date}/external-ixps/index.json e {code}.json.
    Retorna número de IXPs publicados (0 se peeringdb_ixps.json.gz ausente).
    """
    norm_path = normalized_path(base, date_str, "summary") / "peeringdb_ixps.json.gz"
    if not norm_path.exists():
        log.info("peeringdb_ixps not found, skipping external-ixps build")
        return 0

    data = carregar_json_gz(norm_path)
    if not data:
        return 0

    external_ixps = data.get("external_ixps", {})
    # Nome do membro pelo ASN (RIPE asn.txt, `sources.asn_names`): o PeeringDB (netixlan) só dá o nome do PTT
    nomes_arq = normalized_path(base, date_str, "summary") / "asn_names.json.gz"
    nomes = (carregar_json_gz(nomes_arq) or {}) if nomes_arq.exists() else {}
    cfg_map = {
        ixp["code"]: ixp
        for ixp in load_config()["external"]
    }

    out_dir = published_path(base, date_str, "external-ixps")
    out_dir.mkdir(parents=True, exist_ok=True)

    index = []
    for code, ixp_data in external_ixps.items():
        cfg = cfg_map.get(code, {})
        members_raw = ixp_data.get("members", [])

        # `members` tem uma linha por porta (netixlan do PeeringDB); uma rede com duas portas conta uma vez em `redes`
        members = []
        for m in members_raw:
            asn = m["asn"]
            is_br = asn in br_asns
            members.append({
                "asn":   asn,
                "name":  nomes.get(str(asn), ""),
                "speed": m.get("speed", 0),
                "is_br": is_br,
            })

        doc = {
            "code":           code,
            "name":           ixp_data.get("name", cfg.get("name", code)),
            "city":           ixp_data.get("city", cfg.get("city", "")),
            "country":        ixp_data.get("country", cfg.get("country", "")),
            "pdb_ix_id":      ixp_data.get("pdb_ix_id", cfg.get("pdb_ix_id")),
            "redes":          len({m["asn"] for m in members}),
            "redes_br":       len({m["asn"] for m in members if m["is_br"]}),
            "portas":         len(members),
            "last_updated":   date_str,
            "members":        members,
        }
        # nomes antigos, mantidos como alias de `redes` e `redes_br` (até 2026-11 contavam portas)
        doc["member_count"], doc["br_member_count"] = doc["redes"], doc["redes_br"]
        (out_dir / f"{code}.json").write_text(
            json.dumps(doc, ensure_ascii=False), encoding="utf-8"
        )

        index.append({
            "code":           code,
            "name":           doc["name"],
            "city":           doc["city"],
            "country":        doc["country"],
            "pdb_ix_id":      doc["pdb_ix_id"],
            "redes":          doc["redes"],
            "redes_br":       doc["redes_br"],
            "portas":         doc["portas"],
            "member_count":   doc["member_count"],
            "br_member_count": doc["br_member_count"],
            "last_updated":   date_str,
        })

    # Ordena por membros BR desc
    index.sort(key=lambda x: x["br_member_count"], reverse=True)
    (out_dir / "index.json").write_text(
        json.dumps({"ixps": index, "snapshot_date": date_str}, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("external-ixps built", ixps=len(index))
    return len(index)


def _ixp_raw_status(base: Path, date_str: str, code: str) -> str:
    """ok | partial | missing — baseado na presença de arquivos raw."""
    rd = raw_path(base, date_str, code)
    v4 = raw_bgp_ixp(rd, "v4", code, date_str).exists()
    v6 = raw_bgp_ixp(rd, "v6", code, date_str).exists()
    if v4 and v6:
        return "ok"
    if v4 or v6:
        return "partial"
    return "missing"


def publicar_ixp_index(
    base: Path,
    date_str: str,
    all_ixps: list[dict],
    log,
) -> tuple[list[dict], dict]:
    """
    Gera ixps/index.json com campos compactos de cada IXP.
    Retorna (index, aggregate) onde aggregate agrega todos os IXPs.
    """
    pub_dir = published_path(base, date_str, "ixps")
    index = []

    for ixp in all_ixps:
        code = ixp["code"]
        status = _ixp_raw_status(base, date_str, code)
        doc = carregar_json(pub_dir / f"{code}.json")

        entry: dict = {
            "code": code,
            "name": ixp.get("name", ""),
            "uf": ixp.get("uf", ""),
            "status": status,
        }

        if doc:
            v4_data = doc.get("v4", {})
            v6_data = doc.get("v6", {})
            v4_ok = isinstance(v4_data, dict) and v4_data.get("status") != "missing"
            v6_ok = isinstance(v6_data, dict) and v6_data.get("status") != "missing"

            # União de ASNs diretos (v4 ∪ v6) — listas disponíveis no documento
            v4_direct = set(v4_data.get("asn_direct", [])) if v4_ok else set()
            v6_direct = set(v6_data.get("asn_direct", [])) if v6_ok else set()
            direct_union = v4_direct | v6_direct

            # União de ASNs BR diretos (v4 ∪ v6) — presentes nos route servers
            v4_br_direct = set(v4_data.get("br_asns_direct", [])) if v4_ok else set()
            v6_br_direct = set(v6_data.get("br_asns_direct", [])) if v6_ok else set()
            br_direct_union = v4_br_direct | v6_br_direct

            # União de ASNs BR originadores (v4 ∪ v6)
            v4_br_orig = set(v4_data.get("br_asns_origin", [])) if v4_ok else set()
            v6_br_orig = set(v6_data.get("br_asns_origin", [])) if v6_ok else set()
            br_origin_union = v4_br_orig | v6_br_orig

            entry["asn_direct_union_count"] = len(direct_union)
            # união IPv6 ∪ IPv4 gravada pelas métricas do PTT; documento anterior a ela cai no maior dos dois (aproximação antiga)
            uniao = doc.get("asn_origin_union_count")
            entry["asn_origin_union_count"] = uniao if isinstance(uniao, int) else max(
                v4_data.get("asn_origin_count", 0) if v4_ok else 0,
                v6_data.get("asn_origin_count", 0) if v6_ok else 0,
            )
            entry["br_asns_direct_union_count"] = len(br_direct_union)
            entry["br_asns_origin_union_count"] = len(br_origin_union)

            for afi in ("v4", "v6"):
                afi_data = doc.get(afi, {})
                if not isinstance(afi_data, dict) or afi_data.get("status") == "missing":
                    entry[afi] = {"status": "missing"}
                else:
                    raw_space = afi_data.get("ixp_space", 0)
                    if afi == "v4":
                        space_units = raw_space // 256  # /24 units
                    else:
                        space_units = float(raw_space) / _IPV6_48  # /48 units
                    entry[afi] = {
                        "total_routes": afi_data.get("total_routes", 0),
                        "unique_prefixes": afi_data.get("unique_prefixes", 0),
                        "ixp_space": raw_space,
                        "ixp_space_units": round(space_units, 2) if afi == "v6" else space_units,
                        "asn_direct_count": afi_data.get("asn_direct_count", 0),
                        "asn_origin_count": afi_data.get("asn_origin_count", 0),
                        "asn_stub_count": afi_data.get("asn_stub_count", 0),
                        "br_asns_origin_count": afi_data.get("br_asns_origin_count", 0),
                        "br_prefix_coverage_pct": afi_data.get("br_prefix_coverage_pct", 0.0),
                        "ixp_vs_fulltable_space_pct": afi_data.get("ixp_vs_fulltable_space_pct", 0.0),
                    }

        # Membros registrados no IX.br (inclui quem não usa RS) — fonte: `rdap`
        members_path = raw_path(base, date_str, code) / "ixbr_members.json"
        members_data = carregar_json(members_path)
        if members_data is not None:
            entry["ixbr_members_count"] = members_data.get("members_count")

        if doc:
            marcar_ptt(entry)              # `coleta` por família; tabela vazia num LG que respondeu não é "ok" (nem 0% de cobertura)
        index.append(entry)
        log.debug("ixp indexed", code=code, status=entry["status"])

    # Carrega o agregado pré-computado pelo metrics.py (métricas reais, não aproximações)
    agg_doc = carregar_json(pub_dir / "_aggregate.json") or {}
    agg_v4 = agg_doc.get("v4", {})
    agg_v6 = agg_doc.get("v6", {})
    _IPV6_48_local = 2 ** (128 - 48)
    aggregate = {
        "asn_direct_union_count": agg_doc.get("asn_direct_union_count", 0),
        "asn_origin_union_count": agg_doc.get("asn_origin_union_count", 0),
        "br_asns_origin_union_count": agg_doc.get("br_asns_origin_union_count", 0),
        # Por AFI — usados depois em build_summary
        "_v4": agg_v4,
        "_v6": agg_v6,
    }
    return index, aggregate


def executar_indice(base: Path, date_str: str, log, all_ixps=None) -> dict:
    """Produto `ixp_docs`, parte 1: `ixps/index.json` (o agregado entra no resumo; `publicar_ixp_index` não tem efeito colateral).

    `all_ixps`: lista de PTTs (padrão: a da configuração; os testes injetam uma fictícia)."""
    ixp_index, _ = publicar_ixp_index(base, date_str, all_ixps if all_ixps is not None else load_ixps(), log)
    destino = published_path(base, date_str, "ixps") / "index.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(ixp_index, ensure_ascii=False), encoding="utf-8")
    log.info("ixp index written", ixps=len(ixp_index))
    return {"ixps_indexed": len(ixp_index)}


def executar_externos(base: Path, date_str: str, log, load_config=None) -> dict:
    """Produto `ixp_docs`, parte 2: IXPs externos do PeeringDB; os ASNs BR vêm de `asns/index.json`."""
    from core.common import load_peeringdb_ixps_config

    indice = carregar_json(published_path(base, date_str, "asns") / "index.json") or []
    br: set[int] = set()
    for entry in indice:
        if entry.get("is_br"):
            try:
                br.add(int(entry["asn"]))
            except (KeyError, ValueError):
                pass
    return {"external_ixps": publicar_external_ixps(base, date_str, br, log, load_config or load_peeringdb_ixps_config)}
