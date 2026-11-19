# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`telegeography_cables` — Coleta de cabos submarinos do TeleGeography Submarine Cable Map.

Fonte pública, sem autenticação, sob Creative Commons Attribution-ShareAlike
4.0 International (CC BY-SA 4.0) — atribuição obrigatória e mantida na UI
sempre que a camada for exibida (ver frontend/src/components/maps/mapTheme.ts).

Fonte:       https://www.submarinecablemap.com/api/v3/
Normalizado: data/normalized/{date}/summary/telegeography_cables.json.gz

Uso:
    python -m sources.telegeography_cables.collect
    python -m sources.telegeography_cables.collect --date 2026-09-26
"""

from __future__ import annotations

import argparse
import sys
import time

import httpx

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    today_str,
    write_json_gz,
)
from core.site import USER_AGENT

API_BASE = "https://www.submarinecablemap.com/api/v3"
_DETAIL_PAUSE = 0.08  # segundos entre requisições de detalhe por cabo


def _make_client() -> httpx.Client:
    headers = {"User-Agent": USER_AGENT}
    return httpx.Client(headers=headers, timeout=30, follow_redirects=True)


def _fetch_cable_detail(client: httpx.Client, cable_id: str, log) -> dict:
    """Busca metadados (owners, length, rfs) de um cabo. Retorna {} em caso de erro."""
    url = f"{API_BASE}/cable/{cable_id}.json"
    try:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        log.warning("cable detail fetch failed", cable_id=cable_id, error=str(exc))
        return {}


def run(date_str: str, base, log) -> dict:
    """Coleta cabos submarinos + pontos de aterrissagem + metadados por cabo.

    Returns:
        O dict normalizado gravado em disco: cables (geometria + metadados),
        landing_points (geometria).
    """
    norm_dir = normalized_path(base, date_str, "summary")
    norm_dir.mkdir(parents=True, exist_ok=True)

    with _make_client() as client:
        cable_geo = client.get(f"{API_BASE}/cable/cable-geo.json")
        cable_geo.raise_for_status()
        cable_features = cable_geo.json().get("features", [])
        log.info("cable-geo fetched", total=len(cable_features))

        lp_geo = client.get(f"{API_BASE}/landing-point/landing-point-geo.json")
        lp_geo.raise_for_status()
        lp_features = lp_geo.json().get("features", [])
        log.info("landing-point-geo fetched", total=len(lp_features))

        cables = []
        for feat in cable_features:
            props = feat.get("properties") or {}
            cable_id = props.get("id", "")
            detail = _fetch_cable_detail(client, cable_id, log) if cable_id else {}
            landing_countries = sorted({
                lp.get("country", "") for lp in detail.get("landing_points", [])
                if lp.get("country")
            })
            cables.append({
                "id": cable_id,
                "name": props.get("name", ""),
                "color": props.get("color", ""),
                "geometry": feat.get("geometry"),
                "length": detail.get("length", ""),
                "owners": detail.get("owners", ""),
                "suppliers": detail.get("suppliers", ""),
                "rfs_year": detail.get("rfs_year"),
                "is_planned": detail.get("is_planned"),
                "url": detail.get("url", ""),
                # Países dos landing points — usado na publicação para destacar os
                # cabos que tocam o Brasil (cor diferente no mapa).
                "landing_countries": landing_countries,
            })
            time.sleep(_DETAIL_PAUSE)

    landing_points = [
        {
            "id": (f.get("properties") or {}).get("id", ""),
            "name": (f.get("properties") or {}).get("name", ""),
            "is_tbd": (f.get("properties") or {}).get("is_tbd", False),
            "geometry": f.get("geometry"),
        }
        for f in lp_features
    ]

    normalized = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "source": "TeleGeography Submarine Cable Map (submarinecablemap.com), "
                  "CC BY-SA 4.0",
        "cables": cables,
        "landing_points": landing_points,
    }
    norm_file = norm_dir / "telegeography_cables.json.gz"
    write_json_gz(norm_file, normalized)

    log.info("telegeography_cables done",
              cables=len(cables), landing_points=len(landing_points))
    return normalized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="`telegeography_cables` — coleta de cabos submarinos do TeleGeography"
    )
    parser.add_argument("--date", default=today_str(),
                        help="Data do snapshot (YYYY-MM-DD); padrão: hoje")
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, log=log)
    except httpx.HTTPStatusError as exc:
        log.error("http error", status=exc.response.status_code, url=str(exc.request.url))
        return 1
    except httpx.RequestError as exc:
        log.error("connection error", error=str(exc))
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
