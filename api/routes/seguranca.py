# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Segurança de roteamento por ASN, parte A.

  * `GET /seguranca/resumo` — agregado do Brasil, por UF e por faixa de porte (ASNs com medição suficiente, em faixas neutras de percentual).
  * O sinal de cada ASN vem em `GET /asns/{asn}?include=seguranca` e na coleção `seguranca_asn` do `/query`.

ROV e DNSSEC são medições do APNIC por amostragem; o AS Rank é inferência do CAIDA; bogon é fato contra as listas da IANA e do Team Cymru. Cada resposta traz a fonte, a data e as limitações.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import seguranca as s

router = APIRouter()


@router.get(
    "/seguranca/resumo",
    summary="Segurança de roteamento: agregado por UF e faixa de porte",
    description="""
Para os ASNs do Brasil: quantos têm medição de ROV (validação RPKI) e de DNSSEC com amostra suficiente (≥ 100), a mediana e a média ponderada do percentual medido pelo
APNIC e a distribuição em faixas neutras (até 10, de 10 a 90, acima de 90), mais quantos originam prefixos em espaço bogon. Sem `uf`, traz o país, todas as UFs e as faixas
de porte (acessos declarados ao SICI); com `uf`, só aquela UF e o país. Não é ranking de empresas; fontes, datas e limites vêm na resposta. O campo `manrs` traz, só de forma agregada, a participação em organizações do programa de operadores do MANRS
(ASNs e usuários, no total, por porte e por UF; recortes com menos de 5 participantes vêm suprimidos), com a atribuição exigida: "Provided by the MANRS with support from the Global Cyber Alliance".
""",
)
def seguranca_resumo(request: Request, date: Optional[str] = Query(None), uf: Optional[str] = Query(None)) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.seguranca_doc(d)
    if not doc:
        raise HTTPException(404, f"Segurança de roteamento não publicada no snapshot {d}.")
    try:
        return {**s.resumo(doc, uf), "manrs": store.manrs_doc(d)}
    except s.SegurancaErro as e:
        raise HTTPException(e.status, e.mensagem)
