# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Grava `peers-{afi}.json.gz` para snapshots que já têm `routes-{afi}.json.gz`.

O `bgp_ixp` grava esse arquivo junto das rotas; este módulo o preenche em snapshots que não o têm, sem reparsear o bruto
(aditivo e idempotente: `--force` regrava). Uso:

    python -m products.bgp_routes.peers_stats --date 2026-10-27
"""
from __future__ import annotations

import argparse
import sys

from core.common import configure_logging, data_dir, read_json_gz, normalized_path, write_json_gz
from core.ixp_peers import estatisticas_por_peer


def preencher(date_str: str, base, log, force: bool = False) -> dict:
    raiz = normalized_path(base, date_str)
    feitos = pulados = 0
    for rotas in sorted(raiz.glob("*/routes-v[46].json.gz")):
        if rotas.parent.name == "summary":
            continue
        afi = rotas.name.split("-")[1].split(".")[0]
        destino = rotas.parent / f"peers-{afi}.json.gz"
        if destino.exists() and not force:
            pulados += 1
            continue
        dados = read_json_gz(rotas)
        write_json_gz(destino, estatisticas_por_peer((dados or {}).get("routes", []), afi))
        feitos += 1
        log.info("peers gravado", ixp=rotas.parent.name, afi=afi)
    return {"gravados": feitos, "ja_existiam": pulados}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Preenche peers-{afi}.json.gz de um snapshot")
    ap.add_argument("--date", required=True)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    r = preencher(a.date, data_dir(), configure_logging(), a.force)
    print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
