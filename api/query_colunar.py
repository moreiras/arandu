# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Motor de consulta sobre `TabelaColunar`. Mesma linguagem e mesmas respostas de `api.query.execute`.

A equivalência é garantida por construção: cada predicado é avaliado pela **mesma função escalar** do motor por linhas
(`_eval_predicate`), mas uma vez por valor distinto do vocabulário da coluna; o resultado vira máscara por indexação nos códigos.
Filtro, ordenação e agregação só materializam, como dicionários Python, os campos de que precisam e só as linhas que casaram;
a lista final materializa só a página pedida. Testes de equivalência (`tests/unit/test_query_colunar.py`) comparam os dois motores."""
from __future__ import annotations

from itertools import compress
from typing import Any

from api import query as _q
from core.colunar import TabelaColunar
from core.geo import haversine_km


def _mascara_predicado(tab: TabelaColunar, pred: dict) -> list[bool]:
    op = pred.get("op")
    if op == "within_radius":
        return _mascara_raio(tab, pred)
    campo = pred.get("field")
    if not isinstance(campo, str) or op not in _q._OPS:
        raise _q.QueryError(f"predicado inválido: {pred!r} (op deve ser um de {sorted(_q._OPS)})")
    col = tab.colunas.get(campo)
    if col is None:                                   # campo ausente em todas as linhas (como no motor por linhas)
        ok = _q._eval_predicate({}, pred)
        return [ok] * tab.n
    voc = col.vocab()
    resp = [_q._eval_predicate({campo: v}, pred) for v in voc]
    cod = col.codigos
    return [resp[c] for c in cod]


def _mascara_raio(tab: TabelaColunar, pred: dict) -> list[bool]:
    lat_f, lon_f = pred.get("lat", "lat"), pred.get("lon", "lon")
    radius, centers = pred.get("radius_km"), pred.get("centers") or []
    if radius is None or not centers:
        raise _q.QueryError("within_radius exige 'radius_km' e 'centers' (lista de [lat,lon])")
    clat, clon = tab.colunas.get(lat_f), tab.colunas.get(lon_f)
    if clat is None or clon is None:
        return [False] * tab.n
    vlat, vlon = clat.vocab(), clon.vocab()
    memo: dict[tuple[int, int], bool] = {}
    out: list[bool] = []
    for a, b in zip(clat.codigos, clon.codigos):
        r = memo.get((a, b))
        if r is None:
            r = memo[(a, b)] = _q._eval_within_radius({lat_f: vlat[a], lon_f: vlon[b]}, pred)
        out.append(r)
    return out


def _mascara(tab: TabelaColunar, flt: Any) -> list[bool]:
    if flt is None:
        return [True] * tab.n
    if not isinstance(flt, dict):
        raise _q.QueryError(f"filtro inválido: {flt!r}")
    # Combina uma máscara por vez: todas vivas juntas custariam ~2,6 MB por predicado em `global_prefixes`.
    if "and" in flt:
        acc = [True] * tab.n
        for f in flt["and"]:
            m = _mascara(tab, f)
            acc = [a and b for a, b in zip(acc, m)]
        return acc
    if "or" in flt:
        acc = [False] * tab.n
        for f in flt["or"]:
            m = _mascara(tab, f)
            acc = [a or b for a, b in zip(acc, m)]
        return acc
    if "not" in flt:
        return [not x for x in _mascara(tab, flt["not"])]
    return _mascara_predicado(tab, flt)


def _linhas_minimas(tab: TabelaColunar, idx: list[int], campos: set[str]) -> list[dict]:
    """Dicionários só com `campos` (mais `__i`) para as linhas `idx`: o necessário para ordenar/agregar."""
    cols = [(c, tab.colunas[c].vocab(), tab.colunas[c].codigos) for c in campos if c in tab.colunas]
    return [{"__i": i, **{nome: voc[cod[i]] for nome, voc, cod in cols}} for i in idx]


def _campos_de(body: dict) -> set[str]:
    f: set[str] = set()
    for s in body.get("sort") or []:
        if isinstance(s, dict) and isinstance(s.get("field"), str):
            f.add(s["field"].split(".")[0])
    for g in body.get("group_by") or []:
        if isinstance(g, str):
            f.add(g.split(".")[0])
    for a in body.get("aggregate") or []:
        if isinstance(a, dict) and isinstance(a.get("field"), str):
            f.add(a["field"].split(".")[0])
    return f


def execute(tab: TabelaColunar, body: dict) -> dict:
    """Equivalente a `api.query.execute(linhas, body)` para a tabela colunar."""
    if not isinstance(body, dict):
        raise _q.QueryError("corpo da consulta deve ser um objeto JSON")
    flt = body.get("filter")
    mask = _mascara(tab, flt) if flt is not None else None
    idx = list(compress(range(tab.n), mask)) if mask is not None else list(range(tab.n))

    if body.get("group_by") or body.get("aggregate"):
        rows = _linhas_minimas(tab, idx, _campos_de(body))
        # o filtro já foi aplicado; `execute` por linhas só agrega
        return _q.execute(rows, {k: v for k, v in body.items() if k not in ("filter", "sort", "select")})

    sort = body.get("sort") or []
    if sort:
        rows = _linhas_minimas(tab, idx, _campos_de(body))
        for s in reversed(sort):
            if not isinstance(s, dict) or "field" not in s:
                raise _q.QueryError(f"sort inválido: {s!r}")
            rows = _q._ordenar(rows, s["field"], s.get("dir") == "desc")
        idx = [r["__i"] for r in rows]

    total = len(idx)
    limit = max(1, min(int(body.get("limit", 100)), 1000))
    page = max(1, int(body.get("page", 1)))
    start = (page - 1) * limit
    select = body.get("select")
    items = [_q._project(tab.linha(i), select) for i in idx[start:start + limit]]
    return {"mode": "list", "total": total, "page": page, "limit": limit,
            "pages": (total + limit - 1) // limit if total > 0 else 0, "items": items}
