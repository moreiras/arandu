# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Script de teste: baixa apenas o routeviews3 (v4) e grava br-routes-v4.json.gz
no snapshot especificado, sem tocar nos outros arquivos normalizados.

Uso:
    python scripts/fetch_br_routes_one_collector.py [--date YYYY-MM-DD]

Útil para testar a Fase 2 da análise BGP (AS_PATH + communities) sem precisar
executar o pipeline completo de todos os coletores (~800 MB).
"""

from __future__ import annotations

import argparse
import datetime
import sys
import tempfile
from pathlib import Path

# Garante que o root do repo está no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    read_json_gz,
    today_str,
    write_json_gz,
)
from sources.fulltable_routeviews.collect import (
    _download,
    _find_rib_url_rv,
    _parse_mrt,
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Baixa routeviews3 (v4) e grava br-routes-v4.json.gz no snapshot"
    )
    p.add_argument("--date", default=today_str(),
                   help="data do snapshot (YYYY-MM-DD, padrão: hoje)")
    p.add_argument("--force", action="store_true",
                   help="sobrescreve br-routes-v4.json.gz mesmo se já existir")
    args = p.parse_args(argv)

    log  = configure_logging()
    base = data_dir()

    norm_dir  = normalized_path(base, args.date, "summary")
    out_path  = norm_dir / "br-routes-v4.json.gz"

    if not args.force and out_path.exists():
        log.info("br-routes-v4.json.gz já existe — use --force para sobrescrever",
                 path=str(out_path))
        return 0

    # Carrega br_asns do Registro.br
    reg_path = norm_dir / "registro_br.json.gz"
    if not reg_path.exists():
        log.error("registro_br.json.gz não encontrado — rode a coleta registro_br primeiro",
                  path=str(reg_path))
        return 1

    registro_br = read_json_gz(reg_path)
    br_asns = {a["asn"] for a in registro_br.get("asns", [])}
    log.info("br_asns carregados", count=len(br_asns))

    # Descobre URL do dump mais recente do routeviews3
    target = datetime.date.fromisoformat(args.date)
    url = _find_rib_url_rv("route-views3", target, log)
    if not url:
        log.error("nenhum dump routeviews3 encontrado para a data", date=args.date)
        return 1

    # Baixa, parseia e grava br-routes
    with tempfile.TemporaryDirectory(prefix="arandurape_rv3_") as tmpdir:
        tmp  = Path(tmpdir)
        ext  = ".gz" if url.endswith(".gz") else ".bz2"
        dest = tmp / f"rib_v4_route-views3{ext}"

        ok = _download(url, dest, log)
        if not ok:
            log.error("download falhou")
            return 1

        log.info("parseando MRT", file=str(dest))
        routes, _adj = _parse_mrt(dest, "v4", log, br_asns=br_asns)
        dest.unlink(missing_ok=True)

    if not routes:
        log.error("nenhuma rota extraída do dump")
        return 1

    # Filtra apenas rotas BR e grava br-routes
    br_routes = []
    for r in routes:
        asp = r.get("aspath", [])
        if asp and asp[-1] in br_asns:
            entry: dict = {"p": r["prefix"], "a": asp}
            if r.get("communities"):
                entry["c"] = r["communities"]
            if r.get("large_communities"):
                entry["lc"] = r["large_communities"]
            br_routes.append(entry)

    log.info("br-routes filtrados", total_routes=len(routes), br_routes=len(br_routes))

    norm_dir.mkdir(parents=True, exist_ok=True)
    write_json_gz(out_path, br_routes)
    log.info("br-routes-v4.json.gz gravado", path=str(out_path), count=len(br_routes))

    return 0


if __name__ == "__main__":
    sys.exit(main())
