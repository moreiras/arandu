# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Presença de CDNs nos IXPs: `cdns.json`."""
from __future__ import annotations

import json
from pathlib import Path

from core.common import normalized_path, published_path
from core.jsonio import carregar_json, carregar_json_gz


def publicar_cdn_presence(base: Path, date_str: str, log) -> int:
    """
    Gera published/{date}/cdns.json: matriz de presença de CDNs nos IXPs.
    Usa ixbr_members.json (membership declarada no IX.br) e peeringdb_ixps para externos.
    """
    import yaml

    config_path = Path(__file__).resolve().parents[2] / "config" / "cdns.yaml"
    if not config_path.exists():
        log.warning("cdns.yaml not found, skipping CDN presence")
        return 0

    with open(config_path, encoding="utf-8") as f:
        cdn_config = yaml.safe_load(f)

    cdns = cdn_config.get("cdns", [])

    # IX.br member index: asn -> [ixp_code, ...]
    ixbr_index: dict[int, list[str]] = {}
    raw_dir = base / "raw" / date_str
    if raw_dir.exists():
        for ixp_dir in raw_dir.iterdir():
            if not ixp_dir.is_dir():
                continue
            members_file = ixp_dir / "ixbr_members.json"
            if not members_file.exists():
                continue
            try:
                data = json.loads(members_file.read_bytes())
                code = ixp_dir.name
                for m in data.get("members", []):
                    asn = m.get("asn")
                    if asn:
                        ixbr_index.setdefault(int(asn), []).append(code)
            except Exception:
                pass

    # PeeringDB per_asn index for external IXPs
    pdb_path = normalized_path(base, date_str, "summary") / "peeringdb_ixps.json.gz"
    pdb_per_asn: dict[str, dict] = {}
    if pdb_path.exists():
        pdb_data = carregar_json_gz(pdb_path) or {}
        pdb_per_asn = pdb_data.get("per_asn", {})

    # Build CDN rows
    cdn_rows = []
    for cdn in cdns:
        name = cdn["name"]
        asns = [int(a) for a in cdn.get("asns", [])]
        if not asns:
            continue

        ixbr_set: set[str] = set()
        external_set: set[str] = set()

        for asn in asns:
            for code in ixbr_index.get(asn, []):
                ixbr_set.add(code)
            pdb_entry = pdb_per_asn.get(str(asn), {})
            for code in pdb_entry.get("external", []):
                external_set.add(code)

        cdn_rows.append({
            "name":           name,
            "categorias":     [str(c) for c in cdn.get("categorias", [])],
            "asns":           asns,
            "ixbr":           sorted(ixbr_set),
            "external":       sorted(external_set),
            "ixbr_count":     len(ixbr_set),
            "external_count": len(external_set),
        })

    # Sort CDNs: by total presence desc, then name asc
    cdn_rows.sort(key=lambda r: (-(r["ixbr_count"] + r["external_count"]), r["name"].lower()))

    # Load IXP display names
    pub_dir = published_path(base, date_str)
    ixbr_names: dict[str, str] = {}
    ixp_idx = carregar_json(pub_dir / "ixps" / "index.json") or []
    ixp_list = ixp_idx if isinstance(ixp_idx, list) else ixp_idx.get("ixps", [])
    for ixp in ixp_list:
        ixbr_names[ixp["code"]] = ixp["name"]

    ext_names: dict[str, str] = {}
    ext_idx = carregar_json(pub_dir / "external-ixps" / "index.json") or {}
    for ixp in ext_idx.get("ixps", []):
        ext_names[ixp["code"]] = ixp["name"]

    # Column order for IX.br: all IXPs from index (including those with 0 CDNs),
    # sorted by CDN count desc then code asc
    ixbr_cdn_count: dict[str, int] = {}
    for ixp in ixp_list:
        ixbr_cdn_count[ixp["code"]] = 0  # ensure all appear
    for row in cdn_rows:
        for code in row["ixbr"]:
            ixbr_cdn_count[code] = ixbr_cdn_count.get(code, 0) + 1
    ixbr_columns_codes = sorted(ixbr_cdn_count, key=lambda c: (-ixbr_cdn_count[c], c))

    # Column order for external IXPs: only those with presence (no zero-count)
    ext_cdn_count: dict[str, int] = {}
    for row in cdn_rows:
        for code in row["external"]:
            ext_cdn_count[code] = ext_cdn_count.get(code, 0) + 1
    ext_columns_codes = sorted(ext_cdn_count, key=lambda c: (-ext_cdn_count[c], c))

    output = {
        "snapshot_date": date_str,
        "cdns": cdn_rows,
        "ixbr_columns": [
            {"code": c, "name": ixbr_names.get(c, c), "cdn_count": ixbr_cdn_count[c]}
            for c in ixbr_columns_codes
        ],
        "external_columns": [
            {"code": c, "name": ext_names.get(c, c), "cdn_count": ext_cdn_count[c]}
            for c in ext_columns_codes
        ],
    }

    out_path = pub_dir / "cdns.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")
    log.info("cdn presence written",
             cdns=len(cdn_rows),
             ixbr_cols=len(ixbr_columns_codes),
             ext_cols=len(ext_columns_codes))
    return len(cdn_rows)
