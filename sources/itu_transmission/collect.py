# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`itu_transmission` — Coleta de enlaces terrestres (fibra/micro-ondas) da ITU BBmaps.

Fonte: ITU Transmission Networks Geocatalogue (bbmaps.itu.int), servido por um
GeoServer padrão via WFS, sem autenticação. Dado de infraestrutura física,
global, atualizado com pouca frequência pela ITU — mas coletado toda semana
junto com o resto do snapshot, a pedido, em vez de sob uma cadência própria.

Fonte:       https://bbmaps.itu.int/geoserver/itu-geocatalogue/wfs
Normalizado: data/normalized/{date}/summary/itu_transmission.json.gz

Uso:
    python -m sources.itu_transmission.collect
    python -m sources.itu_transmission.collect --date 2026-09-26

Pegadinha confirmada em levantamento manual: o filtro `bbox` do WFS 2.0 usa eixo
lat/lon (miny,minx,maxy,maxx), diferente da ordem lon/lat das coordenadas no
GeoJSON de saída. Este coletor não usa bbox (dataset é global), mas fica
documentado aqui para quem for estender.
"""

from __future__ import annotations

import argparse
import sys

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

WFS_BASE = "https://bbmaps.itu.int/geoserver/itu-geocatalogue/wfs"
LAYER = "itu-geocatalogue:trx_geocatalogue"
PAGE_SIZE = 5000


def _make_client() -> httpx.Client:
    headers = {"User-Agent": USER_AGENT}
    return httpx.Client(headers=headers, timeout=60, follow_redirects=True)


def _fetch_page(client: httpx.Client, start_index: int, log) -> dict:
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": LAYER,
        "outputFormat": "application/json",
        "count": PAGE_SIZE,
        "startIndex": start_index,
        # A camada não tem chave primária configurada no GeoServer — sem sortBy,
        # startIndex > 0 falha com "Cannot do natural order without a primary key"
        # (confirmado em teste manual). 'uid' é o campo estável usado como PK de fato.
        "sortBy": "uid",
    }
    resp = client.get(WFS_BASE, params=params)
    resp.raise_for_status()
    data = resp.json()
    log.info("page fetched", start_index=start_index,
              returned=data.get("numberReturned", 0),
              matched=data.get("numberMatched"))
    return data


def _fetch_all(client: httpx.Client, log) -> list[dict]:
    """Varre a camada inteira paginando por startIndex/count."""
    features: list[dict] = []
    start_index = 0
    total: int | None = None
    while True:
        page = _fetch_page(client, start_index, log)
        page_features = page.get("features", [])
        features.extend(page_features)
        if total is None:
            total = page.get("numberMatched")
        start_index += PAGE_SIZE
        if not page_features or (total is not None and start_index >= total):
            break
    return features


def run(date_str: str, base, log) -> dict:
    """Coleta a camada trx_geocatalogue inteira (fibra + micro-ondas, mundo todo).

    Returns:
        O dict normalizado gravado em disco: features GeoJSON simplificadas
        (geometria + type_inf, status) e contagem por status.
    """
    norm_dir = normalized_path(base, date_str, "summary")
    norm_dir.mkdir(parents=True, exist_ok=True)

    with _make_client() as client:
        raw_features = _fetch_all(client, log)

    features = []
    status_counts: dict[str, int] = {}
    for f in raw_features:
        geom = f.get("geometry")
        props = f.get("properties") or {}
        if not geom or geom.get("type") != "LineString":
            continue
        status = props.get("status", "")
        status_counts[status] = status_counts.get(status, 0) + 1
        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "type_inf": props.get("type_inf", ""),
                "status": status,
            },
        })

    normalized = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "source": "ITU BBmaps Transmission Networks Geocatalogue "
                  "(bbmaps.itu.int/geoserver/itu-geocatalogue)",
        "total": len(features),
        "status_counts": status_counts,
        "features": features,
    }
    norm_file = norm_dir / "itu_transmission.json.gz"
    write_json_gz(norm_file, normalized)

    log.info("itu_transmission done", total=len(features), status_counts=status_counts)
    return normalized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="`itu_transmission` — coleta de enlaces terrestres da ITU BBmaps"
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
