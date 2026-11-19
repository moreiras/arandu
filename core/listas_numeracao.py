# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Listas diárias de numeração do Registro.br e do LACNIC. Código comum de `sources/registrobr_listas` e `sources/lacnic_listas`.

Só GUARDA o bruto, comprimido e com o dia: as listas públicas do Registro.br mantêm apenas a versão atual e o diretório do
`nicbr-asn-blk` só ~2 semanas. Nenhum produto depende destes arquivos ainda.

Grupos (um por fonte do catálogo):
  registrobr_listas  https://ftp.registro.br/pub/numeracao/{transferencias-diretas-latest, transferencias-diretas-lacnic-latest,
                     recuperacao-latest, recuperados-latest}
  lacnic_listas      https://ftp.lacnic.net/pub/stats/lacnic/{transfers/transfers_latest.json, critical_infra/critical-infra-AAAAMMDD}

Raw: data/raw/{date}/summary/{prefixo}-{nome}-{date}.gz  (bytes originais, Latin-1 no Registro.br, sem reinterpretar)

"""
from __future__ import annotations

import gzip
import re
from pathlib import Path

import httpx

from core.common import raw_path
from core.site import USER_AGENT

REGISTROBR = "https://ftp.registro.br/pub/numeracao/"
LACNIC = "https://ftp.lacnic.net/pub/stats/lacnic/"

# (nome do arquivo no raw, URL)
GRUPOS: dict[str, list[tuple[str, str]]] = {
    "registrobr_listas": [
        ("transferencias-diretas", REGISTROBR + "transferencias-diretas-latest"),
        ("transferencias-diretas-lacnic", REGISTROBR + "transferencias-diretas-lacnic-latest"),
        ("recuperacao", REGISTROBR + "recuperacao-latest"),
        ("recuperados", REGISTROBR + "recuperados-latest"),
    ],
    "lacnic_listas": [
        ("transfers", LACNIC + "transfers/transfers_latest.json"),
        ("critical-infra", LACNIC + "critical_infra/"),         # diretório: acha o arquivo mais recente
    ],
}
_CRITICAL = re.compile(r'href="(critical-infra-(\d{8}))"')
HEADERS = {"User-Agent": USER_AGENT}


def nome_bruto(grupo: str, nome: str, date_str: str) -> str:
    return f"{grupo.split('_')[0]}-{nome}-{date_str}.gz"


def ultimo_critical_infra(indice_html: str) -> str:
    achados = _CRITICAL.findall(indice_html)
    if not achados:
        raise RuntimeError("nenhum critical-infra-AAAAMMDD no índice do LACNIC")
    return max(achados, key=lambda x: x[1])[0]


def _baixar(client: httpx.Client, url: str, log) -> bytes:
    resp = client.get(url)
    resp.raise_for_status()
    log.info("baixado", url=url, bytes=len(resp.content))
    return resp.content


def _gravar_gz(destino: Path, conteudo: bytes) -> int:
    tmp = destino.with_name(destino.name + ".tmp")
    with tmp.open("wb") as bruto, gzip.GzipFile(filename="", mode="wb", fileobj=bruto, compresslevel=6, mtime=0) as f:
        f.write(conteudo)                         # mtime=0: mesmo conteúdo → mesmos bytes → mesmo hash no armazém
    tmp.replace(destino)
    return destino.stat().st_size


def run(grupo: str, date_str: str, base: Path, log, client: httpx.Client | None = None) -> dict:
    """Baixa todos os arquivos do grupo. Falha alto se algum vier vazio ou não baixar (nada parcial fica como bom)."""
    if grupo not in GRUPOS:
        raise ValueError(f"grupo desconhecido: {grupo} (há: {', '.join(GRUPOS)})")
    destino_dir = raw_path(base, date_str, "summary")
    destino_dir.mkdir(parents=True, exist_ok=True)
    proprio = client is None
    client = client or httpx.Client(timeout=120, follow_redirects=True, headers=HEADERS)
    try:
        baixados: dict[str, bytes] = {}
        for nome, url in GRUPOS[grupo]:
            if url.endswith("/"):                  # diretório do critical_infra
                indice = _baixar(client, url, log).decode("utf-8", errors="replace")
                arquivo = ultimo_critical_infra(indice)
                log.info("critical_infra mais recente", arquivo=arquivo)
                conteudo = _baixar(client, url + arquivo, log)
            else:
                conteudo = _baixar(client, url, log)
            if not conteudo.strip():
                raise RuntimeError(f"{nome}: arquivo vazio em {url}")
            baixados[nome] = conteudo
    finally:
        if proprio:
            client.close()
    saida = {}
    for nome, conteudo in baixados.items():       # só grava depois de baixar tudo: sem conjunto parcial
        alvo = destino_dir / nome_bruto(grupo, nome, date_str)
        saida[nome] = {"arquivo": alvo.name, "bytes": len(conteudo), "gz_bytes": _gravar_gz(alvo, conteudo)}
        log.info("bruto gravado", **saida[nome])
    return saida
