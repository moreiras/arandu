# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Trânsito por UF e cone de clientes.

  * `GET /transito/ufs` — por UF, quantos ASNs com sede nela têm provedor inferido e quão concentrado é o trânsito (HHI, top 1 e top 3).
  * `GET /transito/ufs/{uf}` — o detalhe, com os provedores e a participação de cada um.
  * `GET /asns/{asn}/transito` — cone de clientes do ASN (todos, do Brasil, usuários estimados e UFs).
  * O mesmo bloco do ASN vem em `?include=transito`; as coleções `transito_uf` e `transito_asn` do `/query` trazem uma linha por UF e por ASN.

Tudo é inferência sobre relações inferidas pelo ARC v2 (nível provável ou superior): não é lista de contratos de trânsito nem volume de tráfego.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import transito as s

router = APIRouter()


def _data(request: Request, date: Optional[str]) -> str:
    d = request.app.state.store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return d


@router.get(
    "/transito/ufs",
    summary="Concentração do trânsito por UF (provedores inferidos dos ASNs com sede na UF)",
    description="""
Por UF: ASNs do Brasil com sede nela, quantos têm provedor inferido (nível provável ou superior), provedores distintos, HHI (0 a 10.000) sobre a participação de cada provedor
nos ASNs da UF, participação do maior e dos três maiores, e a fração de provedores estrangeiros. A UF é a da sede da organização. É inferência (ARC v2) sobre rotas observadas, não
contratos nem tráfego; veja `limites` e `cobertura` na resposta.
""",
)
def transito_ufs(request: Request, date: Optional[str] = Query(None)) -> dict:
    d = _data(request, date)
    r = s.resumo_ufs(request.app.state.store.transito_ufs_doc(d))
    if r is None:
        raise HTTPException(404, f"Trânsito por UF não publicado no snapshot {d}.")
    return r


@router.get(
    "/transito/ufs/{uf}",
    summary="Provedores de trânsito inferidos de uma UF, com participação e concentração",
    description="Os 20 maiores provedores inferidos dos ASNs com sede na UF: clientes na UF, usuários estimados (APNIC) e participação. Inferência; veja `limites`.",
)
def transito_uf(uf: str, request: Request, date: Optional[str] = Query(None)) -> dict:
    d = _data(request, date)
    b = s.bloco_uf(request.app.state.store.transito_ufs_doc(d), uf)
    if b is None:
        raise HTTPException(404, f"UF {uf} sem trânsito inferido no snapshot {d}.")
    return b


@router.get(
    "/asns/{asn}/transito",
    summary="Cone de clientes de um ASN (clientes diretos e indiretos inferidos)",
    description="""
Clientes diretos, tamanho do cone (todos os ASNs e só os do Brasil), usuários estimados (APNIC, repetidos entre ASNs da mesma operadora) e UFs dos ASNs do Brasil no cone, pela
relação provedor-cliente inferida (ARC v2, nível provável ou superior). Irmãos (mesmo CNPJ raiz ou organização do CAIDA) não contam como clientes. `com_cliente=false` quer dizer
nenhum cliente inferido, não que o ASN não tenha clientes. Só existem elos com ao menos um ASN brasileiro.
""",
)
def asn_transito(asn: int, request: Request, date: Optional[str] = Query(None)) -> dict:
    d = _data(request, date)
    b = s.bloco_asn(request.app.state.store.transito_asns_doc(d), asn)
    if b is None:
        raise HTTPException(404, f"Trânsito não publicado no snapshot {d}.")
    return b
