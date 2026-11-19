# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`apnic_pop` — Estimativas de população por AS (APNIC Labs)

Coleta um único endpoint do APNIC Labs com totais e IPv6 para ASNs brasileiros:

  https://stats.labs.apnic.net/v6pop?c=BR&w=60

  Formato: HTML com tabela embutida em javascript (google.visualization)
  Colunas relevantes: Users (est.), % of country, V6 Users (est.), % of AS

Raw:
    data/raw/{date}/apnic_v6pop-{date}.html

Normalizado:
    data/normalized/{date}/summary/apnic_pop.json.gz

    Estrutura:
    {
      "date": "2026-06-08",
      "window_days": 60,
      "asns": {
        "28573": {
          "users":        20771435,  # usuários totais estimados
          "users_pct_cc": 12.66,     # percentual da população do país (BR)
          "v6_users":     16116420,  # usuários IPv6 estimados
          "v6_pct_as":    82.08      # % de usuários IPv6 dentro do AS
        }
      }
    }

Uso:
    python -m sources.apnic_pop.collect
    python -m sources.apnic_pop.collect --date 2026-06-09
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    raw_path,
    today_str,
    write_json_gz,
)
from core.site import USER_AGENT

V6POP_URL   = "https://stats.labs.apnic.net/v6pop?c=BR&w=60"
WINDOW_DAYS = 60
TIMEOUT     = 60


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def run(date_str: str, base: Path, log) -> dict:
    raw_dir = raw_path(base, date_str)
    raw_dir.mkdir(parents=True, exist_ok=True)

    log.info("fetching v6pop", url=V6POP_URL)
    html = _get(V6POP_URL).decode("utf-8", errors="replace")

    out_raw = raw_dir / f"apnic_v6pop-{date_str}.html"
    out_raw.write_bytes(html.encode())

    m = re.search(r"arrayToDataTable\(\[(.*?)\]\)", html, re.DOTALL)
    if not m:
        log.error("v6pop: JS table not found in response")
        return {"asns": 0}

    rows_text = m.group(1)

    # Colunas: Rank, ASN, AS Name, CC, Users(est.), GDP×Users, %CC, %Net,
    #          V6Users(est.), %AS, %CC_V6, %Net_V6, Samples
    # Grupos:   1     2              3      4         5   6
    row_re = re.compile(
        r'\[(\d+),"(AS\d+)","(?:[^"\\]|\\.)*","(?:[^"\\]|\\.)*",'
        r'(\d+),[\d.]+,([\d.]+),[\d.]+,'
        r'(\d+),([\d.]+),'
    )

    asns: dict[str, dict] = {}
    for rm in row_re.finditer(rows_text):
        asn = int(rm.group(2)[2:])  # "AS28573" → 28573
        asns[str(asn)] = {
            "users":        int(rm.group(3)),
            "users_pct_cc": float(rm.group(4)),
            "v6_users":     int(rm.group(5)),
            "v6_pct_as":    float(rm.group(6)),
        }

    output = {
        "date":        date_str,
        "window_days": WINDOW_DAYS,
        "asns":        asns,
    }
    out_path = normalized_path(base, date_str, "summary") / "apnic_pop.json.gz"
    write_json_gz(out_path, output)
    log.info("apnic_pop saved", path=str(out_path), total_asns=len(asns))
    return {"asns": len(asns)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="`apnic_pop` — APNIC Labs population estimates per AS"
    )
    parser.add_argument("--date", default=today_str(),
                        help="Data do snapshot (YYYY-MM-DD); padrão: hoje")
    args = parser.parse_args(argv)

    log  = configure_logging()
    base = data_dir()

    try:
        result = run(args.date, base, log)
        log.info("done", **result)
        return 0
    except Exception as exc:
        log.error("apnic_pop failed", error=str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
