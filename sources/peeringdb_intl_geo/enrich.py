# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Geolocalização de ASNs internacionais via PeeringDB + Nominatim.

Estratégia (decrescente de confiança):
  1. /api/org do PeeringDB tem latitude/longitude  → geo_confidence: "org_coords"
  2. /api/org tem city + country → Nominatim        → geo_confidence: "city_centroid"
  3. Sem dados                                      → geo_confidence: "unknown"

Fluxo:
  a. Coleta ASNs não-BR dos documentos publicados e dos ixbr_members.json
  b. Consulta /api/net em lotes para obter org_id de cada ASN
  c. Consulta /api/org em lotes para obter coordenadas / cidade de cada org
  d. Geocodifica via Nominatim quando lat/lon ausente
  e. Escreve geo_intl_asns.json.gz

Cache:
  data/normalized/geo_cache/peeringdb_intl.json.gz  — keyed por ASN
  data/normalized/geo_cache/peeringdb_intl_nom.json.gz — keyed por "city|country"

Uso:
    python -m sources.peeringdb_intl_geo.enrich --date 2026-06-12
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    published_path,
    read_json_gz,
    today_str,
    write_json_gz,
)
from core.site import USER_AGENT

PDB_BASE        = "https://www.peeringdb.com/api"
NOMINATIM_URL   = "https://nominatim.openstreetmap.org/search"
NOMINATIM_DELAY = 1.1
BATCH_SIZE      = 500

CACHE_VERSION = "1"


def _user_agent() -> str:
    return os.environ.get("NOMINATIM_USER_AGENT", USER_AGENT)


def _pdb_client() -> httpx.Client:
    api_key = os.environ.get("PEERINGDB_API_KEY", "")
    headers = {"User-Agent": USER_AGENT}
    if api_key:
        headers["Authorization"] = f"Api-Key {api_key}"
    return httpx.Client(headers=headers, timeout=30, follow_redirects=True)


def _collect_intl_asns(base: Path, date_str: str, br_asns: set[int]) -> set[int]:
    """Coleta todos os ASNs não-BR referenciados nos IXPs do snapshot."""
    intl: set[int] = set()

    ixp_dir = published_path(base, date_str, "ixps")
    if ixp_dir.exists():
        for f in ixp_dir.glob("*.json"):
            if f.name == "index.json":
                continue
            try:
                doc = json.loads(f.read_bytes())
            except Exception:
                continue
            for afi in ("v4", "v6"):
                for asn in (doc.get(afi) or {}).get("asn_direct") or []:
                    if int(asn) not in br_asns:
                        intl.add(int(asn))

    raw_date_dir = base / "raw" / date_str
    if raw_date_dir.exists():
        for ixp_dir_raw in raw_date_dir.iterdir():
            if not ixp_dir_raw.is_dir():
                continue
            members_file = ixp_dir_raw / "ixbr_members.json"
            if not members_file.exists():
                continue
            try:
                data = json.loads(members_file.read_bytes())
                for m in data.get("members") or []:
                    asn = m.get("asn")
                    if asn and int(asn) not in br_asns:
                        intl.add(int(asn))
            except Exception:
                continue

    return intl


