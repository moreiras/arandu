# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""CAIDA AS Relationships, serial-2: relações entre ASNs inferidas pelo CAIDA (AS-Rank) a partir de RIBs públicas.

Uso no Arandurapé: **prior e régua**, nunca verdade (usa os mesmos coletores que nós; concordar mede consistência, não acurácia).
Atribuição obrigatória (AUA do CAIDA): "The CAIDA AS Relationships Dataset, <período>".

Fonte:       https://publicdata.caida.org/datasets/as-relationships/serial-2/AAAAMMDD.as-rel2.txt.bz2 (mensal; usa o mais recente ≤ data)
Raw:         data/raw/{date}/summary/caida-asrel-{as_of}.txt.gz
Normalizado: data/normalized/{date}/summary/caida_asrel.json.gz   {snapshot_date, as_of, p2c: [[provedor, cliente]…], p2p: [[a, b]…], total}
Formato:     `# comentário`; `provedor|cliente|-1`; `par|par|0|fonte`

Uso:
    python -m sources.caida_asrel.collect --date 2026-10-24
"""
from __future__ import annotations

import argparse
import bz2
import re
import sys
from pathlib import Path

import httpx

from core.common import configure_logging, data_dir, gravar_texto_gz, normalized_path, now_iso, raw_path, today_str, write_json_gz
from core.site import USER_AGENT

URL = "https://publicdata.caida.org/datasets/as-relationships/serial-2/"
HEADERS = {"User-Agent": USER_AGENT}
_ARQUIVO = re.compile(r"(\d{8})\.as-rel2\.txt\.bz2")


def escolher_arquivo(listagem: str, ate: str) -> str | None:
    """Nome do arquivo mensal mais recente cuja data (AAAAMMDD) é ≤ `ate` (AAAA-MM-DD)."""
    alvo = ate.replace("-", "")
    datas = sorted({m.group(1) for m in _ARQUIVO.finditer(listagem) if m.group(1) <= alvo})
    return f"{datas[-1]}.as-rel2.txt.bz2" if datas else None


def parse_asrel(texto: str) -> dict:
    """`{p2c: [[provedor, cliente]…], p2p: [[a, b]…]}`; linhas malformadas são contadas em `ignoradas`."""
    p2c: list[list[int]] = []
    p2p: list[list[int]] = []
    ignoradas = 0
    for linha in texto.splitlines():
        if not linha or linha.startswith("#"):
            continue
        campos = linha.split("|")
        try:
            a, b, tipo = int(campos[0]), int(campos[1]), int(campos[2])
        except (ValueError, IndexError):
            ignoradas += 1
            continue
        if tipo == -1:
            p2c.append([a, b])
        elif tipo == 0:
            p2p.append([min(a, b), max(a, b)])
        else:
            ignoradas += 1
    return {"p2c": p2c, "p2p": p2p, "ignoradas": ignoradas}


def run(date_str: str, base: Path, log) -> dict:
    with httpx.Client(timeout=120, follow_redirects=True, headers=HEADERS) as client:
        lista = client.get(URL)
        lista.raise_for_status()
        nome = escolher_arquivo(lista.text, date_str)
        if nome is None:
            raise RuntimeError(f"caida_asrel: nenhum arquivo ≤ {date_str} em {URL}")
        arq = client.get(URL + nome)
        arq.raise_for_status()
    texto = bz2.decompress(arq.content).decode("utf-8", errors="replace")
    as_of = nome[:8]
    as_of_iso = f"{as_of[:4]}-{as_of[4:6]}-{as_of[6:]}"
    raw_dir = raw_path(base, date_str, "summary")
    raw_dir.mkdir(parents=True, exist_ok=True)
    gravar_texto_gz(raw_dir / f"caida-asrel-{as_of}.txt.gz", texto)
    r = parse_asrel(texto)
    if not r["p2c"]:
        raise RuntimeError("caida_asrel: o arquivo veio sem relações provedor-cliente")
    saida = {"snapshot_date": date_str, "as_of": as_of_iso, "generated_at": now_iso(), "arquivo": nome,
             "total": len(r["p2c"]) + len(r["p2p"]), "ignoradas": r["ignoradas"], "p2c": r["p2c"], "p2p": r["p2p"]}
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "caida_asrel.json.gz", saida)
    log.info("caida_asrel written", as_of=as_of_iso, p2c=len(r["p2c"]), p2p=len(r["p2p"]), ignoradas=r["ignoradas"])
    return saida


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="CAIDA AS Relationships (serial-2)")
    p.add_argument("--date", default=today_str())
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        run(a.date, data_dir(), log)
    except Exception:
        log.exception("falha na coleta de caida_asrel")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
