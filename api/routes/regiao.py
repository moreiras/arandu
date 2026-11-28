# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Região.

  * `GET /regiao?ibges=…` — os ASNs de um conjunto de municípios (até 50) e, deles, a participação nos PTTs, os provedores de trânsito e os ASNs que carregam até os PTTs.

É inferência: o ASN entra no município pelo SICI (a operadora declara acessos), pela sede do CNPJ ou por prefixos geolocalizados (DB-IP, precisão de cidade). Os limites vêm na resposta.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import regiao as s

router = APIRouter()


@router.get(
    "/regiao",
    summary="ASNs de um conjunto de municípios: PTTs, trânsito e carregadores",
    description="""
`ibges` são até 50 códigos IBGE de município separados por vírgula (o município da página e os do raio). Devolve os ASNs do conjunto (SICI, sede ou IPs geolocalizados, cada um com seu vínculo),
a participação deles nos PTTs (direta e indireta, em número e %), os provedores de trânsito mais comuns (relações inferidas, com o nível de confiança), os ASNs que carregam os ASNs indiretos até
os PTTs e a lista de provedores (cada um com o `cnpj` da operadora quando o SICI o liga ao ASN; omitido para pessoa natural). É inferência com limites explicados na resposta; não há posição de prefixo nem contato.
""",
)
def regiao(request: Request, ibges: str = Query(..., description="Códigos IBGE de município separados por vírgula (até 50)"), date: Optional[str] = Query(None)) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.regiao_doc(d)
    if not doc:
        raise HTTPException(404, f"Região não publicada no snapshot {d}.")
    try:
        titulares = store.pessoa_natural_indice(d)
        return s.agregar(doc, s.ibges_da_consulta(ibges), store.prontidao_doc(d), cnpj_de=lambda asn: store.sici_cnpj_for_asn(d, asn),
                         e_titular=lambda asn, cnpj: titulares.e_titular(cnpj=cnpj, asn=asn) is not None)
    except s.RegiaoErro as e:
        raise HTTPException(e.status, e.mensagem)
