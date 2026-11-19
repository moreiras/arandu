# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Anatel: quadro de atribuição e destinação de faixas (PDFF).

Fonte:       https://www.anatel.gov.br/dadosabertos/paineis_de_dados/espectro_e_orbita/pdff.zip (dados abertos; 225 KB)
Bruto:       data/raw/{date}/summary/pdff-{date}.zip (o arquivo original, sem alteração)
Normalizado: data/normalized/{date}/summary/anatel_pdff.json.gz
O zip traz 8 CSVs (duas versões de cada); só `Destinacao.csv` e `Atribuicao_BR.csv` são lidos.

Uso:
    python -m sources.anatel_pdff.collect --date 2026-11-02
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path
from typing import Optional

import httpx

from core import pdff
from core.common import configure_logging, data_dir, normalized_path, now_iso, raw_path, today_str, write_json_gz
from core.site import USER_AGENT

URL = "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/espectro_e_orbita/pdff.zip"
HEADERS = {"User-Agent": USER_AGENT}
ARQUIVOS = ("Destinacao.csv", "Atribuicao_BR.csv")
MINIMO_FAIXAS = 300                                       # hoje 658 faixas (início, fim) em MHz


def baixar(destino: Path, client: Optional[httpx.Client] = None) -> dict:
    proprio = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(60, read=300), follow_redirects=True, headers=HEADERS)
    h = hashlib.sha256()
    try:
        with client.stream("GET", URL) as r:
            r.raise_for_status()
            modificado = r.headers.get("last-modified")
            with open(destino, "wb") as f:
                for pedaco in r.iter_bytes(1 << 20):
                    f.write(pedaco)
                    h.update(pedaco)
    finally:
        if proprio:
            client.close()
    return {"sha256": h.hexdigest(), "last_modified": modificado}


def processar(zip_path: Path) -> tuple[list[dict], dict]:
    with zipfile.ZipFile(zip_path) as z:
        faltam = [a for a in ARQUIVOS if a not in z.namelist()]
        if faltam:
            raise RuntimeError(f"anatel_pdff: {faltam} ausente(s) do zip ({z.namelist()})")
        with z.open(ARQUIVOS[0]) as d, z.open(ARQUIVOS[1]) as a:
            return pdff.consolidar(d, a)


def run(date_str: str, base: Path, log, client: Optional[httpx.Client] = None) -> dict:
    bruto = raw_path(base, date_str, "summary")
    bruto.mkdir(parents=True, exist_ok=True)
    destino_zip = bruto / f"pdff-{date_str}.zip"
    tmp = destino_zip.with_suffix(".zip.tmp")
    meta = baixar(tmp, client)
    tmp.replace(destino_zip)
    dados, resumo = processar(destino_zip)
    if resumo["faixas"] < MINIMO_FAIXAS:
        raise RuntimeError(f"anatel_pdff: só {resumo['faixas']} faixas (esperado ≥ {MINIMO_FAIXAS}); arquivo truncado?")
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "anatel_pdff.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "fonte": "Anatel, dados abertos (PDFF)", "url": URL,
        "data_arquivo": meta["last_modified"], "sha256": meta["sha256"], "resumo": resumo, "faixas": dados})
    log.info("anatel_pdff written", **resumo)
    return resumo


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Quadro de faixas de frequência, PDFF (Anatel, dados abertos)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log))
    except Exception:
        log.exception("falha na coleta de anatel_pdff")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