def _fetch_batch(client: httpx.Client, url: str, param: str,
                 ids: list, log) -> list[dict]:
    """Consulta PeeringDB com ?{param}__in=... Retenta em 429."""
    params = {f"{param}__in": ",".join(str(i) for i in ids), "depth": 0, "status": "ok"}
    for attempt in range(2):
        try:
            resp = client.get(url, params=params)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 65))
                log.warning("peeringdb rate limited", wait=wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json().get("data", [])
        except Exception as exc:
            log.warning("peeringdb batch failed", url=url, error=str(exc))
            return []
    return []


def _nominatim_intl(city: str, country: str, client: httpx.Client) -> dict | None:
    if not city:
        return None
    try:
        r = client.get(
            NOMINATIM_URL,
            params={"city": city, "country": country, "format": "jsonv2", "limit": 1},
            timeout=15,
        )
        r.raise_for_status()
        results = r.json()
        return results[0] if results else None
    except Exception:
        return None


def _cache_path(base: Path) -> Path:
    return base / "normalized" / "geo_cache" / "peeringdb_intl.json.gz"


def _nom_cache_path(base: Path) -> Path:
    return base / "normalized" / "geo_cache" / "peeringdb_intl_nom.json.gz"


def _load_cache(base: Path) -> dict:
    p = _cache_path(base)
    return read_json_gz(p) if p.exists() else {}


def _load_nom_cache(base: Path) -> dict:
    p = _nom_cache_path(base)
    return read_json_gz(p) if p.exists() else {}


def run(date_str: str, base: Path, force: bool, log) -> dict:
    norm_dir = normalized_path(base, date_str, "summary")

    lacnic_path = norm_dir / "lacnic_delegated.json.gz"
    br_asns: set[int] = set()
    if lacnic_path.exists():
        br_asns = set(read_json_gz(lacnic_path).get("br_asns", []))

    intl_asns = _collect_intl_asns(base, date_str, br_asns)
    log.info("intl asns collected", total=len(intl_asns))

    if not intl_asns:
        output = {"snapshot_date": date_str, "generated_at": now_iso(),
                  "total": 0, "geolocated": 0, "asns": {}}
        write_json_gz(norm_dir / "geo_intl_asns.json.gz", output)
        return output

    asn_cache = {} if force else _load_cache(base)
    nom_cache: dict[str, dict | None] = {} if force else _load_nom_cache(base)

    # ---- Step 1: query /api/net for org_id ----
    uncached_asns = [
        a for a in sorted(intl_asns)
        if force or str(a) not in asn_cache
            or asn_cache[str(a)].get("cache_version") != CACHE_VERSION
    ]
    log.info("querying peeringdb net", uncached=len(uncached_asns))

    # asn → {name, org_id}
    net_map: dict[int, dict] = {}
    with _pdb_client() as client:
        for i in range(0, len(uncached_asns), BATCH_SIZE):
            batch = uncached_asns[i : i + BATCH_SIZE]
            records = _fetch_batch(client, f"{PDB_BASE}/net", "asn", batch, log)
            for rec in records:
                asn = rec.get("asn")
                if asn:
                    net_map[int(asn)] = {
                        "name":   rec.get("name") or "",
                        "org_id": rec.get("org_id"),
                    }
            log.info("net batch done", offset=i, fetched=len(records), mapped=len(net_map))
            time.sleep(0.5)

    # ---- Step 2: query /api/org for city / lat / lon ----
    org_ids = list({d["org_id"] for d in net_map.values() if d.get("org_id")})
    log.info("querying peeringdb orgs", unique_orgs=len(org_ids))

    org_map: dict[int, dict] = {}
    with _pdb_client() as client:
        for i in range(0, len(org_ids), BATCH_SIZE):
            batch = org_ids[i : i + BATCH_SIZE]
            records = _fetch_batch(client, f"{PDB_BASE}/org", "id", batch, log)
            for rec in records:
                org_id = rec.get("id")
                if org_id:
                    org_map[int(org_id)] = {
                        "city":    rec.get("city") or "",
                        "country": rec.get("country") or "",
                        "lat":     rec.get("latitude"),
                        "lon":     rec.get("longitude"),
                    }
            log.info("org batch done", offset=i, fetched=len(records), mapped=len(org_map))
            time.sleep(0.5)

    # ---- Step 3: geocode via Nominatim where lat/lon missing ----
    ua = _user_agent()
    with httpx.Client(headers={"User-Agent": ua}, follow_redirects=True) as nom_client:
        for asn in uncached_asns:
            net_info = net_map.get(asn)
            if not net_info:
                asn_cache[str(asn)] = {"lat": None, "lon": None,
                                        "geo_confidence": "unknown", "geo_source": None,
                                        "cache_version": CACHE_VERSION}
                continue

            org = org_map.get(net_info.get("org_id")) if net_info.get("org_id") else None
            name    = net_info.get("name") or ""
            city    = (org or {}).get("city") or ""
            country = (org or {}).get("country") or ""
            lat     = (org or {}).get("lat")
            lon     = (org or {}).get("lon")

            if lat is not None and lon is not None:
                entry = {
                    "name": name, "city": city, "country": country,
                    "lat": float(lat), "lon": float(lon),
                    "geo_source": "peeringdb", "geo_confidence": "org_coords",
                    "cache_version": CACHE_VERSION, "cached_at": now_iso(),
                }
            elif city:
                nom_key = f"{city.lower().strip()}|{country.lower().strip()}"
                if nom_key not in nom_cache:
                    time.sleep(NOMINATIM_DELAY)
                    result = _nominatim_intl(city, country, nom_client)
                    nom_cache[nom_key] = result
                result = nom_cache[nom_key]
                if result:
                    entry = {
                        "name": name, "city": city, "country": country,
                        "lat": float(result["lat"]), "lon": float(result["lon"]),
                        "geo_source": "peeringdb", "geo_confidence": "city_centroid",
                        "cache_version": CACHE_VERSION, "cached_at": now_iso(),
                    }
                else:
                    entry = {
                        "name": name, "city": city, "country": country,
                        "lat": None, "lon": None,
                        "geo_source": "peeringdb", "geo_confidence": "unknown",
                        "cache_version": CACHE_VERSION, "cached_at": now_iso(),
                    }
            else:
                entry = {
                    "name": name, "city": city, "country": country,
                    "lat": None, "lon": None,
                    "geo_source": "peeringdb", "geo_confidence": "unknown",
                    "cache_version": CACHE_VERSION, "cached_at": now_iso(),
                }

            asn_cache[str(asn)] = entry

    write_json_gz(_cache_path(base), asn_cache)
    write_json_gz(_nom_cache_path(base), nom_cache)

    # ---- Assemble output ----
    results: dict[str, dict] = {}
    geolocated = 0
    for asn in sorted(intl_asns):
        entry = asn_cache.get(str(asn), {
            "lat": None, "lon": None, "geo_confidence": "unknown", "geo_source": None,
        })
        results[str(asn)] = entry
        if entry.get("lat") is not None:
            geolocated += 1

    output = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "total": len(results),
        "geolocated": geolocated,
        "asns": results,
    }
    write_json_gz(norm_dir / "geo_intl_asns.json.gz", output)
    log.info("geo_intl_asns saved", path=str(norm_dir / "geo_intl_asns.json.gz"),
             total=len(results), geolocated=geolocated)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Geolocalização de ASNs internacionais")
    parser.add_argument("--date", default=today_str())
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, force=args.force, log=log)
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
