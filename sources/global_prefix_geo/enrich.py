# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`global_prefix_geo` — Geolocalização de prefixos globais (todos os IXPs IX.br)

Para cada prefixo único visto em qualquer IXP do IX.br:
  - Registra quais IXPs o anunciaram (ixps_seen)
  - Registra o ASN originador (origin_asn, do primeiro IXP onde apareceu)
  - Geolocaliza com DB-IP City Lite (CC BY 4.0)

Entrada:
  normalized/{date}/{ixp}/prefix-set-{afi}.json.gz     — lista de prefixos por IXP
  normalized/{date}/{ixp}/origin-prefixes-{afi}.json.gz — {asn: [prefixos]} por IXP
  raw/dbip/dbip-city-lite-{YYYY-MM}.mmdb

Saída:
  normalized/{date}/summary/geo_global_prefixes.json.gz

Uso:
    python -m sources.global_prefix_geo.enrich --date 2026-06-08
    python -m sources.global_prefix_geo.enrich --date 2026-06-08 --mmdb-month 2026-05
"""

from __future__ import annotations

import argparse
import sys
from ipaddress import ip_network
from pathlib import Path

import maxminddb

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    read_json_gz,
    today_str,
    write_json_gz,
)
from sources.prefix_geo.enrich import _download_mmdb, _lookup, _mmdb_month


def _ip_version(prefix: str) -> int:
    return 6 if ":" in prefix else 4


def _build_prefix_index(norm_date_dir: Path) -> tuple[dict[str, set[str]], dict[str, int]]:
    """Varre todos os IXPs em normalized/{date}/ e constrói:
      prefix_ixps  → {prefix: {ixp_code, ...}}
      prefix_origin → {prefix: origin_asn}  (primeiro IXP que resolver wins)
    """
    prefix_ixps: dict[str, set[str]] = {}
    prefix_origin: dict[str, int] = {}

    ixp_dirs = sorted(
        d for d in norm_date_dir.iterdir()
        if d.is_dir() and d.name != "summary"
    )

    for ixp_dir in ixp_dirs:
        code = ixp_dir.name

        for afi in ("v4", "v6"):
            # prefix-set: lista de prefixos únicos vistos neste IXP
            pset_path = ixp_dir / f"prefix-set-{afi}.json.gz"
            if pset_path.exists():
                try:
                    prefixes: list[str] = read_json_gz(pset_path)
                    for p in prefixes:
                        prefix_ixps.setdefault(p, set()).add(code)
                except Exception:
                    pass

            # origin-prefixes: {asn: [prefixos originados]}
            orig_path = ixp_dir / f"origin-prefixes-{afi}.json.gz"
            if orig_path.exists():
                try:
                    orig: dict[int, list[str]] = read_json_gz(orig_path)
                    for asn, pfxs in orig.items():
                        asn_int = int(asn)
                        for p in pfxs:
                            if p not in prefix_origin:
                                prefix_origin[p] = asn_int
                except Exception:
                    pass

    return prefix_ixps, prefix_origin


def run(date_str: str, base: Path, mmdb_month: str | None, log) -> dict:
    mmdb, month = _download_mmdb(base, mmdb_month or _mmdb_month(date_str), log)

    norm_date_dir = base / "normalized" / date_str
    if not norm_date_dir.exists():
        raise FileNotFoundError(
            f"normalized/{date_str}/ não encontrado. Rode as etapas lg_ixbr e bgp_ixp primeiro."
        )

    log.info("scanning ixp prefix files", date=date_str)
    prefix_ixps, prefix_origin = _build_prefix_index(norm_date_dir)

    if not prefix_ixps:
        raise FileNotFoundError(
            f"Nenhum prefix-set encontrado em normalized/{date_str}/. Rode a etapa bgp_ixp primeiro."
        )

    total = len(prefix_ixps)
    log.info("geolocating global prefixes", total=total, mmdb_month=month)

    geo_source = f"dbip-lite-{month}"
    result: dict[str, dict] = {}
    found = 0

    with maxminddb.open_database(str(mmdb)) as reader:
        for prefix, ixps in prefix_ixps.items():
            geo = _lookup(reader, prefix)
            origin_asn = prefix_origin.get(prefix)
            ip_ver = _ip_version(prefix)
            entry: dict = {
                "ixps_seen": sorted(ixps),
                "origin_asn": origin_asn,
                "ip_version": ip_ver,
                "geo_source": geo_source,
            }
            if geo:
                entry.update({
                    "lat": geo["lat"],
                    "lon": geo["lon"],
                    "city": geo["city"],
                    "country": geo["country"],
                    "uf": geo["uf"],
                    "geo_confidence": "city_centroid",
                })
                found += 1
            else:
                entry.update({
                    "lat": None,
                    "lon": None,
                    "city": "",
                    "country": "",
                    "uf": "",
                    "geo_confidence": "unknown",
                })
            result[prefix] = entry

    output = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "mmdb_month": month,
        "geo_source": geo_source,
        "total": total,
        "geolocated": found,
        "unknown": total - found,
        "prefixes": result,
    }

    dst = normalized_path(base, date_str, "summary", "geo_global_prefixes.json.gz")
    write_json_gz(dst, output)
    log.info("geo_global_prefixes saved", path=str(dst), total=total, geolocated=found)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="`global_prefix_geo` — geolocalização de prefixos globais IX.br via DB-IP City Lite"
    )
    parser.add_argument("--date", default=today_str())
    parser.add_argument(
        "--mmdb-month",
        default=None,
        metavar="YYYY-MM",
        help="Versão do banco DB-IP a usar (padrão: mês corrente do snapshot)",
    )
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, mmdb_month=args.mmdb_month, log=log)
    except EnvironmentError as e:
        log.error("env missing", error=str(e))
        return 1
    except FileNotFoundError as e:
        log.error("input not found", error=str(e))
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
