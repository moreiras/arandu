# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Séries agregadas do histórico: por PTT, operadora (CNPJ) e UF. Funções puras sobre as linhas de ASN
e sobre o índice de PTTs publicado.

A estimativa de usuários da APNIC oscila de uma medição para outra, então a série traz também `users_ma4`: média das amostras
dos últimos 28 dias (a atual inclusa), por CNPJ e por UF. Só entram na média datas **anteriores ou iguais** à do snapshot
(reprodutível), e `n_ma4` diz quantas amostras sustentam a média."""
from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Iterable, Optional

from products.history.esquema import LinhaIxp, LinhaOperadora, LinhaUf

JANELA_MA_DIAS = 28
SOMAS = ("p4", "p6", "n_ixd", "n_roa", "rpki_valid", "rpki_invalid", "rpki_not_found", "n_alertas")


def linhas_ixp(indice: list[dict]) -> list[dict]:
    """Uma linha por PTT a partir de `ixps/index.json` do snapshot."""
    out = []
    for e in sorted(indice, key=lambda x: x["code"]):
        v4, v6 = e.get("v4") or {}, e.get("v6") or {}
        out.append(LinhaIxp(
            ixp=e["code"], status=e.get("status"),
            n_direct=e.get("asn_direct_union_count"), n_br_direct=e.get("br_asns_direct_union_count"),
            n_origin=e.get("asn_origin_union_count"), n_br_origin=e.get("br_asns_origin_union_count"),
            n_membros=e.get("ixbr_members_count"),
            v4_rotas=v4.get("total_routes"), v4_prefixos=v4.get("unique_prefixes"),
            v6_rotas=v6.get("total_routes"), v6_prefixos=v6.get("unique_prefixes"),
        ).model_dump(exclude_none=True))
    return out


def _somar(acc: dict, ln: dict) -> None:
    acc["n_asns"] += 1
    acc["users"] += ln.get("users") or 0
    acc["v6users"] += ln.get("v6users") or 0
    for k in SOMAS:
        acc[k] += ln.get(k) or 0


def _vazio() -> dict:
    return {"n_asns": 0, "users": 0, "v6users": 0, **{k: 0 for k in SOMAS}}


def agregar_operadoras(linhas_asn: Iterable[dict], grupo_por_cnpj: Optional[dict[str, str]] = None) -> dict[str, dict]:
    """{cnpj: soma} dos ASNs BR com CNPJ. Sem média móvel (ver `com_media_movel`)."""
    por: dict[str, dict] = defaultdict(_vazio)
    for ln in linhas_asn:
        if ln.get("is_br") and ln.get("cnpj"):
            _somar(por[ln["cnpj"]], ln)
    for cnpj, acc in por.items():
        if grupo_por_cnpj and grupo_por_cnpj.get(cnpj):
            acc["grupo_id"] = grupo_por_cnpj[cnpj]
    return por


def agregar_ufs(linhas_asn: Iterable[dict]) -> dict[str, dict]:
    por: dict[str, dict] = defaultdict(_vazio)
    cnpjs: dict[str, set] = defaultdict(set)
    for ln in linhas_asn:
        if ln.get("is_br") and ln.get("uf"):
            _somar(por[ln["uf"]], ln)
            if ln.get("cnpj"):
                cnpjs[ln["uf"]].add(ln["cnpj"])
    for uf, acc in por.items():
        acc["n_cnpjs"] = len(cnpjs[uf])
        acc.pop("n_ixd", None)               # soma de PTTs por ASN não é "PTTs da UF"
        acc.pop("n_alertas", None)
    return por


def dentro_da_janela(data: str, outra: str) -> bool:
    """`outra` é anterior à `data` e a menos de JANELA_MA_DIAS dias dela."""
    d = (dt.date.fromisoformat(data) - dt.date.fromisoformat(outra)).days
    return 0 < d < JANELA_MA_DIAS


def com_media_movel(atual: dict[str, dict], anteriores: list[dict[str, dict]]) -> dict[str, dict]:
    """Acrescenta `users_ma4` e `n_ma4` a cada chave. `anteriores`: agregados de datas na janela (cada um {chave: soma})."""
    for chave, acc in atual.items():
        amostras = [acc["users"]] + [a[chave]["users"] for a in anteriores if chave in a]
        acc["users_ma4"] = round(sum(amostras) / len(amostras), 1)
        acc["n_ma4"] = len(amostras)
    return atual


def linhas_operadora(agg: dict[str, dict]) -> list[dict]:
    return [LinhaOperadora(cnpj=c, **agg[c]).model_dump(exclude_none=True) for c in sorted(agg)]


def linhas_uf(agg: dict[str, dict]) -> list[dict]:
    return [LinhaUf(uf=u, **agg[u]).model_dump(exclude_none=True) for u in sorted(agg)]
