# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estabilidade temporal (E6): histerese sobre o estado publicado de cada elo.

A inferência de um snapshot é só uma *proposta*. A relação publicada (`tipo`, `a`, `b`, `p`, `nivel`) é o **estado**: a do snapshot
anterior, que só muda quando a mesma proposta nova se repete em `persistencia` **gerações de evidência** distintas. Geração = a data da
coleta dos coletores (semanal): dois snapshots diários sobre a mesma coleta são a mesma evidência e não contam como persistência.
Exceção: ASPA positivo (`declarado`) é declaração do operador e muda o estado na hora. Sem snapshot anterior com o bloco, o estado nasce
igual à proposta (a v1 também serve de estado inicial: seus `tipo`/`a`/`b` são lidos como estado).

Cada linha pode trazer `pendente`: `{proposta, desde, n, geracao}` (mudança vista mas ainda não confirmada). Mudanças confirmadas
saem em `mudancas` do documento (de → para), a fonte do evento "mudança de provedor" do histórico."""
from __future__ import annotations

from typing import Optional

Chave = tuple


def chave(l: dict) -> Chave:
    return (min(l["a"], l["b"]), max(l["a"], l["b"]), l["afi"][0] if l.get("afi_divergente") else "")


def assinatura(l: dict) -> tuple:
    """O que identifica a relação (sem p, nível nem evidência)."""
    if l["tipo"] == "p2c":
        return ("p2c", l["a"], l["b"])
    if l["tipo"] == "complexa":
        return ("complexa", (l.get("evid") or {}).get("complexa", {}).get("subtipo"))
    return (l["tipo"],)


def _estado(l: dict) -> dict:
    return {k: l[k] for k in ("tipo", "a", "b", "p", "nivel") if k in l}


def geracao(entradas: dict, data: str) -> str:
    """Identificador da geração de evidência do snapshot: data da coleta dos coletores (a mais antiga das famílias) ou a do snapshot."""
    de = (entradas or {}).get("coletores_coletados_em") or {}
    datas = [d for d in de.values() if d]
    return min(datas) if datas else data


def aplicar(linhas: list[dict], anterior: Optional[dict], data: str, geracao_atual: str, persistencia: int) -> tuple[list[dict], list[dict], dict]:
    """Devolve `(linhas com estado, mudanças confirmadas, resumo)`. `anterior` é o documento publicado do snapshot anterior (ou None)."""
    prev: dict[Chave, dict] = {}
    if anterior:
        for l in anterior.get("relacoes", []):
            prev[chave(l)] = l
    out: list[dict] = []
    mudancas: list[dict] = []
    resumo = {"novos": 0, "estaveis": 0, "pendentes": 0, "confirmadas": 0, "retidas": 0}
    for l in linhas:
        k = chave(l)
        p = prev.get(k)
        if p is None:
            l.pop("pendente", None)
            out.append(l)
            resumo["novos"] += 1
            continue
        if assinatura(l) == assinatura(p):
            l.pop("pendente", None)
            out.append(l)
            resumo["estaveis"] += 1
            continue
        pend = p.get("pendente")
        n = 1
        if pend and _tup(pend["proposta_assinatura"]) == _tup(assinatura(l)):
            n = pend["n"] + (1 if pend["geracao"] != geracao_atual else 0)
            desde = pend["desde"]
        else:
            desde = data
        imediato = l["nivel"] == "declarado" and l["tipo"] == "p2c"
        if imediato or n >= persistencia:
            l.pop("pendente", None)
            l["mudou_em"] = data
            out.append(l)
            mudancas.append({"a": min(l["a"], l["b"]), "b": max(l["a"], l["b"]), "afi": l["afi"], "de": _estado(p), "para": _estado(l),
                             "proposta_desde": desde, "confirmada_em": data, "imediata": imediato})
            resumo["confirmadas"] += 1
            continue
        retida = {k2: v for k2, v in p.items() if k2 not in ("pendente",)}
        retida["visto_em"] = l.get("visto_em", data)
        retida["pendente"] = {"proposta": _estado(l), "proposta_assinatura": list(assinatura(l)), "desde": desde, "n": n, "geracao": geracao_atual}
        out.append(retida)
        resumo["pendentes"] += 1
        resumo["retidas"] += 1
    return out, mudancas, resumo


def _tup(x):
    return tuple(_tup(i) for i in x) if isinstance(x, (list, tuple)) else x
