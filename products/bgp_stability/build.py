# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Análise de estabilidade BGP — enriquece e publica os dados coletados por
sources/bgp_updates_routeviews/collect.py.

Input:
  normalized/{date}/summary/bgp_stability.json.gz   — saída bruta do collector

Output:
  published/{date}/bgp_stability.json               — dados prontos para a API

Uso:
  python -m products.bgp_stability.build
  python -m products.bgp_stability.build --date 2026-06-28
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    published_path,
    read_json_gz,
    today_str,
)


def _load_asn_names(pub: Path, log) -> dict[int, str]:
    index_path = pub / "asns" / "index.json"
    if not index_path.exists():
        return {}
    try:
        with index_path.open(encoding="utf-8") as f:
            data = json.load(f)
        return {a["asn"]: a.get("name", "") for a in data if isinstance(a, dict) and "asn" in a}
    except Exception as exc:
        log.warning("falha ao carregar nomes de ASN", error=str(exc))
        return {}


def run(date_str: str, base: Path, log) -> bool:
    norm = normalized_path(base, date_str, "summary")
    pub  = published_path(base, date_str)

    src = norm / "bgp_stability.json.gz"
    if not src.exists():
        log.error("bgp_stability.json.gz não encontrado — execute primeiro o collector",
                  path=str(src))
        return False

    log.info("carregando bgp_stability.json.gz", date=date_str)
    try:
        data = read_json_gz(src)
    except Exception as exc:
        log.error("falha ao ler bgp_stability.json.gz", error=str(exc))
        return False

    # Enriquecer com nomes de ASN
    asn_names = _load_asn_names(pub, log)
    log.info("nomes de ASN carregados", count=len(asn_names))

    for entry in data.get("as_stability", []):
        entry["name"] = asn_names.get(entry["asn"], "")

    # Adicionar timestamp de publicação
    data["published_at"] = now_iso()

    # Gravar JSON publicado (sem gzip — servido diretamente pela API)
    pub.mkdir(parents=True, exist_ok=True)
    out_path = pub / "bgp_stability.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=None)

    asns = len(data.get("as_stability", []))
    log.info("bgp_stability.json publicado", path=str(out_path), asns=asns)
    return True


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Publica análise de estabilidade BGP em published/{date}/bgp_stability.json"
    )
    p.add_argument("--date",      default=today_str())
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)

    log  = configure_logging(args.log_level)
    base = data_dir()

    ok = run(args.date, base, log)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
