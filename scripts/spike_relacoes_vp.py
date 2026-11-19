# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Medição: quanto custa registrar o ponto de observação (VP) por caminho no parse do MRT?

Baixa o RIB de UM coletor (o mesmo que a coleta usa), lê a *peer index table* e mede, para os formatos candidatos:
caminhos únicos (com contagem de VPs e de prefixos), triplas únicas e elos direcionados únicos; tempo e memória.
Descarta o arquivo no fim. Não escreve nada em `data/`. Saída: JSON em stdout (uma linha por coletor).

    python scripts/spike_relacoes_vp.py route-views.napafrica rv v4
    python scripts/spike_relacoes_vp.py rrc12 ris v4 --arquivo /caminho/rib.gz     # usa um arquivo local
"""
from __future__ import annotations

import argparse
import datetime
import gzip
import json
import resource
import sys
import tempfile
import time
from pathlib import Path

import mrtparse

from core.common import configure_logging
from sources.fulltable_routeviews import collect as fc


def _rss_mib() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(r / (1024 * 1024 if sys.platform == "darwin" else 1024), 1)


def medir(path: Path, afi: str) -> dict:
    alvo = fc._RIB_IPV4 if afi == "v4" else fc._RIB_IPV6
    peers: list[tuple[int, str]] = []                     # índice → (ASN do VP, IP)
    caminhos: dict[tuple, list] = {}                      # caminho comprimido → [conjunto de VPs, nº de prefixos]
    triplas: set[tuple] = set()
    elos: set[tuple] = set()
    entradas = prefixos = 0
    t0 = time.monotonic()
    for m in mrtparse.Reader(str(path)):
        if m.err:
            continue
        d = m.data
        if fc._first_key(d.get("type", {})) != fc._TABLE_DUMP_V2:
            continue
        sub = fc._first_key(d.get("subtype", {}))
        if sub == 1:                                      # PEER_INDEX_TABLE
            peers = [(int(e.get("peer_as", 0)), str(e.get("ip_address", ""))) for e in d.get("peer_entries", [])]
            continue
        if sub != alvo or not d.get("length"):
            continue
        prefixos += 1
        for rib in d.get("rib_entries", []):
            asp = fc._extract_aspath(rib.get("path_attributes", []))
            if not asp:
                continue
            entradas += 1
            comp = [asp[0]]
            for a in asp[1:]:
                if a != comp[-1]:
                    comp.append(a)
            chave = tuple(comp)
            vp = rib.get("peer_index", -1)
            reg = caminhos.get(chave)
            if reg is None:
                caminhos[chave] = [{vp}, 1]
            else:
                reg[0].add(vp)
                reg[1] += 1
    seg = time.monotonic() - t0
    for c in caminhos:
        for i in range(len(c) - 1):
            elos.add((c[i], c[i + 1]))
            if i + 2 < len(c):
                triplas.add((c[i], c[i + 1], c[i + 2]))
    # tamanho estimado dos formatos candidatos (JSON compacto + gzip)
    def gz(obj) -> int:
        return len(gzip.compress(json.dumps(obj, separators=(",", ":")).encode(), 6))

    amostra = list(caminhos.items())
    fmt_caminhos = gz([[list(c), len(v[0]), v[1]] for c, v in amostra])
    fmt_triplas = gz([list(t) for t in triplas])
    return {
        "peers_na_tabela": len(peers), "vps_asn_distintos": len({a for a, _ in peers}),
        "prefixos": prefixos, "entradas_rib": entradas,
        "caminhos_unicos": len(caminhos), "triplas_unicas": len(triplas), "elos_direcionados": len(elos),
        "caminhos_com_mais_de_1_vp": sum(1 for v in caminhos.values() if len(v[0]) > 1),
        "bytes_gz_caminhos_agregados": fmt_caminhos, "bytes_gz_triplas": fmt_triplas,
        "segundos_parse": round(seg, 1), "rss_pico_mib": _rss_mib(),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("coletor")
    p.add_argument("tipo", choices=["rv", "ris"])
    p.add_argument("afi", choices=["v4", "v6"])
    p.add_argument("--arquivo", type=Path)
    p.add_argument("--data", default=datetime.date.today().isoformat())
    a = p.parse_args(argv)
    log = configure_logging()
    with tempfile.TemporaryDirectory(prefix="spike_rib_") as tmp:
        if a.arquivo:
            dest = a.arquivo
        else:
            alvo = datetime.date.fromisoformat(a.data)
            url = (fc._find_rib_url_rv if a.tipo == "rv" else fc._find_rib_url_ris)(a.coletor, alvo, log)
            if not url:
                print(json.dumps({"coletor": a.coletor, "erro": "sem dump"}))
                return 1
            dest = Path(tmp) / ("rib.gz" if url.endswith(".gz") else "rib.bz2")
            if not fc._download(url, dest, log):
                print(json.dumps({"coletor": a.coletor, "erro": "download"}))
                return 1
        tam = dest.stat().st_size
        r = {"coletor": a.coletor, "afi": a.afi, "arquivo_mib": round(tam / 1048576, 1), **medir(dest, a.afi)}
    print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
