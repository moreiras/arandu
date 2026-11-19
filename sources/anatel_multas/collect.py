# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Anatel: multas constituídas (arrecadação).

Fonte:       https://www.anatel.gov.br/dadosabertos/paineis_de_dados/arrecadacao/arrecadacao.zip (dados abertos; 5 MB, CSV de ~35 MB dentro)
Bruto:       data/raw/{date}/summary/multas-{date}.zip (o arquivo original, sem alteração)
Normalizado: data/normalized/{date}/summary/anatel_multas.json.gz
O zip traz só `multas_constituidas.csv`; pessoa física (CPF mascarado na fonte) e serviços fora de SCM, SMP, STFC e SeAC são descartados e contados.

Uso:
    python -m sources.anatel_multas.collect --date 2026-11-02
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path
from typing import Optional

import httpx

from core import multas
from core.common import configure_logging, data_dir, normalized_path, now_iso, raw_path, today_str, write_json_gz
from core.site import USER_AGENT

URL = "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/arrecadacao/arrecadacao.zip"
HEADERS = {"User-Agent": USER_AGENT}
ARQUIVO = "multas_constituidas.csv"
MINIMO_EMPRESAS = 500                                   # hoje ~1,5 mil (raiz do CNPJ × grupo de serviço); bem menos é arquivo truncado ou outro layout


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
        if ARQUIVO not in z.namelist():
            raise RuntimeError(f"anatel_multas: {ARQUIVO} ausente do zip ({z.namelist()})")
        with z.open(ARQUIVO) as f:
            return multas.consolidar(f)


def run(date_str: str, base: Path, log, client: Optional[httpx.Client] = None) -> dict:
    bruto = raw_path(base, date_str, "summary")
    bruto.mkdir(parents=True, exist_ok=True)
    destino_zip = bruto / f"multas-{date_str}.zip"
    tmp = destino_zip.with_suffix(".zip.tmp")
    meta = baixar(tmp, client)
    tmp.replace(destino_zip)
    dados, resumo = processar(destino_zip)
    if resumo["empresas"] < MINIMO_EMPRESAS:
        raise RuntimeError(f"anatel_multas: só {resumo['empresas']} empresas (esperado ≥ {MINIMO_EMPRESAS}); arquivo truncado?")
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "anatel_multas.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "fonte": "Anatel, dados abertos (multas constituídas)", "url": URL,
        "data_arquivo": meta["last_modified"], "sha256": meta["sha256"], "resumo": resumo, "empresas": dados})
    log.info("anatel_multas written", **resumo)
    return resumo


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Multas constituídas da Anatel (dados abertos)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log))
    except Exception:
        log.exception("falha na coleta de anatel_multas")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
