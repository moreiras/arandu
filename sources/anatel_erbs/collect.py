# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Anatel: estações do SMP licenciadas (ERBs).

Fonte:       https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/estacoes_smp.zip (dados abertos; ~94 MB, CSV de ~1 GB dentro)
Bruto:       data/raw/{date}/summary/estacoes_smp-{date}.zip (o arquivo original, sem alteração)
Normalizado: data/normalized/{date}/summary/anatel_erbs.json.gz   {estacoes: [...], resumo, data_arquivo, sha256, ...}
A consolidação de 3,3 milhões de linhas em ~114 mil estações está em core/erbs.py. O arquivo da Anatel é "licenciada", não "em operação", e não traz cobertura.

Uso:
    python -m sources.anatel_erbs.collect --date 2026-11-01
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path
from typing import Optional

import httpx

from core import erbs
from core.common import configure_logging, data_dir, normalized_path, now_iso, raw_path, today_str, write_json_gz
from core.site import USER_AGENT

URL = "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/estacoes_smp.zip"
HEADERS = {"User-Agent": USER_AGENT}
MINIMO_ESTACOES = 50000                               # hoje 114 mil; bem menos que isso é arquivo truncado ou outro layout
MAX_SEM_POSICAO = 0.02                                # fração de estações sem posição válida acima da qual a coleta falha


def baixar(destino: Path, client: Optional[httpx.Client] = None) -> dict:
    proprio = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(60, read=600), follow_redirects=True, headers=HEADERS)
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
        nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if len(nomes) != 1:
            raise RuntimeError(f"anatel_erbs: esperava 1 CSV no zip, achei {nomes}")
        with z.open(nomes[0]) as f:
            return erbs.consolidar(f)


def run(date_str: str, base: Path, log, client: Optional[httpx.Client] = None) -> dict:
    bruto = raw_path(base, date_str, "summary")
    bruto.mkdir(parents=True, exist_ok=True)
    destino_zip = bruto / f"estacoes_smp-{date_str}.zip"
    tmp = destino_zip.with_suffix(".zip.tmp")
    meta = baixar(tmp, client)
    tmp.replace(destino_zip)
    estacoes, resumo = processar(destino_zip)
    if resumo["estacoes"] < MINIMO_ESTACOES:
        raise RuntimeError(f"anatel_erbs: só {resumo['estacoes']} estações (esperado ≥ {MINIMO_ESTACOES}); arquivo truncado?")
    ruins = resumo["sem_posicao"] + resumo["fora_do_brasil"]
    if ruins > MAX_SEM_POSICAO * resumo["estacoes"]:
        raise RuntimeError(f"anatel_erbs: {ruins} estações sem posição válida em {resumo['estacoes']}")
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "anatel_erbs.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "fonte": "Anatel, dados abertos (estações do SMP licenciadas)", "url": URL,
        "data_arquivo": meta["last_modified"], "sha256": meta["sha256"], "resumo": resumo, "estacoes": estacoes})
    log.info("anatel_erbs written", estacoes=resumo["estacoes"], linhas=resumo["linhas"], sem_posicao=resumo["sem_posicao"], sem_ibge=resumo["sem_ibge"])
    return {k: v for k, v in resumo.items() if k != "cnpj_da_marca"}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Estações do SMP licenciadas (Anatel, dados abertos)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log))
    except Exception:
        log.exception("falha na coleta de anatel_erbs")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
