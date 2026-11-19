# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Caminhos únicos com ponto de observação (VP) por coletor.

O grafo de adjacências que a coleta sempre gravou não guarda **quem viu** o caminho. As relações entre ASNs (produto
`as_relationships`) precisam saber: o elo VP→primeiro AS é o mais sujeito a viés, e a confiança de um elo cresce com o nº de VPs.

Por coletor, agrega os caminhos únicos (prepend comprimido) com: nº de VPs distintos (por ASN), nº de rotas e se o primeiro AS do
caminho é o próprio VP. Chave = ASNs empacotados em bytes; VPs = máscara de bits sobre os ASNs de VP do coletor. Sem dedupe entre
coletores: cada coletor grava o seu arquivo e quem consome lê um por vez, em streaming, e acumula só o que precisa.

Formato (`summary/aspaths-{afi}/{coletor}.tsv.gz`): primeira linha `#coletor<TAB>n_vps_total<TAB>asn_vp,asn_vp,…`; depois, por
caminho, `asn asn asn<TAB>n_vps<TAB>n_rotas<TAB>vp0` (`vp0` = 1 se o primeiro AS é um dos VPs do coletor)."""
from __future__ import annotations

import gzip
import os
from array import array
from pathlib import Path
from typing import Iterator, NamedTuple


class Caminho(NamedTuple):
    asns: tuple[int, ...]
    n_vps: int
    n_rotas: int
    vp0: bool


class AgregadorCaminhos:
    def __init__(self) -> None:
        self.dados: dict[bytes, list[int]] = {}          # chave → [máscara de VPs, nº de rotas]
        self._bit: dict[int, int] = {}                   # ASN do VP → posição do bit
        self._peers: list[int] = []                      # índice da peer index table → ASN do VP

    def definir_peers(self, asns: list[int]) -> None:
        self._peers = list(asns)
        for a in asns:
            self._bit.setdefault(a, len(self._bit))

    def adicionar(self, comp: list[int], peer_index: int) -> None:
        """`comp`: AS_PATH com prepend já comprimido; `peer_index`: índice do VP na peer index table."""
        asn_vp = self._peers[peer_index] if 0 <= peer_index < len(self._peers) else -1
        bit = 1 << self._bit.setdefault(asn_vp, len(self._bit))
        k = array("I", comp).tobytes()
        r = self.dados.get(k)
        if r is None:
            self.dados[k] = [bit, 1]
        else:
            r[0] |= bit
            r[1] += 1

    def escrever(self, destino: Path, coletor: str) -> int:
        vps = sorted(a for a in self._bit if a >= 0)
        tmp = destino.with_name(destino.name + ".tmp")
        destino.parent.mkdir(parents=True, exist_ok=True)
        eh_vp = set(vps)
        with gzip.open(tmp, "wt", encoding="utf-8", compresslevel=6) as f:
            f.write(f"#{coletor}\t{len(vps)}\t{','.join(map(str, vps))}\n")
            for k, (mask, n) in self.dados.items():
                a = array("I")
                a.frombytes(k)
                f.write(f"{' '.join(map(str, a))}\t{mask.bit_count()}\t{n}\t{1 if a[0] in eh_vp else 0}\n")
        os.replace(tmp, destino)
        return len(self.dados)


def ler(caminho: Path) -> Iterator[Caminho]:
    """Caminhos de um arquivo `aspaths-*/{coletor}.tsv.gz` (sem o cabeçalho)."""
    with gzip.open(caminho, "rt", encoding="utf-8") as f:
        for linha in f:
            if linha.startswith("#"):
                continue
            c, v, n, p = linha.rstrip("\n").split("\t")
            yield Caminho(tuple(map(int, c.split())), int(v), int(n), p == "1")


def cabecalho(caminho: Path) -> dict:
    with gzip.open(caminho, "rt", encoding="utf-8") as f:
        _, n, vps = f.readline().rstrip("\n").split("\t")
    return {"n_vps": int(n), "vps": [int(x) for x in vps.split(",") if x]}
