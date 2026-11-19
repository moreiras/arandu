# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Cloudflare Radar por ASN e por UF.

  * `GET /asns/{asn}/radar` — IPv6 (com a data da leitura), participação no tráfego e velocidade (só ASNs de topo) e papel nos eventos de BGP dos últimos 28 dias.
  * `GET /radar/ufs/{uf}` — agregado DERIVADO dos ASNs da UF (o Radar não tem recorte por UF).
  * O mesmo bloco vem em `?include=radar` do ASN e da UF.

Dados do Cloudflare Radar sob CC BY-NC 4.0 (licença e atribuição na resposta). Ausência de dado não é zero; sem ranking.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.routes.perfis import UFS
from api.services import radar as s

router = APIRouter()


def _data(request: Request, date: Optional[str]) -> str:
    d = request.app.state.store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return d


@router.get(
    "/asns/{asn}/radar",
    summary="Cloudflare Radar em um ASN: IPv6, tráfego, velocidade e papel nos eventos de BGP",
    description="""
`ipv6` é o percentual das requisições HTTP de pessoas que a Cloudflare viu no ASN nos últimos 28 dias, com a data da leitura (rodízio de dias; `cobertura` diz quantos ASNs já foram lidos). `trafego_pct_do_brasil` e
`velocidade` só existem para os ASNs de topo do Brasil: ausência não quer dizer zero. `bgp` conta o papel do ASN nos eventos dos últimos 28 dias (vazou, no caminho de vazamento, sequestrou, vítima de sequestro);
não prova intenção nem dano. Dados do Cloudflare Radar sob **CC BY-NC 4.0**: licença, atribuição, limites e cobertura vêm na resposta.
""",
)
def asn_radar(asn: int, request: Request, date: Optional[str] = Query(None)) -> dict:
    d = _data(request, date)
    b = s.bloco_asn(request.app.state.store.radar_doc(d), asn)
    if b is None:
        raise HTTPException(404, f"AS{asn} sem dado do Cloudflare Radar (ainda não lido pelo rodízio, fora do Radar ou produto não publicado) no snapshot {d}.")
    return b


@router.get(
    "/radar/ufs/{uf}",
    summary="Cloudflare Radar agregado por UF (derivado dos ASNs do cadastro)",
    description="""
ASNs da UF, quantos têm IPv6 lido, mediana e média ponderada pelo tráfego (só entre ASNs que têm os dois números) e soma dos papéis de BGP. **Derivado** dos ASNs pelo mapeamento ASN → UF do projeto: o Radar não
tem recorte por UF. Dados do Cloudflare Radar sob **CC BY-NC 4.0**.
""",
)
def uf_radar(uf: str, request: Request, date: Optional[str] = Query(None)) -> dict:
    d = _data(request, date)
    sigla = uf.strip().upper()
    if sigla not in UFS:
        raise HTTPException(404, f"UF inválida: {uf}")
    b = s.bloco_uf(request.app.state.store.radar_doc(d), sigla)
    if b is None:
        raise HTTPException(404, f"UF {sigla} sem dado do Cloudflare Radar (ou produto não publicado) no snapshot {d}.")
    return b
