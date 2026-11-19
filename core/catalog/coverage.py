# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cobertura do dicionário de dados sobre o que é de fato publicado (T3(c)).

Unidade medida: chave de primeiro nível de cada arquivo JSON publicado (objeto) ou do primeiro
elemento (lista de objetos). Está 'documentada' quando algum campo do catálogo declara
`publicado_em: "<dono> → <arquivo>#<chave>"` para um padrão que casa o arquivo.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from core.catalog.loader import Catalog, parse_publicado_em, pattern_matches, publicados_declarados


def _chaves(path: Path) -> list[str] | None:
    try:
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as f:
                obj = json.load(f)
        else:
            obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(obj, list):
        obj = obj[0] if obj and isinstance(obj[0], dict) else {}
    if not isinstance(obj, dict):
        return None
    # dicionário-mapa (chaves numéricas são dados, ex.: ASN → nome): vira a pseudo-chave '*'
    if len(obj) > 5 and all(k.isdigit() for k in obj):
        return ["*"]
    return list(obj.keys())


def declarados_por_padrao(cat: Catalog) -> dict[str, set[str]]:
    """{padrão de arquivo publicado: {chaves documentadas}} a partir dos `publicado_em`."""
    doc: dict[str, set[str]] = {}
    for it in [*cat.sources.values(), *cat.products.values()]:
        for c in it.campos:
            for ref in c.publicado_em:
                r = parse_publicado_em(ref)
                if r and r[2]:
                    doc.setdefault(r[1], set()).add(r[2])
    return doc


def cobertura(cat: Catalog, pub_dir: Path, amostra_por_padrao: int = 1) -> dict:
    """Mede a cobertura em `pub_dir` (published/{date}). Arquivos que o catálogo não declara contam como 'nao_declarado'."""
    docs = declarados_por_padrao(cat)
    padroes = sorted({p for dono in [*cat.sources, *cat.products] for p in publicados_declarados(cat, dono)})
    por_padrao: dict[str, dict] = {}
    nao_declarado: list[str] = []
    vistos: dict[str, int] = {}
    for f in sorted(p for p in pub_dir.rglob("*") if p.is_file()):
        rel = f.relative_to(pub_dir).as_posix()
        pad = next((p for p in padroes if pattern_matches(p, rel)), None)
        if pad is None:
            nao_declarado.append(rel)
            continue
        if vistos.get(pad, 0) >= amostra_por_padrao:
            continue
        vistos[pad] = vistos.get(pad, 0) + 1
        ks = _chaves(f)
        if ks is None:
            continue
        ok = [k for k in ks if k in docs.get(pad, set())]
        d = por_padrao.setdefault(pad, {"documentadas": set(), "total": set()})
        d["total"] |= set(ks)
        d["documentadas"] |= set(ok)
    total = sum(len(d["total"]) for d in por_padrao.values())
    doc = sum(len(d["documentadas"]) for d in por_padrao.values())
    return {
        "total": total, "documentadas": doc, "pct": round(100 * doc / total, 1) if total else 100.0,
        "faltam": {p: sorted(d["total"] - d["documentadas"]) for p, d in por_padrao.items() if d["total"] - d["documentadas"]},
        "nao_declarado": nao_declarado,
    }
