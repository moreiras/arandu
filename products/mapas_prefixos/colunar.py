# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Gera `maps/global_prefixes.col` para snapshots já publicados (aditivo; o pipeline novo já gera junto do GeoJSON).

    python -m products.mapas_prefixos.colunar --date 2026-10-25 [--date 2026-10-24 ...]

Lê o `global_prefixes.geojson` do snapshot (uns 100 MB → cerca de 1 GB de memória enquanto roda) e escreve o `.col` ao lado.
Idempotente; sem `--force` não sobrescreve. Não toca no manifesto: o arquivo é derivado e a API cai no GeoJSON se ele faltar."""
from __future__ import annotations

import argparse
import json
import sys

from core.common import configure_logging, data_dir, published_path
from products.mapas_prefixos.build import escrever_global_prefixes_colunar


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Gera maps/global_prefixes.col de snapshots publicados")
    p.add_argument("--date", action="append", required=True)
    p.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    log = configure_logging()
    rc = 0
    for d in a.date:
        maps = published_path(data_dir(), d, "maps")
        origem, destino = maps / "global_prefixes.geojson", maps / "global_prefixes.col"
        if not origem.exists():
            log.warning("sem global_prefixes.geojson", date=d)
            rc = 1
            continue
        if destino.exists() and not a.force:
            log.info("já existe", date=d)
            continue
        features = json.loads(origem.read_text(encoding="utf-8")).get("features", [])
        n = escrever_global_prefixes_colunar(features, destino)
        log.info("global_prefixes.col written", date=d, rows=n, bytes=destino.stat().st_size)
    return rc


if __name__ == "__main__":
    sys.exit(main())
