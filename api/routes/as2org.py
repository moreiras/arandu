# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Organização por ASN e abuso agregado.

  * `GET /asns/{asn}/organizacao` — organização do ASN (CAIDA) e os outros ASNs do Brasil da mesma organização.
  * `GET /asns/{asn}/abuso` — servidores C2 do Feodo Tracker (abuse.ch) em prefixos do ASN, só contagem.
  * Os mesmos blocos vêm em `?include=organizacao` e `?include=abuso` do ASN; a coleção `organizacoes_asn` do `/query` traz uma linha por ASN.

A organização é inferência do CAIDA a partir do WHOIS (não é grupo societário); o abuso é medição de terceiros, sem IPs e sem veredito.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import as2org as s

router = APIRouter()


def _data(request: Request, date: Optional[str]) -> str:
    d = request.app.state.store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return d


@router.get(
    "/asns/{asn}/organizacao",
    summary="Organização de um ASN (CAIDA) e ASNs irmãos do Brasil",
    description="""
Nome, país e identificador da organização do ASN no CAIDA AS Rank (derivada do WHOIS), quantos ASNs ela tem no mundo (`membros_total`) e os outros ASNs do Brasil dela (`irmaos_br`).
É inferência do CAIDA: pode agrupar filiais sob uma 'Parent' e não é o grupo societário (para esse, veja `/grupos`). Fonte, citação exigida, data da coleta e limites vêm na resposta.
""",
)
def asn_organizacao(asn: int, request: Request, date: Optional[str] = Query(None)) -> dict:
    d = _data(request, date)
    b = s.bloco_organizacao(request.app.state.store.as2org_doc(d), asn)
    if b is None:
        raise HTTPException(404, f"AS{asn} sem organização no CAIDA AS Rank no snapshot {d}.")
    return b


@router.get(
    "/asns/{asn}/abuso",
    summary="Servidores C2 de botnets (Feodo Tracker) em um ASN: contagem",
    description="""
Quantos servidores de comando e controle do Feodo Tracker (abuse.ch, CC0) estão em prefixos do ASN na data da coleta, quantos online e por família. Só contagem, sem IPs. `registrado=false`
quer dizer "nenhum na lista", e NÃO "rede limpa": a lista cobre poucas famílias e está quase vazia em 2026. O ASN que hospeda um C2 não é o dono do servidor. URLhaus não é coletado.
""",
)
def asn_abuso(asn: int, request: Request, date: Optional[str] = Query(None)) -> dict:
    d = _data(request, date)
    b = s.bloco_abuso(request.app.state.store.abuso_doc(d), asn)
    if b is None:
        raise HTTPException(404, f"Abuso agregado não publicado no snapshot {d}.")
    return b
