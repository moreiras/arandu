# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Agregação do índice de prontidão: por grupo de ASNs, classes, média ponderada, cobertura dos pilares e medição de cada componente.

Mora em `core/` porque o produto (`products/prontidao`, por UF, porte e operadora), o MANRS e a região (`api/services/regiao.py`, por conjunto de municípios) usam a mesma conta e a API
não importa `products`."""
from __future__ import annotations

import statistics
from collections import defaultdict

from core.avisos_agregado import avisos, peso_top1

CLASSES = ("pronto", "em_progresso", "atrasado", "sem_dados")


COMPONENTES = (("filtragem", "rov"), ("filtragem", "sem_bogon"), ("anti_spoofing", "spoofer"), ("coordenacao", "peeringdb"), ("coordenacao", "irr_aut_num"),
               ("coordenacao", "irr_as_set"), ("validacao_global", "roa"), ("validacao_global", "irr"), ("validacao_global", "aspa"))


def medicoes(itens: list[dict]) -> dict[str, dict]:
    """Por componente, entre os ASNs do grupo que têm o dado: quantos, a média simples do valor (0 a 100; nos componentes sim/não é o % de ASNs com sim) e a média ponderada pelos usuários estimados."""
    out = {}
    for pilar, c in COMPONENTES:
        vs = [(d["pilares"][pilar]["componentes"][c]["valor"], d.get("usuarios") or 0) for d in itens if c in ((d["pilares"].get(pilar) or {}).get("componentes") or {})]
        pesos = sum(w for _, w in vs)
        peso = peso_top1(w for _, w in vs)
        out[c] = {"pilar": pilar, "asns": len(vs), "n_asns_com_dado": len(vs), "media": round(statistics.fmean(v for v, _ in vs), 1) if vs else None,
                  "media_ponderada_usuarios": round(sum(v * w for v, w in vs) / pesos, 1) if pesos else None,
                  "peso_top1": peso, "avisos": avisos(len(vs), peso)}
    return out


def _tem_rov(d: dict) -> bool:
    return "rov" in (((d.get("pilares") or {}).get("filtragem") or {}).get("componentes") or {})


def classes_por_rov(itens: list[dict]) -> dict[str, dict[str, int]]:
    """Classes dos ASNs do grupo separadas por haver ou não ROV medido (SEG-E5). Sem o pilar de filtragem o índice é renormalizado sobre os pilares medidos, então
    "pronto" sem ROV medido e "pronto" com ROV medido não são a mesma afirmação; a soma das duas partes é a distribuição por classe do grupo."""
    return {"com_rov": {c: sum(1 for d in itens if _tem_rov(d) and d["classe"] == c) for c in CLASSES},
            "sem_rov": {c: sum(1 for d in itens if not _tem_rov(d) and d["classe"] == c) for c in CLASSES}}


def agregar(asns: dict[str, dict], grupo_de: dict[str, str]) -> dict[str, dict]:
    """Por grupo (UF, faixa de porte ou operadora): contagem por classe, média ponderada pelos usuários estimados e cobertura de cada pilar."""
    por: dict[str, list[dict]] = defaultdict(list)
    for a, d in asns.items():
        g = grupo_de.get(a)
        if g is not None:
            por[g].append(d)
    out = {}
    for g, itens in sorted(por.items()):
        com = [d for d in itens if d["total"] is not None]
        pesos = [d.get("usuarios") or 0 for d in com]
        media = (sum(d["total"] * w for d, w in zip(com, pesos)) / sum(pesos)) if sum(pesos) else (statistics.fmean(d["total"] for d in com) if com else None)
        peso = peso_top1(pesos)
        por_rov = classes_por_rov(itens)
        out[g] = {"asns": len(itens), "classes_com_rov": por_rov["com_rov"], "classes_sem_rov": por_rov["sem_rov"], "n_asns_com_dado": len(com), "peso_top1": peso, "avisos": avisos(len(com), peso), "classes": {c: sum(1 for d in itens if d["classe"] == c) for c in CLASSES}, "asns_com_indice": len(com),
                  "media_ponderada_usuarios": round(media, 1) if media is not None else None, "mediana": round(statistics.median(d["total"] for d in com), 1) if com else None,
                  "usuarios": sum(d.get("usuarios") or 0 for d in itens),
                  "cobertura_pilares": {p: sum(1 for d in itens if p in d["pilares"]) for p in ("filtragem", "anti_spoofing", "coordenacao", "validacao_global")},
                  "medicoes": medicoes(itens)}
    return out
