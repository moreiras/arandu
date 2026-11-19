#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Mede o rodízio do Alice sobre os normalizados já gravados: só lê arquivos, nunca consulta a rede.

Para cada data de `normalized/` (ou as pedidas), mostra a cobertura do `cobertura_rodizio` dos documentos `rs_filtered`, `rs_communities` (IX.br) e `decix_rs_rotas` (DE-CIX):
vizinhos elegíveis, lidos na rodada, herdados, sem leitura, idade máxima, requisições e segundos da rodada. Com `--por-ptt`, uma linha por PTT.

    python3 scripts/medir_rodizio_alice.py [--data-dir data] [--desde 2026-11-10] [--por-ptt]
No ambiente de teste (somente leitura, pode rodar a qualquer hora):
    docker compose --profile worker run --rm worker python scripts/medir_rodizio_alice.py --desde 2026-11-10
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

DOCS = (("ixbr_alice_rotas n2", "rs_filtered.json.gz"), ("ixbr_alice_rotas n3", "rs_communities.json.gz"), ("decix_alice n3", "decix_rs_rotas.json.gz"))


def ler(p: Path):
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return json.load(f)


def linha(nome: str, data: str, c: dict, doc: dict, ptt: str | None = None) -> str:
    cab = f"{data}  {nome:<20}" + (f" {ptt:<10}" if ptt else " total     ")
    cob = (f"elegíveis {c.get('elegiveis', 0):>5}  lidos {c.get('lidos_na_rodada', 0):>5}  herdados {c.get('herdados', 0):>5}  sem leitura {c.get('sem_leitura', 0):>5}  "
           f"idade máx {c.get('idade_max_dias')}")
    if ptt is None:
        cob += f"  req {doc.get('requisicoes_da_rodada')}/{doc.get('orcamento')}  {doc.get('segundos_da_rodada')} s" + ("  BLOQUEIO " + str(doc["bloqueio"]) if doc.get("bloqueio") else "")
    return cab + cob


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--desde", default="0000-00-00")
    ap.add_argument("--por-ptt", action="store_true")
    a = ap.parse_args(argv)
    raiz = Path(a.data_dir) / "normalized"
    if not raiz.is_dir():
        print(f"sem {raiz}", file=sys.stderr)
        return 1
    n = 0
    for d in sorted(p.name for p in raiz.iterdir() if p.is_dir() and p.name >= a.desde):
        for nome, arq in DOCS:
            p = raiz / d / "summary" / arq
            if not p.is_file():
                continue
            doc = ler(p)
            cr = doc.get("cobertura_rodizio")
            if not cr:
                print(f"{d}  {nome:<20} sem cobertura_rodizio (rodada anterior à 1.5.32)")
                continue
            print(linha(nome, d, cr.get("total") or {}, doc))
            n += 1
            if a.por_ptt:
                for ptt, c in (cr.get("por_ptt") or {}).items():
                    print(linha(nome, d, c, doc, ptt))
    if not n:
        print("nenhum documento com cobertura_rodizio encontrado", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
