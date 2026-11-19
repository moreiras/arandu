# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Backfill do histórico do LACNIC: só GUARDA, comprimido e retomável.

  delegated  https://ftp.lacnic.net/pub/stats/lacnic/archive/AAAA/delegated-lacnic-extended-AAAAMMDD (+ .md5, conferido)
             um arquivo por dia desde 2003; padrão: desde 2020-01-01 (pós-esgotamento do IPv4)
  transfers  https://ftp.lacnic.net/pub/stats/lacnic/transfers/AAAA/transfers_AAAAMMDDThhmmssZ.json
             uma versão do log de transferências por dia desde 2016-08-30 (o log é append-only: as versões servem para auditar edições)

Saída (fora de raw/ e de normalized/, então o `arandu gc` nunca toca):
  data/historico/lacnic/delegated-extended/AAAA/delegated-lacnic-extended-AAAAMMDD.gz
  data/historico/lacnic/transfers/AAAA/transfers_AAAAMMDDThhmmssZ.json.gz

Gentil com o servidor público: uma conexão, pausa entre downloads (`--pausa`, padrão 1 s) e `--limite` de arquivos novos por execução.
Idempotente: o que já existe é pulado, então rodar de novo continua de onde parou.

Uso:
    python -m sources.lacnic_historico.collect --tipo delegated --desde 2020-01-01 --limite 200
    python -m sources.lacnic_historico.collect --tipo transfers --ate 2018-12-31
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import httpx

from core.common import configure_logging, data_dir
from core.site import USER_AGENT

BASE = "https://ftp.lacnic.net/pub/stats/lacnic/"
HEADERS = {"User-Agent": USER_AGENT}
INICIO = {"delegated": dt.date(2020, 1, 1), "transfers": dt.date(2016, 8, 30)}
_ARQ = {
    "delegated": re.compile(r'href="(delegated-lacnic-extended-(\d{8}))"'),
    "transfers": re.compile(r'href="(transfers_(\d{8})T\d{6}Z\.json)"'),
}
_DIR = {"delegated": "archive", "transfers": "transfers"}
_SAIDA = {"delegated": "delegated-extended", "transfers": "transfers"}


def listar_ano(client: httpx.Client, tipo: str, ano: int) -> list[tuple[str, dt.date]]:
    """[(nome do arquivo, data)] do diretório do ano, em ordem; ano ainda sem diretório → []."""
    r = client.get(f"{BASE}{_DIR[tipo]}/{ano}/")
    if r.status_code == 404:
        return []
    r.raise_for_status()
    achados = sorted({(n, dt.datetime.strptime(d, "%Y%m%d").date()) for n, d in _ARQ[tipo].findall(r.text)}, key=lambda x: x[0])
    return achados


def destino(base: Path, tipo: str, nome: str) -> Path:
    ano = re.search(r"(\d{4})\d{4}", nome).group(1)
    sufixo = ".gz"
    return base / "historico" / "lacnic" / _SAIDA[tipo] / ano / (nome + sufixo)


def _gravar_gz(alvo: Path, conteudo: bytes) -> None:
    alvo.parent.mkdir(parents=True, exist_ok=True)
    tmp = alvo.with_name(alvo.name + ".tmp")
    with tmp.open("wb") as bruto, gzip.GzipFile(filename="", mode="wb", fileobj=bruto, compresslevel=6, mtime=0) as f:
        f.write(conteudo)
    tmp.replace(alvo)


def _md5_esperado(texto: str) -> str | None:
    m = re.search(r"\b([0-9a-fA-F]{32})\b", texto)
    return m.group(1).lower() if m else None


class ArquivoVazio(ValueError):
    """O próprio LACNIC publicou o arquivo vazio (visto em 6 versões do log de transferências, 08 e 10/2024): não é falha nossa."""


def baixar_um(client: httpx.Client, tipo: str, ano: int, nome: str, log) -> bytes:
    """Baixa um arquivo e confere: delegated pelo .md5 do LACNIC (quando existe); transfers precisa ser JSON válido."""
    url = f"{BASE}{_DIR[tipo]}/{ano}/{nome}"
    r = client.get(url)
    r.raise_for_status()
    conteudo = r.content
    if not conteudo.strip():
        raise ArquivoVazio(f"{nome}: arquivo vazio na origem")
    if tipo == "delegated":
        m = client.get(url + ".md5")
        if m.status_code == 200:
            esperado = _md5_esperado(m.text)
            if esperado and hashlib.md5(conteudo).hexdigest() != esperado:
                raise ValueError(f"{nome}: md5 não confere (esperado {esperado})")
        else:
            log.warning("md5 indisponível", arquivo=nome, status=m.status_code)
    else:
        json.loads(conteudo)                       # levanta se não for JSON
    return conteudo


def run(tipo: str, base: Path, desde: dt.date, ate: dt.date, limite: int, pausa: float, log,
        client: httpx.Client | None = None, dormir=time.sleep) -> dict:
    proprio = client is None
    client = client or httpx.Client(timeout=120, follow_redirects=True, headers=HEADERS)
    novos = ja_tinha = falhas = 0
    vazios: list[str] = []
    parou_no_limite = False
    try:
        for ano in range(desde.year, ate.year + 1):
            for nome, dia in listar_ano(client, tipo, ano):
                if dia < desde or dia > ate:
                    continue
                alvo = destino(base, tipo, nome)
                if alvo.exists():
                    ja_tinha += 1
                    continue
                if novos >= limite:
                    parou_no_limite = True
                    break
                try:
                    _gravar_gz(alvo, baixar_um(client, tipo, ano, nome, log))
                    novos += 1
                except ArquivoVazio:
                    vazios.append(nome)            # a origem está vazia: não grava e não conta como falha (tenta de novo na próxima)
                    log.warning("arquivo vazio na origem", arquivo=nome)
                except Exception as exc:  # noqa: BLE001 — um arquivo ruim não derruba o backfill; entra na contagem de falhas
                    falhas += 1
                    log.warning("falha no arquivo", arquivo=nome, erro=str(exc))
                dormir(pausa)
            if parou_no_limite:
                break
    finally:
        if proprio:
            client.close()
    r = {"tipo": tipo, "novos": novos, "ja_tinha": ja_tinha, "falhas": falhas, "vazios_na_origem": len(vazios), "parou_no_limite": parou_no_limite}
    log.info("backfill lacnic", **r)
    return r


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Backfill do histórico do LACNIC")
    p.add_argument("--tipo", required=True, choices=sorted(_DIR))
    p.add_argument("--desde", type=dt.date.fromisoformat, default=None)
    p.add_argument("--ate", type=dt.date.fromisoformat, default=dt.date.today())
    p.add_argument("--limite", type=int, default=500, help="máximo de arquivos NOVOS por execução")
    p.add_argument("--pausa", type=float, default=1.0, help="segundos entre downloads")
    a = p.parse_args(argv)
    log = configure_logging()
    r = run(a.tipo, data_dir(), a.desde or INICIO[a.tipo], a.ate, a.limite, a.pausa, log)
    return 1 if r["falhas"] else 0


if __name__ == "__main__":
    sys.exit(main())
