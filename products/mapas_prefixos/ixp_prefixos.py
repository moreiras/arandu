# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Camadas de prefixos dos PTTs no mapa, pré-calculadas: `maps/ixp_prefixes/{ptt}-{v4|v6}.json.gz`.

O passo `mapas_geo` gera junto dos demais mapas. Para snapshots já publicados (aditivo, como o `.col`):

    python -m products.mapas_prefixos.ixp_prefixos --date 2026-11-15 [--date ...] [--ixp sp ...] [--force]

Lê `normalized/{data}/{ptt}/routes-{afi}.json.gz` (ou o `prefix-set`, sem os ASes) e a base DB-IP mais recente em `raw/dbip/`.
Sem `--force` não sobrescreve. Não toca no manifesto: o arquivo é derivado e a API calcula na hora se ele faltar."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from core import ixp_geo
from core.common import codigo_valido, configure_logging, data_dir, normalized_path, published_path
from core.jsonio import carregar_json_gz


def _ptts(base: Path, date_str: str) -> list[str]:
    """PTTs da data com rotas ou conjunto de prefixos no normalized. `summary` tem as rotas de todos juntos e não é PTT."""
    norm = normalized_path(base, date_str)
    if not norm.is_dir():
        return []
    return sorted(d.name for d in norm.iterdir()
                  if d.is_dir() and codigo_valido(d.name) and d.name != "summary"
                  and any((d / f"{n}-{afi}.json.gz").exists() for n in ("routes", "prefix-set") for afi in ixp_geo.FAMILIAS))


def _abrir_base(base: Path, log):
    mmdb = ixp_geo.arquivo_mmdb(base)
    if mmdb is None:
        log.warning("ixp_prefixes: sem base de geolocalização em raw/dbip nem raw/geolite2")
        return None, None
    try:
        import maxminddb
        return maxminddb.open_database(str(mmdb)), mmdb
    except Exception as exc:  # noqa: BLE001 — base corrompida ou biblioteca ausente: a API segue calculando na hora
        log.warning("ixp_prefixes: base de geolocalização não abriu", mmdb=str(mmdb), erro=str(exc))
        return None, None


def publicar(base: Path, date_str: str, log, force: bool = True, codigos: list[str] | None = None) -> int:
    """Grava as camadas de todos os PTTs da data (ou de `codigos`). Devolve o número de arquivos gravados."""
    if not published_path(base, date_str).is_dir():
        log.warning("ixp_prefixes: snapshot não publicado", date=date_str)
        return 0
    reader, mmdb = _abrir_base(base, log)
    if reader is None:
        return 0
    memo: dict = {}                                     # bloco → geo, compartilhado: os PTTs grandes repetem quase toda a tabela
    gravados = 0
    try:
        for code in codigos or _ptts(base, date_str):
            norm = normalized_path(base, date_str, code)
            for afi in ixp_geo.FAMILIAS:
                destino = ixp_geo.caminho(base, date_str, code, afi)
                if destino is None or (destino.exists() and not force):
                    continue
                t0 = time.monotonic()
                rs = ixp_geo.rotas(carregar_json_gz(norm / f"routes-{afi}.json.gz"))
                if rs:
                    info = ixp_geo.prefixos_das_rotas(rs)
                else:
                    pset = carregar_json_gz(norm / f"prefix-set-{afi}.json.gz") or []
                    info = {p: {"origin_asns": set(), "peer_asns": set()} for p in pset if isinstance(p, str)}
                if not info:
                    continue
                fc = ixp_geo.geolocalizar(info, reader, afi, memo)
                ixp_geo.gravar(destino, fc, {"snapshot_date": date_str, "ixp_code": code, "afi": afi,
                                             "routes": len(rs), "prefixes": len(info), "mmdb": mmdb.name})
                gravados += 1
                log.info("ixp_prefixes written", date=date_str, ixp=code, afi=afi, prefixes=len(info),
                         features=len(fc["features"]), segundos=round(time.monotonic() - t0, 1))
    finally:
        reader.close()
    return gravados


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Gera maps/ixp_prefixes/ de snapshots publicados")
    p.add_argument("--date", action="append", required=True)
    p.add_argument("--ixp", action="append", help="só estes PTTs (padrão: todos os da data)")
    p.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    log = configure_logging()
    base = data_dir()
    rc = 0
    for d in a.date:
        if not normalized_path(base, d).is_dir():
            log.warning("ixp_prefixes: sem normalized da data", date=d)
            rc = 1
            continue
        n = publicar(base, d, log, force=a.force, codigos=a.ixp)
        log.info("ixp_prefixes: data concluída", date=d, arquivos=n)
    return rc


if __name__ == "__main__":
    sys.exit(main())
