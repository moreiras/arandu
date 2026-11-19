# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Régua de validação: precisão e recall dos provedores inferidos contra os objetos ASPA.

O ASPA é autoritativo para "este AS autoriza aquele provedor", mas pequeno, enviesado para operadores cuidadosos e muitas vezes
desatualizado (num estudo, 44 de 76 falsos positivos BR eram provedores segundo o CAIDA). Por isso a precisão medida
é um **limite inferior**. Para medir de verdade o algoritmo é preciso rodá-lo **sem** o ASPA como entrada (`avaliar` não exclui
nada sozinho: quem chama passa os vereditos de uma execução sem ASPA)."""
from __future__ import annotations

from typing import Iterable, Optional

NIVEIS = ("declarado", "confirmado", "provavel", "possivel")


def provedores_inferidos(vereditos: Iterable, nivel_min: str = "possivel") -> set[tuple[int, int]]:
    """{(provedor, cliente)} dos vereditos p2c com nível ≥ `nivel_min`."""
    aceitos = set(NIVEIS[:NIVEIS.index(nivel_min) + 1])
    return {(v.a, v.b) for v in vereditos if v.tipo == "p2c" and v.nivel in aceitos}


def verdade_aspa(aspa: Iterable[dict], clientes: Optional[set[int]] = None) -> set[tuple[int, int]]:
    out = set()
    for o in aspa:
        c = int(o["customer"])
        if clientes is not None and c not in clientes:
            continue
        out |= {(int(p), c) for p in o.get("providers", []) if int(p) != 0}
    return out


def _prf(previsto: set, verdade: set) -> dict:
    acertos = len(previsto & verdade)
    return {"previstos": len(previsto), "verdade": len(verdade), "acertos": acertos,
            "precisao": round(acertos / len(previsto), 4) if previsto else None,
            "recall": round(acertos / len(verdade), 4) if verdade else None}


def avaliar(vereditos: list, aspa: list[dict], br_asns: Optional[set[int]] = None) -> dict:
    """Precisão/recall por nível mínimo, para o conjunto BR (clientes brasileiros) e o global. A precisão só conta clientes que têm
    objeto ASPA (para os demais não há verdade); o recall conta os pares do ASPA."""
    clientes_aspa = {int(o["customer"]) for o in aspa}
    out: dict = {}
    for escopo, clientes in (("global", clientes_aspa), ("br", clientes_aspa & br_asns if br_asns is not None else set())):
        verdade = verdade_aspa(aspa, clientes)
        out[escopo] = {"clientes": len(clientes)}
        for nivel in NIVEIS[1:]:
            prev = {pc for pc in provedores_inferidos(vereditos, nivel) if pc[1] in clientes}
            out[escopo][f"ate_{nivel}"] = _prf(prev, verdade)
    return out


def concordancia_caida(vereditos: list, p2c: Iterable[Iterable[int]], p2p: Iterable[Iterable[int]]) -> dict:
    """Concordância (não acurácia: o CAIDA usa os mesmos coletores) entre as inferências p2c/p2p e o as-rel2."""
    cp2c = {(int(a), int(b)) for a, b in p2c}
    cp2p = {(min(int(a), int(b)), max(int(a), int(b))) for a, b in p2p}
    res = {"p2c": [0, 0, 0], "p2p": [0, 0, 0]}          # [concorda, discorda (outro tipo/direção), ausente no CAIDA]
    for v in vereditos:
        if v.tipo == "p2c":
            r = res["p2c"]
            r[0 if (v.a, v.b) in cp2c else 1 if ((v.b, v.a) in cp2c or (min(v.a, v.b), max(v.a, v.b)) in cp2p) else 2] += 1
        elif v.tipo == "p2p":
            r = res["p2p"]
            k = (min(v.a, v.b), max(v.a, v.b))
            r[0 if k in cp2p else 1 if ((v.a, v.b) in cp2c or (v.b, v.a) in cp2c) else 2] += 1
    return {t: {"concorda": c, "discorda": d, "ausente": a} for t, (c, d, a) in res.items()}
