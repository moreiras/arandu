# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Diff diário do `delegated-lacnic-extended` em eventos do ciclo de vida do IPv4.

O `delegated` diz, para cada bloco, país, status (`allocated`, `assigned`, `reserved`), data de registro e `opaque-id` (a organização, sem nome). Duas fotos de dias seguidos revelam o que
as listas de transferência não mostram:

  * `titularidade`  o `opaque-id` do bloco mudou (transferência, fusão, troca de organização);
  * `recuperacao`   `allocated`/`assigned` → `reserved` (o recurso voltou ao pool do registro);
  * `liberacao`     `reserved` → `allocated`/`assigned` (saiu da reserva para uma organização);
  * `novo`          bloco que não existia; `removido`: bloco que sumiu;
  * `pais`          mudança de país sem mudança de organização.
Dividir ou juntar blocos (o mesmo intervalo de endereços com outro tamanho de registro, mesma organização) **não é evento**: conta como `reorganizacoes`. Compara por intervalo de endereços,
não pela chave do registro, justamente para isso. Evento é diferença **observada** entre duas fotos, sem causa nem intenção; a data é a da foto em que a mudança apareceu.
"""
from __future__ import annotations

import hashlib
import ipaddress
from typing import Iterable

from core.ipv4_listas import faixa_para_cidrs

ALOCADOS = {"allocated", "assigned"}


def _intervalo(b: dict) -> tuple[int, int]:
    i = int(ipaddress.IPv4Address(b["inicio"]))
    return i, i + b["quantidade"] - 1


def _estado(b: dict) -> dict:
    return {"cc": b.get("cc"), "status": b.get("status"), "opaque": b.get("opaque")}


def _ev(dia: str, tipo: str, b: dict, de: dict | None, para: dict | None) -> dict:
    return {"id": hashlib.sha1(f"{dia}|{tipo}|{b['inicio']}|{b['quantidade']}".encode()).hexdigest()[:12], "data": dia, "tipo": tipo, "inicio": b["inicio"], "quantidade": b["quantidade"],
            "blocos": faixa_para_cidrs(b["inicio"], b["quantidade"]), "de": de, "para": para}


def _classe(de: dict, para: dict) -> str | None:
    """Evento entre dois estados do mesmo intervalo (None = sem mudança que importe)."""
    if de["status"] in ALOCADOS and para["status"] == "reserved":
        return "recuperacao"
    if de["status"] == "reserved" and para["status"] in ALOCADOS:
        return "liberacao"
    if de["opaque"] and para["opaque"] and de["opaque"] != para["opaque"]:
        return "titularidade"
    if de["cc"] and para["cc"] and de["cc"] != para["cc"]:
        return "pais"
    return None


def diff(anterior: dict[str, dict], atual: dict[str, dict], dia: str) -> tuple[list[dict], dict]:
    """Eventos entre duas fotos (`parse_delegated_ipv4`) e contadores (`reorganizacoes`, `iguais`)."""
    eventos: list[dict] = []
    cont = {"iguais": 0, "reorganizacoes": 0}
    novos = {k: b for k, b in atual.items() if k not in anterior}
    sumidos = {k: b for k, b in anterior.items() if k not in atual}
    for k, b in atual.items():
        if k in anterior:
            e = _classe(_estado(anterior[k]), _estado(b))
            if e:
                eventos.append(_ev(dia, e, b, _estado(anterior[k]), _estado(b)))
            else:
                cont["iguais"] += 1
    ivs_sumidos = sorted((_intervalo(b), k) for k, b in sumidos.items())
    usados: set[str] = set()
    for k, b in novos.items():
        i0, i1 = _intervalo(b)
        sob = [(kk, sumidos[kk]) for (a0, a1), kk in ivs_sumidos if a0 <= i1 and a1 >= i0]
        if not sob:
            eventos.append(_ev(dia, "novo", b, None, _estado(b)))
            continue
        usados.update(kk for kk, _ in sob)
        classes = {_classe(_estado(sb), _estado(b)) for _, sb in sob}
        classes.discard(None)
        if not classes:
            cont["reorganizacoes"] += 1
        else:                                                         # o intervalo mudou de tamanho e de estado ao mesmo tempo: o evento é o do estado
            ref = sob[0][1]
            for c in sorted(classes):
                eventos.append(_ev(dia, c, b, _estado(ref), _estado(b)))
    for k, b in sumidos.items():
        if k in usados:
            continue
        i0, i1 = _intervalo(b)
        if not any(a0 <= i1 and a1 >= i0 for a0, a1 in (_intervalo(n) for n in novos.values())):
            eventos.append(_ev(dia, "removido", b, _estado(b), None))
    eventos.sort(key=lambda e: (e["tipo"], int(ipaddress.IPv4Address(e["inicio"]))))
    return eventos, cont


def operacoes(eventos: Iterable[dict]) -> list[dict]:
    """Agrupa eventos da mesma data, tipo e par de organizações em uma operação (um lote de blocos é uma operação só)."""
    grupos: dict[tuple, dict] = {}
    for e in eventos:
        de, para = e.get("de") or {}, e.get("para") or {}
        k = (e["data"], e["tipo"], de.get("opaque"), para.get("opaque"), de.get("cc"), para.get("cc"))
        g = grupos.setdefault(k, {"data": e["data"], "tipo": e["tipo"], "de": de, "para": para, "blocos": [], "enderecos": 0, "registros": 0})
        g["blocos"].extend(e["blocos"])
        g["enderecos"] += e["quantidade"]
        g["registros"] += 1
    return sorted(grupos.values(), key=lambda g: (g["data"], g["tipo"]), reverse=True)
