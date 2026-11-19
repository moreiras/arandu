# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Download único das outorgas da Anatel.

SCM, SMP, STFC e SeAC leem o MESMO arquivo (`prestadoras_servicos_telecomunicacoes.zip`; MD5 idêntico nos quatro CSVs em
2026-10-11 e 2026-10-17). Cada coletor continua filtrando o seu serviço, mas o ZIP é baixado uma vez por data: o primeiro grava
`raw/{data}/summary/anatel-outorgas-{data}.csv.gz` e os demais reaproveitam.
"""
from __future__ import annotations

import gzip
import io
import zipfile
from pathlib import Path

import httpx

from core.common import raw_path

ANATEL_URL = (
    "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/"
    "outorga_e_licenciamento/prestadoras_servicos_telecomunicacoes.zip"
)


def arquivo_bruto(base: Path, date_str: str) -> Path:
    return raw_path(base, date_str, "summary") / f"anatel-outorgas-{date_str}.csv.gz"


def obter_csv(date_str: str, base: Path, log, url: str = ANATEL_URL) -> bytes:
    """CSV das outorgas da data: do bruto já gravado hoje ou, se não houver, baixado e gravado comprimido."""
    destino = arquivo_bruto(base, date_str)
    if destino.exists():
        with gzip.open(destino, "rb") as f:
            conteudo = f.read()
        log.info("outorgas da Anatel reaproveitadas do bruto da data", arquivo=str(destino), size_kb=round(len(conteudo) / 1024, 1))
        return conteudo

    log.info("downloading Anatel outorgas", url=url)
    with httpx.Client(timeout=180, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
    zip_bytes = resp.content
    log.info("download complete", size_mb=round(len(zip_bytes) / 1_048_576, 1))

    conteudo = None
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        nomes = zf.namelist()
        log.info("zip contents", files=nomes)
        for nome in nomes:
            if nome.lower().endswith(".csv"):
                conteudo = zf.read(nome)
                log.info("csv found", file=nome, size_kb=round(len(conteudo) / 1024, 1))
                break
    if conteudo is None:
        raise RuntimeError(f"Nenhum .csv encontrado no ZIP. Conteúdo: {nomes}")

    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    with tmp.open("wb") as bruto, gzip.GzipFile(filename="", mode="wb", fileobj=bruto, compresslevel=6, mtime=0) as f:
        f.write(conteudo)                       # bytes estáveis: o mesmo CSV tem sempre o mesmo hash no armazém
    tmp.replace(destino)
    return conteudo
