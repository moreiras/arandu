# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`arandu repair`: detecta etapas sem saída primária num snapshot e as reexecuta (com dependentes).

A lista de etapas é a do catálogo: toda etapa do pipeline é verificável. Detecção por existência da saída primária
declarada; uma falha parcial dentro de uma etapa (um IXP com coleta ruim) não é detectada: reexecute a etapa com
`arandu run --only <etapa> --date AAAA-MM-DD --force`.
"""
from __future__ import annotations

import re
from pathlib import Path

from core.catalog.loader import Catalog, dependencias_de_etapas, ordem_de_execucao


def _glob(p: str) -> str:
    return re.sub(r"\{[^}]+\}", "*", p)


def saidas_primarias(cat: Catalog, step) -> list[tuple[str, str]]:
    """[(subpasta, padrão)]: a 1ª saída declarada (não cache) de cada fonte/produto que a etapa produz."""
    out: list[tuple[str, str]] = []
    for sid in step.fontes:
        s = cat.sources.get(sid)
        if not s:
            continue
        for sub, lst in (("normalized", s.saidas.normalizado), ("published", s.saidas.publicado), ("raw", s.saidas.bruto)):
            cand = [p for p in lst if not p.startswith("../")]
            if cand:
                out.append((sub, cand[0]))
                break
    for pid in step.produtos:
        p = cat.products.get(pid)
        if not p:
            continue
        for sub, lst in (("published", p.saidas.publicado), ("normalized", p.saidas.normalizado)):
            cand = [x for x in lst if not x.startswith("../")]
            if cand:
                out.append((sub, cand[0]))
                break
    return out


def existe(data_dir: Path, date: str, sub: str, padrao: str) -> bool:
    return any((data_dir / sub / date).glob(_glob(padrao)))


def etapas_faltantes(cat: Catalog, data_dir: Path, date: str) -> list[str]:
    falt = []
    for k in ordem_de_execucao(cat):
        s = cat.steps[k]
        if s.runner != "worker":
            continue
        prim = saidas_primarias(cat, s)
        if prim and not all(existe(data_dir, date, sub, p) for sub, p in prim):
            falt.append(k)
    return falt


def dependentes(cat: Catalog, ids: list[str]) -> list[str]:
    """`ids` mais tudo que depende deles (transitivo), na ordem de execução; só etapas de worker."""
    deps = dependencias_de_etapas(cat)
    alvo = set(ids)
    mudou = True
    while mudou:
        mudou = False
        for k, d in deps.items():
            if k not in alvo and d & alvo:
                alvo.add(k)
                mudou = True
    return [k for k in ordem_de_execucao(cat) if k in alvo and cat.steps[k].runner == "worker"]


def plano_de_reparo(cat: Catalog, data_dir: Path, date: str) -> dict:
    faltam = etapas_faltantes(cat, data_dir, date)
    return {"date": date, "faltam": faltam, "reexecutar": dependentes(cat, faltam) if faltam else []}
