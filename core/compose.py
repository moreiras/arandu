# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Fragmentos e `compose` do documento de ASN.

Em vez de cada produto reabrir e reescrever os ~87 mil `asns/{asn}.json` já publicados (documentos de ASN, caminhos de IXP, SICI e saúde do ASN
escreviam o mesmo arquivo até 4 vezes, em ordem implícita), cada produto grava o **seu pedaço** em
`build/{data}/fragments/asn/<produto>.jsonl.gz` (uma linha por ASN, em ordem crescente de ASN) e um passo único monta o documento final
e o grava uma só vez, na ordem declarada em `PRODUTOS_ASN`.

Formato de uma linha: `{"asn": 64500, "d": {...campos do produto...}}`. O fragmento `base` é o documento completo de `metricas_ixp_asn`; os demais
acrescentam (ou substituem) chaves, e a ordem das chaves do documento final é a de inserção, igual à do fluxo antigo.
"""
from __future__ import annotations

import gzip
import heapq
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator, Optional

from core.common import build_path, published_path  # noqa: E402

# Ordem em que os pedaços entram no documento: documento de ASN → caminhos de IXP → SICI → saúde do ASN/RPKI.
PRODUTOS_ASN: tuple[str, ...] = ("base", "ixp_paths", "sici", "relacoes", "saude")


def ativo() -> bool:
    """Fluxo de fragmentos + compose ligado (padrão). `ARANDU_COMPOSE=off` usa o fluxo sem compose."""
    return os.environ.get("ARANDU_COMPOSE", "on").lower() not in ("off", "0", "false", "nao", "não")


def fluxo_novo(base: Path, date_str: str) -> bool:
    """O produto deve escrever fragmento: flag ligada E esta data já tem o fragmento `base` (snapshot feito pelo fluxo novo).

    Snapshot montado sem a flag segue o fluxo sem fragmentos, em vez de falhar por falta de base."""
    return ativo() and caminho(base, date_str, "base").is_file()


def diretorio(base: Path, date_str: str) -> Path:
    return build_path(base, date_str, "fragments", "asn")


def caminho(base: Path, date_str: str, produto: str) -> Path:
    return diretorio(base, date_str) / f"{produto}.jsonl.gz"


class FragmentoWriter:
    """Grava um fragmento em streaming (os ASNs têm de chegar em ordem crescente); atômico: só aparece ao fechar sem erro."""

    def __init__(self, destino: Path):
        self.destino = destino
        self._tmp = destino.with_name(destino.name + ".tmp")
        self._ultimo = -1
        self.linhas = 0
        destino.parent.mkdir(parents=True, exist_ok=True)
        self._bruto = self._tmp.open("wb")
        # mtime=0: mesmo conteúdo → mesmos bytes (hash estável no armazém e nos testes)
        self._gz = gzip.GzipFile(filename="", mode="wb", fileobj=self._bruto, compresslevel=6, mtime=0)

    def escrever(self, asn: int, campos: dict) -> None:
        if asn <= self._ultimo:
            raise ValueError(f"fragmento {self.destino.name}: ASN {asn} fora de ordem (anterior {self._ultimo})")
        self._ultimo = asn
        self._gz.write((json.dumps({"asn": asn, "d": campos}, ensure_ascii=False) + "\n").encode("utf-8"))
        self.linhas += 1

    def fechar(self) -> None:
        self._gz.close()
        self._bruto.close()
        self._tmp.replace(self.destino)

    def abortar(self) -> None:
        self._gz.close()
        self._bruto.close()
        self._tmp.unlink(missing_ok=True)


def limpar_derivados(base: Path, date_str: str, depois_de: str = "base") -> list[str]:
    """Apaga os fragmentos dos produtos que vêm DEPOIS de `depois_de` (derivam dele): regravar o base invalida o resto."""
    i = PRODUTOS_ASN.index(depois_de)
    apagados = []
    for p in PRODUTOS_ASN[i + 1:]:
        f = caminho(base, date_str, p)
        if f.exists():
            f.unlink()
            apagados.append(p)
    return apagados


@contextmanager
def gravar_fragmento(base: Path, date_str: str, produto: str):
    if produto == "base":
        limpar_derivados(base, date_str)
    w = FragmentoWriter(caminho(base, date_str, produto))
    try:
        yield w
    except BaseException:
        w.abortar()
        raise
    else:
        w.fechar()


def ler_fragmento(path: Path) -> Iterator[tuple[int, dict]]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for linha in f:
            if linha.strip():
                r = json.loads(linha)
                yield int(r["asn"]), r["d"]


def iterar_documentos(base: Path, date_str: str, produtos: Iterable[str] = PRODUTOS_ASN) -> Iterator[tuple[int, dict]]:
    """(asn, documento) em ordem crescente de ASN, juntando os fragmentos presentes de `produtos` (o primeiro tem de ser `base`).

    Streaming (merge por ASN): um documento por vez em memória. ASN sem `base` é ignorado. Usado pelo `compor_asns` e pelos
    produtos que precisam do documento antes de ele ser publicado (índice, nomes, caminhos de IXP, saúde)."""
    produtos = [p for p in produtos if caminho(base, date_str, p).is_file()]
    if not produtos or produtos[0] != "base":
        raise FileNotFoundError(f"fragmento 'base' ausente em {diretorio(base, date_str)}")

    def com_produto(i: int, p: str):
        for asn, campos in ler_fragmento(caminho(base, date_str, p)):
            yield asn, i, campos

    atual: Optional[int] = None
    doc: Optional[dict] = None
    for asn, i, campos in heapq.merge(*(com_produto(i, p) for i, p in enumerate(produtos)), key=lambda t: (t[0], t[1])):
        if asn != atual:
            if atual is not None and doc is not None:
                yield atual, doc
            atual, doc = asn, None
        if i == 0:
            doc = dict(campos)
        elif doc is not None:
            doc.update(campos)
    if atual is not None and doc is not None:
        yield atual, doc


def compor_asns(base: Path, date_str: str, produtos: Iterable[str] = PRODUTOS_ASN, log=None,
                destino: Optional[Path] = None) -> dict:
    """Monta `asns/{asn}.json` juntando os fragmentos existentes (os ausentes são ignorados) e grava cada documento UMA vez.

    Devolve {"docs", "produtos"}; falha alto se não houver o fragmento `base`."""
    presentes = [p for p in produtos if caminho(base, date_str, p).is_file()]
    destino = destino or published_path(base, date_str, "asns")
    destino.mkdir(parents=True, exist_ok=True)
    docs = 0
    for asn, doc in iterar_documentos(base, date_str, presentes):
        (destino / f"{asn}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        docs += 1
    if log:
        log.info("asn docs composed", docs=docs, produtos=presentes)
    return {"docs": docs, "produtos": presentes}


def recompor(base: Path, date_str: str, log=None) -> dict:
    """`compor_asns` com todos os fragmentos presentes, na ordem de PRODUTOS_ASN (ponto de composição intermediário)."""
    return compor_asns(base, date_str, PRODUTOS_ASN, log)
