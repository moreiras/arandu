# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`sources[]` do manifesto: de que versão de cada fonte o snapshot é feito e quão fresca ela está."""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Optional

from core.catalog.loader import Catalog
from core.store.fontes import arquivos_da_fonte, as_of_do_dado
from core.store.legado import ler_indice
from core.store.versions import resolver, ultima_verificacao

LAYOUT_VERSION = 1


def _dias(frescor_maximo: str) -> Optional[int]:
    m = re.fullmatch(r"(\d+)([dhw])", frescor_maximo or "")
    if not m:
        return None
    n, u = int(m.group(1)), m.group(2)
    return n * 7 if u == "w" else (n if u == "d" else max(1, n // 24))


def _frescor(idade: Optional[int], frescor_maximo: str) -> str:
    limite = _dias(frescor_maximo)
    if idade is None:
        return "desconhecido"
    if limite is None:
        return "sem_limite"
    return "ok" if idade <= limite else "atrasado"


def compor_fontes(cat: Catalog, data_dir: Path, date: str) -> list[dict]:
    """Uma entrada por fonte não curada: a versão resolvida para `date` (ou o legado inferido dos arquivos) e o frescor.

    Frescor = idade da última coleta registrada (não da `as_of`, que no SICI é um mês de referência) contra
    `frescor_maximo` do catálogo. Fonte sem versão nem arquivos aparece como `ausente`.
    """
    hoje = dt.date.fromisoformat(date)
    saida = []
    for s in sorted(cat.sources.values(), key=lambda x: x.id):
        if s.tipo == "curada" or s.cadencia.coleta_atual == "manual":      # curada ou backfill manual: não compõe o snapshot
            continue
        v = resolver(data_dir, s.id, date)
        if v is not None:
            ver = ultima_verificacao(data_dir, s.id)
            ref = min(ver, date) if ver else v.disponivel_desde
            idade = (hoje - dt.date.fromisoformat(ref)).days
            saida.append({"id": s.id, "as_of": v.as_of, "coletado_em": v.coletado_em, "hash": v.hash, "versao": v.nome,
                          "origem": "armazem", "frescor": _frescor(max(idade, 0), s.cadencia.frescor_maximo)})
            continue
        arqs = arquivos_da_fonte(cat, data_dir, s.id, date)
        if arqs:
            saida.append({"id": s.id, "as_of": as_of_do_dado(s.id, arqs, date), "coletado_em": None, "hash": None,
                          "versao": None, "origem": "legado", "legado": True, "frescor": "desconhecido"})
        else:
            saida.append({"id": s.id, "as_of": None, "coletado_em": None, "hash": None, "versao": None,
                          "origem": "ausente", "frescor": "ausente"})
    return saida


def fontes_do_legado(data_dir: Path, date: str) -> Optional[list[dict]]:
    """`sources[]` de um snapshot antigo a partir do índice lateral (`catalog/snapshots/{date}.json`), sem tocar no manifesto."""
    idx = ler_indice(data_dir, date)
    if not idx:
        return None
    return [{"id": f["id"], "as_of": f.get("as_of"), "coletado_em": None, "hash": None, "versao": None,
             "origem": "legado", "legado": True, "frescor": "desconhecido"} for f in idx.get("fontes", [])]
