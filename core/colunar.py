# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tabela colunar de um arquivo só, para coleções grandes (ex.: `maps/global_prefixes.col`).

Cada coluna é codificada por dicionário: um vetor de códigos `int32` (um por linha) e um vocabulário de valores JSON distintos
(string, número, `null` ou lista). A leitura mapeia o arquivo em memória (`mmap`): os códigos não passam pelo heap do Python e o
sistema operacional decide o que fica residente. O motor de consulta (`api/query_colunar.py`) avalia cada predicado **uma vez por
valor distinto** e só depois por linha, o que torna filtros sobre 300 mil linhas questão de dezenas de milissegundos.

Formato: `ARCOL1\\n` + tamanho do cabeçalho (8 bytes, little-endian) + cabeçalho JSON + dados alinhados em 8 bytes.
Sem dependências além da biblioteca padrão (nada de numpy na imagem da API)."""
from __future__ import annotations

import json
import mmap
import os
import struct
import sys
from array import array
from pathlib import Path
from typing import Any, Iterable, Optional

MAGIA = b"ARCOL1\n"
EXTENSAO = ".col"


def _alinha(n: int) -> int:
    return (n + 7) & ~7


def escrever(destino: Path, colunas: dict[str, list[Any]], meta: Optional[dict] = None) -> int:
    """Grava `colunas` ({nome: valores, todos com o mesmo tamanho}) de forma atômica. Devolve o número de linhas."""
    nomes = list(colunas)
    n = len(colunas[nomes[0]]) if nomes else 0
    if any(len(v) != n for v in colunas.values()):
        raise ValueError("colunas de tamanhos diferentes")
    blobs: list[bytes] = []
    desc: list[dict] = []
    for nome in nomes:
        indice: dict[str, int] = {}
        vocab: list[Any] = []
        codigos = array("i")
        for v in colunas[nome]:
            chave = json.dumps(v, ensure_ascii=False, sort_keys=True)
            c = indice.get(chave)
            if c is None:
                c = indice[chave] = len(vocab)
                vocab.append(v)
            codigos.append(c)
        if sys.byteorder != "little":
            codigos.byteswap()
        # vocabulário em linhas JSON (sem quebra de linha crua) + deslocamentos: valor de um código em O(1) sem decodificar tudo
        linhas_voc = [json.dumps(v, ensure_ascii=False, separators=(",", ":")).encode("utf-8") for v in vocab]
        desloc = array("q", [0])
        for lv in linhas_voc:
            desloc.append(desloc[-1] + len(lv) + 1)
        if sys.byteorder != "little":
            desloc.byteswap()
        desc.append({"nome": nome, "distintos": len(vocab)})
        blobs.append(codigos.tobytes())
        blobs.append(desloc.tobytes() + b"".join(lv + b"\n" for lv in linhas_voc))
    # offsets só dependem do tamanho do cabeçalho, que depende dos offsets: dois passos
    def montar(base: int) -> tuple[bytes, list[tuple[int, bytes]]]:
        pos = base
        pecas: list[tuple[int, bytes]] = []
        for i, d in enumerate(desc):
            cod, voc = blobs[2 * i], blobs[2 * i + 1]
            d["codigos"] = [pos, len(cod)]
            pecas.append((pos, cod))
            pos = _alinha(pos + len(cod))
            d["vocab"] = [pos, len(voc)]
            pecas.append((pos, voc))
            pos = _alinha(pos + len(voc))
        cab = json.dumps({"n": n, "colunas": desc, "meta": meta or {}}, ensure_ascii=False).encode("utf-8")
        return cab, pecas

    base = _alinha(len(MAGIA) + 8 + 4096)
    cab, pecas = montar(base)
    if len(MAGIA) + 8 + len(cab) > base:             # cabeçalho maior que o reservado: reserva o necessário
        base = _alinha(len(MAGIA) + 8 + len(cab) + 64)
        cab, pecas = montar(base)
    tmp = destino.with_name(destino.name + ".tmp")
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "wb") as f:
        f.write(MAGIA + struct.pack("<Q", len(cab)) + cab)
        for pos, dados in pecas:
            f.seek(pos)
            f.write(dados)
        f.truncate(max(f.tell(), base))
    os.replace(tmp, destino)
    return n


class Coluna:
    """Uma coluna: `codigos[i]` indexa `vocab()`. O vocabulário de alta cardinalidade não fica em cache."""

    CACHE_ATE = 100_000

    def __init__(self, mm: mmap.mmap, d: dict):
        self.nome = d["nome"]
        self.distintos = d["distintos"]
        off, ln = d["codigos"]
        self.codigos = memoryview(mm)[off:off + ln].cast("i")
        self._voc = d["vocab"]
        self._mm = mm
        self._cache: Optional[list] = None
        off, _ = self._voc
        self._desloc = memoryview(mm)[off:off + 8 * (self.distintos + 1)].cast("q")
        self._dados = off + 8 * (self.distintos + 1)

    def vocab(self) -> list:
        if self._cache is not None:
            return self._cache
        ini, fim = self._dados, self._dados + self._desloc[self.distintos]
        texto = bytes(self._mm[ini:fim]).decode("utf-8")
        v = json.loads("[" + ",".join(texto.split("\n")[:-1]) + "]") if self.distintos else []
        if len(v) <= self.CACHE_ATE:
            self._cache = v
        return v

    def valor_do_codigo(self, c: int) -> Any:
        if self._cache is not None:
            return self._cache[c]
        a, b = self._dados + self._desloc[c], self._dados + self._desloc[c + 1] - 1
        return json.loads(bytes(self._mm[a:b]).decode("utf-8"))

    def valor(self, i: int) -> Any:
        return self.valor_do_codigo(self.codigos[i])


class TabelaColunar:
    """Tabela aberta por `mmap`. Feche com `fechar()` (ou deixe o coletor de lixo fazer)."""

    def __init__(self, caminho: Path):
        self.caminho = caminho
        self._f = open(caminho, "rb")
        try:
            self._mm = mmap.mmap(self._f.fileno(), 0, access=mmap.ACCESS_READ)
        except Exception:
            self._f.close()
            raise
        mm = self._mm
        if mm[:len(MAGIA)] != MAGIA:
            self.fechar()
            raise ValueError(f"{caminho}: não é uma tabela colunar")
        (tam,) = struct.unpack("<Q", mm[len(MAGIA):len(MAGIA) + 8])
        ini = len(MAGIA) + 8
        cab = json.loads(bytes(mm[ini:ini + tam]).decode("utf-8"))
        self.n: int = cab["n"]
        self.meta: dict = cab.get("meta") or {}
        self.colunas: dict[str, Coluna] = {d["nome"]: Coluna(mm, d) for d in cab["colunas"]}

    def campos(self) -> list[str]:
        return list(self.colunas)

    def linha(self, i: int) -> dict:
        return {nome: c.valor(i) for nome, c in self.colunas.items()}

    def fechar(self) -> None:
        for c in getattr(self, "colunas", {}).values():
            c.codigos.release()
            c._desloc.release()
        try:
            self._mm.close()
        finally:
            self._f.close()


def aberta_ou_none(caminho: Path) -> Optional[TabelaColunar]:
    try:
        return TabelaColunar(caminho)
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return None


def linhas(colunas: dict[str, list[Any]]) -> Iterable[dict]:
    """Inverso de `escrever` para testes: reconstrói as linhas de um dicionário de colunas."""
    nomes = list(colunas)
    for vals in zip(*(colunas[k] for k in nomes)):
        yield dict(zip(nomes, vals))
