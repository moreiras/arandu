# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Anatel: compromissos do FUST.

Fonte:       https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acompanhamento_e_controle/fust.zip (dados abertos; ~1 MB, CSV de ~9,5 MB dentro)
Bruto:       data/raw/{date}/summary/fust-{date}.zip (o arquivo original, sem alteração)
Normalizado: data/normalized/{date}/summary/anatel_fust.json.gz   {compromissos: [...], resumo, data_arquivo, sha256, ...}
O zip traz 3 CSVs (a base do FUST e duas do ônus contratual); só `Base_FUST.csv` é lido.

Uso:
    python -m sources.anatel_fust.collect --date 2026-11-02
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path
from typing import Optional

import httpx

from core import fust
from core.common import configure_logging, data_dir, normalized_path, now_iso, raw_path, today_str, write_json_gz
from core.site import USER_AGENT

URL = "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acompanhamento_e_controle/fust.zip"
HEADERS = {"User-Agent": USER_AGENT}
ARQUIVO = "Base_FUST.csv"
MINIMO_COMPROMISSOS = 10000                             # hoje ~21,6 mil; bem menos que isso é arquivo truncado ou outro layout
MAX_SEM_IBGE = 0.02


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
            raise RuntimeError(f"anatel_fust: {ARQUIVO} ausente do zip ({z.namelist()})")
        with z.open(ARQUIVO) as f:
            return fust.consolidar(f)


def run(date_str: str, base: Path, log, client: Optional[httpx.Client] = None) -> dict:
    bruto = raw_path(base, date_str, "summary")
    bruto.mkdir(parents=True, exist_ok=True)
    destino_zip = bruto / f"fust-{date_str}.zip"
    tmp = destino_zip.with_suffix(".zip.tmp")
    meta = baixar(tmp, client)
    tmp.replace(destino_zip)
    compromissos, resumo = processar(destino_zip)
    if resumo["compromissos"] < MINIMO_COMPROMISSOS:
        raise RuntimeError(f"anatel_fust: só {resumo['compromissos']} compromissos (esperado ≥ {MINIMO_COMPROMISSOS}); arquivo truncado?")
    if resumo["sem_ibge"] > MAX_SEM_IBGE * resumo["compromissos"]:
        raise RuntimeError(f"anatel_fust: {resumo['sem_ibge']} compromissos sem município em {resumo['compromissos']}")
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "anatel_fust.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "fonte": "Anatel, dados abertos (FUST)", "url": URL,
        "data_arquivo": meta["last_modified"], "sha256": meta["sha256"], "resumo": resumo, "compromissos": compromissos})
    log.info("anatel_fust written", **{k: v for k, v in resumo.items() if k != "status"})
    return resumo


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Compromissos do FUST (Anatel, dados abertos)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log))
    except Exception:
        log.exception("falha na coleta de anatel_fust")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
