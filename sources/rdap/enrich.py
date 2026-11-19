# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`rdap` — Extrai dados de organizações do Registro.br

Não faz consultas externas. Lê o snapshot do `registro_br` (registro_br.json.gz)
e produz um mapeamento compacto {asn: {name, cnpj}} para uso pelo `cnpj_geo`.

Entrada:  normalized/{date}/summary/registro_br.json.gz
Saída:    normalized/{date}/summary/orgs.json.gz

Uso:
    python -m sources.rdap.enrich --date 2026-06-12
"""

from __future__ import annotations

import argparse
import sys

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    now_iso,
    read_json_gz,
    today_str,
    write_json_gz,
)


def run(date_str: str, base, log) -> dict:
    src = normalized_path(base, date_str, "summary", "registro_br.json.gz")
    dst = normalized_path(base, date_str, "summary", "orgs.json.gz")

    if not src.exists():
        raise FileNotFoundError(f"registro_br.json.gz não encontrado: {src}")

    registro = read_json_gz(src)
    asns = registro.get("asns", [])

    orgs = {
        str(r["asn"]): {"name": r["name"], "cnpj": r["cnpj"]}
        for r in asns
    }

    output = {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "total": len(orgs),
        "with_cnpj": sum(1 for v in orgs.values() if v["cnpj"]),
        "orgs": orgs,
    }

    write_json_gz(dst, output)
    log.info(
        "orgs extracted",
        total=output["total"],
        with_cnpj=output["with_cnpj"],
        path=str(dst),
    )
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="`rdap` — extrai orgs do Registro.br")
    parser.add_argument("--date", default=today_str())
    args = parser.parse_args(argv)

    log = configure_logging()
    base = data_dir()

    try:
        run(date_str=args.date, base=base, log=log)
    except FileNotFoundError as e:
        log.error("input not found", error=str(e))
        return 1
    except Exception:
        log.exception("unexpected error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
