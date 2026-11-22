# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`arandu memoria`: pico de memória e duração medidos por etapa, nos relatórios gravados, contra o `memoria_mb` do catálogo.

O executor grava em cada etapa o `pico_mem_mb` (RSS máximo do processo da etapa, por `wait4`). Este resumo junta todos os
relatórios guardados (do dia, histórico e os da trilha contínua) e aponta as etapas sem declaração e as que passaram do declarado:
é daqui que sai o `memoria_mb` que libera uma etapa para rodar em paralelo."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from core.catalog.loader import Catalog, id_de_etapa


def _relatorios(data_dir: Path) -> list[Path]:
    raiz = data_dir / "ops" / "runs"
    return sorted(raiz.glob("*.json")) + sorted(raiz.glob("history/*.json")) + sorted(raiz.glob("continuo/*.json")) \
        + sorted(raiz.glob("continuo/history/*.json"))


def resumo(cat: Catalog, data_dir: Path) -> list[dict]:
    por: dict[str, dict] = {}
    vistos: set[tuple] = set()
    for arq in _relatorios(data_dir):
        try:
            rel = json.loads(arq.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for e in rel.get("etapas") or []:
            eid = id_de_etapa(str(e.get("id")))
            chave = (eid, e.get("inicio"))           # o relatório do dia e a cópia no histórico trazem a mesma execução
            if e.get("inicio") is None or chave in vistos:
                continue
            vistos.add(chave)
            r = por.setdefault(eid, {"etapa": eid, "execucoes": 0, "medidas": 0, "pico_mb": None, "duracao_max_s": None})
            r["execucoes"] += 1
            if e.get("pico_mem_mb") is not None:
                r["medidas"] += 1
                r["pico_mb"] = max(r["pico_mb"] or 0, int(e["pico_mem_mb"]))
            if e.get("duracao_s") is not None:
                r["duracao_max_s"] = max(r["duracao_max_s"] or 0, float(e["duracao_s"]))
    saida = []
    for eid, r in por.items():
        s = cat.steps.get(eid)
        declarado: Optional[int] = s.memoria_mb if s else None
        r["declarado_mb"] = declarado
        if r["pico_mb"] is None:
            r["situacao"] = "sem medição"
        elif declarado is None:
            r["situacao"] = "sem declaração"
        elif r["pico_mb"] > declarado:
            r["situacao"] = "ACIMA do declarado"
        else:
            r["situacao"] = "ok"
        saida.append(r)
    return sorted(saida, key=lambda r: (-(r["pico_mb"] or 0), r["etapa"]))


def texto(linhas: list[dict]) -> str:
    out = [f"{'etapa':34s} {'pico MB':>8s} {'declarado':>9s} {'medidas':>7s} {'dur. máx':>9s}  situação"]
    for r in linhas:
        dur = f"{r['duracao_max_s']:.0f} s" if r["duracao_max_s"] is not None else "—"
        out.append(f"{r['etapa']:34s} {r['pico_mb'] if r['pico_mb'] is not None else '—':>8} "
                   f"{r['declarado_mb'] if r['declarado_mb'] is not None else '—':>9} {r['medidas']:>7d} {dur:>9s}  {r['situacao']}")
    return "\n".join(out)
