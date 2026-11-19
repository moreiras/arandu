# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`arandu status`: última versão (as_of) de cada fonte, frescor × frescor_maximo e falhas recentes."""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Optional

from arandu.executor import ler_relatorio
from core.catalog.loader import Catalog
from core.store import listar, ultima_verificacao

_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _glob(padrao: str) -> str:
    return re.sub(r"\{[^}]+\}", "*", padrao)


def ultima_versao(raiz: Path, subpasta: str, padrao: str) -> Optional[str]:
    """Maior AAAA-MM-DD de `raiz/subpasta/<data>/<padrao>` que existe (padrão com {x} vira *)."""
    base = raiz / subpasta
    if not base.is_dir():
        return None
    melhor = None
    for d in base.iterdir():
        if _DATA.match(d.name) and any(d.glob(_glob(padrao))):
            melhor = max(melhor or d.name, d.name)
    return melhor


def _dias(frescor: str) -> Optional[int]:
    m = re.fullmatch(r"(\d+)([dhw])", frescor or "")
    if not m:
        return None
    n, u = int(m.group(1)), m.group(2)
    return n * 7 if u == "w" else (n if u == "d" else max(1, n // 24))


def status_das_fontes(cat: Catalog, data_dir: Path, em: str) -> list[dict]:
    hoje = dt.date.fromisoformat(em)
    ult = None
    for d in sorted((data_dir / "ops" / "runs").glob("*.json"), reverse=True) if (data_dir / "ops" / "runs").is_dir() else []:
        ult = ler_relatorio(data_dir, d.stem)
        if ult:
            break
    falhas = {e["id"]: e for e in (ult or {}).get("etapas", []) if e.get("status") == "falha"}
    produtor = {x: s.id for s in cat.steps.values() for x in s.fontes}
    linhas = []
    for s in sorted(cat.sources.values(), key=lambda x: x.id):
        as_of = None
        verificada = None
        vs = listar(data_dir, s.id) if s.tipo != "curada" else []
        if vs:                                   # armazém: idade = última coleta; as_of = referência do dado
            as_of, verificada = vs[-1].as_of, ultima_verificacao(data_dir, s.id)
        elif s.tipo != "curada":
            for sub, padroes in (("normalized", s.saidas.normalizado), ("raw", s.saidas.bruto), ("published", s.saidas.publicado)):
                for p in padroes:
                    if p.startswith("../"):
                        f = list((data_dir / sub).glob(_glob(p[3:])))
                        if f:
                            as_of = max(dt.datetime.fromtimestamp(x.stat().st_mtime).strftime("%Y-%m-%d") for x in f)
                    else:
                        as_of = ultima_versao(data_dir, sub, p)
                    if as_of:
                        break
                if as_of:
                    break
        limite = _dias(s.cadencia.frescor_maximo)
        if s.tipo == "curada":
            estado, idade = "curada", None
        elif as_of is None:
            estado, idade = "ausente", None
        else:
            ref = verificada or as_of
            idade = (hoje - dt.date.fromisoformat(ref if len(ref) == 10 else ref + "-01")).days
            estado = "sem_limite" if limite is None else ("ok" if idade <= limite else "atrasado")
        etapa = produtor.get(s.id)
        f = falhas.get(etapa) if etapa else None
        linhas.append({"fonte": s.id, "tipo": s.tipo, "as_of": as_of, "verificada": verificada, "origem_dados": "armazem" if verificada else "pasta",
                       "idade_dias": idade, "frescor_maximo": s.cadencia.frescor_maximo,
                       "estado": estado, "etapa": etapa, "politica_falha": s.politica_falha,
                       "ultima_falha": f.get("motivo") if f else None})
    return linhas


def texto(linhas: list[dict]) -> str:
    out = [f"{'fonte':32} {'as_of':11} {'idade':>5} {'limite':>7} {'estado':10} falha"]
    for l in linhas:
        out.append(f"{l['fonte']:32} {l['as_of'] or '—':11} {('' if l['idade_dias'] is None else l['idade_dias']):>5} "
                   f"{l['frescor_maximo']:>7} {l['estado']:10} {l['ultima_falha'] or ''}")
    return "\n".join(out)
