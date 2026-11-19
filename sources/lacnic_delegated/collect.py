# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`lacnic_delegated` — Download e parser do delegated-lacnic-extended-latest.

Extrai os ASNs alocados pelo LACNIC ao Brasil (country=BR).
Esta é a fonte autoritativa para "quais ASNs são brasileiros" —
distinta do nicbr-asn-blk-latest.txt, que mapeia ASNs → prefixos IP
e inclui ASNs estrangeiros que receberam blocos BR (ex: Cogent AS 174).

Fonte:       https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-extended-latest
Raw:         data/raw/{date}/summary/delegated-lacnic-extended-{date}.txt
Normalizado: data/normalized/{date}/summary/lacnic_delegated.json.gz

Uso:
    python -m sources.lacnic_delegated.collect
    python -m sources.lacnic_delegated.collect --date 2026-06-01
"""

from __future__ import annotations

import argparse
import hashlib
import sys

import httpx

from core.common import (
    configure_logging,
    data_dir,
    now_iso,
    normalized_path,
    raw_path,
    today_str,
    write_json_gz,
    gravar_texto_gz,
)

SOURCE_URL = (
    "https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-extended-latest"
)


def parse_text(text: str) -> list[int]:
    """
    Extrai ASNs alocados ao Brasil.
    Formato relevante: lacnic|BR|asn|{num}|1|{date}|allocated|{id}
    Inclui 'assigned' além de 'allocated' para capturar transferências.
    """
    asns: list[int] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 7:
            continue
        # rir | country | type | start | value | date | status [| opaque-id]
        if parts[0] != "lacnic":
            continue
        if parts[1] != "BR":
            continue
        if parts[2] != "asn":
            continue
        status = parts[6]
        if status not in ("allocated", "assigned"):
            continue
        try:
            asns.append(int(parts[3]))
        except ValueError:
            pass
    return sorted(asns)


def run(date_str: str, base, log) -> dict:
    raw_dir = raw_path(base, date_str, "summary")
    norm_dir = normalized_path(base, date_str, "summary")
    raw_dir.mkdir(parents=True, exist_ok=True)
    norm_dir.mkdir(parents=True, exist_ok=True)

    raw_file = raw_dir / f"delegated-lacnic-extended-{date_str}.txt.gz"
    norm_file = norm_dir / "lacnic_delegated.json.gz"

    log.info("downloading", url=SOURCE_URL)
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        response = client.get(SOURCE_URL)
        response.raise_for_status()

    raw_text = response.text
    sha256 = hashlib.sha256(raw_text.encode()).hexdigest()

    gravar_texto_gz(raw_file, raw_text)
    log.info("raw saved", path=str(raw_file), bytes=len(raw_text), sha256=sha256[:16] + "...")

    br_asns = parse_text(raw_text)
    log.info("parsed", total_br_asns=len(br_asns))

    normalized = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "source_url": SOURCE_URL,
        "source_sha256": sha256,
        "total_br_asns": len(br_asns),
        # Lista ordenada de ASNs alocados pelo LACNIC ao Brasil
        "br_asns": br_asns,
    }

    write_json_gz(norm_file, normalized)
    log.info("normalized saved", path=str(norm_file))

    return normalized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="`lacnic_delegated` — download delegated-lacnic-extended-latest e extrai ASNs BR"
    )
    parser.add_argument(
        "--date",
        default=today_str(),
        help="Data do snapshot (YYYY-MM-DD); padrão: hoje",
    )
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, log=log)
    except httpx.HTTPStatusError as exc:
        log.error("download failed", status=exc.response.status_code, url=SOURCE_URL)
        return 1
    except httpx.RequestError as exc:
        log.error("connection failed", error=str(exc), url=SOURCE_URL)
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
