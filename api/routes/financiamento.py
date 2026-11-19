# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Crédito público (BNDES) e sanções (CEIS e CNEP) por operadora.

  * `GET /financiamento/operadoras/{cnpj}` — operações de financiamento do BNDES e sanções da CGU da raiz do CNPJ.

Registro de fonte oficial, sem julgamento: o BNDES em valores nominais da data da contratação (só operações diretas e não automáticas) e a sanção na data do arquivo da CGU. Pessoa física nunca entra.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import financiamento as s
from api.services.empresas import EmpresasErro

router = APIRouter()


@router.get(
    "/financiamento/operadoras/{cnpj}",
    summary="Crédito público (BNDES) e sanções (CEIS e CNEP) de uma operadora, pela raiz do CNPJ",
    description="""
Operações de financiamento do BNDES (total contratado e desembolsado em R$ nominais, por ano e UF, e as 50 mais recentes) e sanções do CEIS e do CNEP (vigentes, futuras e encerradas na data do
snapshot, com órgão sancionador, fundamento legal e período). Aceita a raiz (8 dígitos) ou o CNPJ completo. `parte=financiamento|sancoes` devolve só uma delas.

É o registro de cada fonte oficial, sem julgamento, e as duas partes **não se ligam**. 404 quer dizer "sem registro nas fontes recortadas", não "sem operação" nem "sem sanção": o BNDES entra só pelas
operações diretas e a sanção vale na data do arquivo da CGU, que pode não refletir uma suspensão ou anulação recente.
""",
)
def financiamento_operadora(request: Request, cnpj: str, parte: Optional[str] = Query(None, description="`financiamento` ou `sancoes`"), date: Optional[str] = Query(None)) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.financiamento_doc(d)
    if not doc:
        raise HTTPException(404, f"Crédito público e sanções não publicados no snapshot {d}.")
    try:
        return s.operadora(doc, s.raiz_do_cnpj(cnpj), parte)
    except EmpresasErro as e:
        raise HTTPException(e.status, e.mensagem)
