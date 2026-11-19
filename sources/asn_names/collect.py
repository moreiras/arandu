# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
`asn_names` — Coleta de nomes de ASNs (bulk global)

Baixa o arquivo compilado pelo RIPE NCC a partir dos dados WHOIS dos cinco RIRs.
Cobre virtualmente todos os ASNs globalmente alocados (~121k entradas).

Fonte:       https://ftp.ripe.net/ripe/asnames/asn.txt
             Mantido pelo RIPE NCC; atualizado diariamente.
Normalizado: normalized/{date}/summary/asn_names.json.gz
             Dicionário {"str(asn)": "nome"} — chaves string para compatibilidade JSON.

Uso no pipeline:
    Os documentos de ASN (`products/ixp_metrics/documentos_asn.py`) usam este arquivo para enriquecer nomes de ASNs não-BR
    que aparecem como upstreams/downstreams nos AS_PATHs dos LGs do IX.br.
    Sem este módulo, esses ASNs ficam sem nome na interface.

Uso:
    python -m sources.asn_names.collect
    python -m sources.asn_names.collect --date 2026-06-01
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path

import httpx

from core.common import (
    configure_logging,
    data_dir,
    normalized_path,
    raw_path,
    today_str,
)

# RIPE NCC — arquivo compilado com nomes de ASNs de todos os RIRs (~121k entradas)
# Formato de cada linha: "{asn_number} {nome_completo}"
# Ex: "1 LVLT-1 - Level 3 Parent, LLC, US"
URL = "https://ftp.ripe.net/ripe/asnames/asn.txt"

_LINE_RE = re.compile(r"^(\d+)\s+(.+)$")


def fetch_text(log) -> str:
    """Baixa o asn.txt do RIPE NCC (texto bruto)."""
    log.info("downloading asn names", url=URL)
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        resp = client.get(URL)
        resp.raise_for_status()
    return resp.text


def parse_autnums(text: str, log) -> dict[str, str]:
    """Converte o texto do asn.txt em dicionário {str(asn): nome}.

    Chaves são strings (não int) para compatibilidade direta com JSON e
    com outros artefatos do pipeline que indexam ASNs como strings.
    """
    names: dict[str, str] = {}
    for line in text.splitlines():
        m = _LINE_RE.match(line.strip())
        if m:
            names[m.group(1)] = m.group(2).strip()

    log.info("asn names parsed", entries=len(names))
    return names


def fetch_autnums(log) -> dict[str, str]:
    return parse_autnums(fetch_text(log), log)


def run(date_str: str, base: Path) -> int:
    """Executa o download e salva o normalizado. Retorna quantidade de ASNs."""
    log = configure_logging()

    out_dir = normalized_path(base, date_str, "summary")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "asn_names.json.gz"

    text = fetch_text(log)
    # Bruto guardado (6 MB, ~1 MB comprimido): em 2026-10-11 a origem serviu um asn.txt em outro formato e, sem o
    # arquivo, não havia como provar a causa.
    raw_dir = raw_path(base, date_str, "summary")
    raw_dir.mkdir(parents=True, exist_ok=True)
    with gzip.open(raw_dir / f"asn-names-{date_str}.txt.gz", "wt", encoding="utf-8") as f:
        f.write(text)
    names = parse_autnums(text, log)

    with gzip.open(out_file, "wt", encoding="utf-8") as f:
        json.dump(names, f, ensure_ascii=False)

    log.info("asn_names written", path=str(out_file), count=len(names))
    return len(names)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="`asn_names` — Bulk ASN names via RIPE NCC asn.txt"
    )
    parser.add_argument("--date", default=today_str(),
                        help="Data do snapshot (YYYY-MM-DD); padrão: hoje")
    args = parser.parse_args(argv)

    base = data_dir()
    count = run(date_str=args.date, base=base)
    return 0 if count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
