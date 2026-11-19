# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Bloqueios e interferência medidos pelo OONI, por ASN.

  * `GET /asns/{asn}/bloqueios` — por teste, medições da janela e quantas a PRÓPRIA sonda declarou anômalas.
  * O mesmo bloco vem em `?include=bloqueios` do ASN; a coleção `bloqueios_asn` do `/query` traz uma linha por ASN × teste.

Veredito da sonda (não do backend do OONI; não é prova de censura), só célula com 10 ou mais medições, sem ranking nominal. Dados do OONI sob CC BY-NC-SA 4.0 (licença e atribuição na resposta).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import bloqueios as s

router = APIRouter()


@router.get(
    "/asns/{asn}/bloqueios",
    summary="Bloqueios e interferência medidos pelo OONI em um ASN (veredito da sonda)",
    description="""
Por teste (WhatsApp, Telegram, Signal, Facebook Messenger, Tor, Psiphon e, por amostra de horas, Web Connectivity): medições da janela de dias e quantas a PRÓPRIA sonda do OONI declarou anômalas
(`anomalias`, `pct_anomalia`), com o componente (`partes`). **Não é o veredito do backend do OONI nem prova de censura**: pode ser filtro do cliente (controle parental, rede corporativa, VPN), falha do
serviço ou falso positivo; sondas são de voluntários (viés e poucas por ASN). Só vêm testes com `minimo_medicoes` ou mais medições na janela (ASN sem sonda não quer dizer sem bloqueio). Dados do OONI sob
**CC BY-NC-SA 4.0**: licença, atribuição, janela, critério de cada teste e limites vêm na resposta.
""",
)
def asn_bloqueios(asn: int, request: Request, date: Optional[str] = Query(None)) -> dict:
    d = request.app.state.store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    b = s.bloco_asn(request.app.state.store.bloqueios_doc(d), asn)
    if b is None:
        raise HTTPException(404, f"AS{asn} sem teste do OONI com o mínimo de medições (ou produto não publicado) no snapshot {d}.")
    return b
