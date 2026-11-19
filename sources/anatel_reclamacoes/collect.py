# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Anatel: reclamações de consumidores.

Fonte:       https://www.anatel.gov.br/dadosabertos/paineis_de_dados/consumidor/consumidor_reclamacoes.zip (dados abertos; ~356 MB, dois CSVs de ~4,1 GB dentro)
Bruto:       data/raw/{date}/summary/reclamacoes-{date}.zip (o arquivo original, sem alteração)
Normalizado: data/normalized/{date}/summary/anatel_reclamacoes.json.gz
`reclamacoes_contexto.csv` (2020 em diante) e `reclamacoes.csv` (2015 a 2020) já são agregados da Anatel (mês × município × serviço × marca × assunto); lidos em fluxo, saem só totais
por marca, serviço, município, UF e assunto (ver `core/reclamacoes.py`). Nada de texto livre nem de quem reclamou (a fonte não os traz).

Uso:
    python -m sources.anatel_reclamacoes.collect --date 2026-11-02
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path
from typing import Optional

import httpx

from core import reclamacoes
from core.common import configure_logging, data_dir, normalized_path, now_iso, raw_path, read_json_gz, today_str, write_json_gz
from core.site import USER_AGENT

URL = "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/consumidor/consumidor_reclamacoes.zip"
HEADERS = {"User-Agent": USER_AGENT}
ARQUIVOS = ("reclamacoes_contexto.csv", "reclamacoes.csv")
MINIMO_RECLAMACOES = 10_000_000                         # hoje ~28 milhões de reclamações em 2015–2026; bem menos é arquivo truncado
MINIMO_MARCAS = 100                                     # hoje ~1,5 mil nomes


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


def _meta_local(zip_path: Path, normalizado_anterior: Path) -> dict:
    h = hashlib.sha256()
    with open(zip_path, "rb") as f:
        for pedaco in iter(lambda: f.read(1 << 20), b""):
            h.update(pedaco)
    anterior = read_json_gz(normalizado_anterior) if normalizado_anterior.exists() else {}
    return {"sha256": h.hexdigest(), "last_modified": anterior.get("data_arquivo")}


def processar(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as z:
        faltam = [a for a in ARQUIVOS if a not in z.namelist()]
        if faltam:
            raise RuntimeError(f"anatel_reclamacoes: {faltam} ausente(s) do zip ({z.namelist()})")
        return reclamacoes.consolidar_zip(z.open)


def run(date_str: str, base: Path, log, client: Optional[httpx.Client] = None, reprocessar: bool = False) -> dict:
    """`reprocessar`: relê o bruto já guardado (sem rede) quando o leiaute do normalizado muda; a data do arquivo na Anatel vem do normalizado anterior."""
    bruto = raw_path(base, date_str, "summary")
    bruto.mkdir(parents=True, exist_ok=True)
    destino_zip = bruto / f"reclamacoes-{date_str}.zip"
    tmp = destino_zip.with_suffix(".zip.tmp")
    if reprocessar and destino_zip.exists():
        meta = _meta_local(destino_zip, normalized_path(base, date_str, "summary") / "anatel_reclamacoes.json.gz")
    else:
        meta = baixar(tmp, client)
        tmp.replace(destino_zip)
    doc = processar(destino_zip)
    resumo = doc["resumo"]
    if resumo["reclamacoes"] < MINIMO_RECLAMACOES or resumo["marcas"] < MINIMO_MARCAS:
        raise RuntimeError(f"anatel_reclamacoes: só {resumo['reclamacoes']} reclamações e {resumo['marcas']} marcas; arquivo truncado?")
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "anatel_reclamacoes.json.gz", {"snapshot_date": date_str, "generated_at": now_iso(), "fonte": "Anatel, dados abertos (reclamações de consumidores)", "url": URL,
                                                           "data_arquivo": meta["last_modified"], "sha256": meta["sha256"], **doc})
    log.info("anatel_reclamacoes written", **{k: v for k, v in resumo.items() if not isinstance(v, (dict, list))})
    return {k: v for k, v in resumo.items() if not isinstance(v, (dict, list))}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Reclamações de consumidores da Anatel (dados abertos)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    p.add_argument("--reprocessar", action="store_true", help="relê o bruto já guardado em vez de baixar de novo (sem rede)")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log, reprocessar=a.reprocessar))
    except Exception:
        log.exception("falha na coleta de anatel_reclamacoes")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
