# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Cadastro das empresas de telecom (Receita Federal cruzado com o SICI).

  * `GET /empresas/mercado?uf=` — empresas de telecom abertas e baixadas por ano, ativas por UF e por porte.
  * `GET /empresas/operadoras/{cnpj}` — matriz, estabelecimentos, porte, Simples/MEI e a presença física por município (estabelecimento ativo × acessos no SICI).

Fato cadastral na data do dump mensal da Receita; o cruzamento com o SICI não prova atendimento. Sem e-mail, telefone, rua nem CEP; empresário individual sem razão social nem nome fantasia.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import empresas as s

router = APIRouter()


def _data_e_doc(request: Request, date: Optional[str]) -> tuple[str, dict]:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.cadastro_empresas_doc(d)
    if not doc:
        raise HTTPException(404, f"Cadastro das empresas não publicado no snapshot {d}.")
    return d, doc


@router.get(
    "/empresas/mercado",
    summary="Empresas de telecom: entradas e baixas por ano, ativas por UF e porte",
    description="""
Empresas de telecom (matriz com CNAE 61 principal, cadastro da Receita Federal) abertas e baixadas por ano, no país ou em uma UF, e as ativas por UF e por porte (micro, pequeno, demais, MEI).
Uma contagem por empresa (a matriz); não separa operadora de revenda ou de MEI. É o cadastro na data do dump mensal, não o de hoje.
""",
)
def empresas_mercado(request: Request, uf: Optional[str] = Query(None, description="UF (sigla) para restringir as séries"), date: Optional[str] = Query(None)) -> dict:
    _, doc = _data_e_doc(request, date)
    try:
        return s.mercado(doc, uf)
    except s.EmpresasErro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/empresas/operadoras/{cnpj}",
    summary="Cadastro e presença física de uma operadora, pela raiz do CNPJ",
    description="""
Matriz, estabelecimentos (ativos, baixados, filiais ativas), porte, Simples e MEI e, por município, os estabelecimentos × os acessos que a empresa declara no SICI (fixo e móvel). Aceita a raiz
(8 dígitos) ou o CNPJ completo. A diferença entre onde há estabelecimento e onde há acessos vem de duas fontes que medem coisas diferentes e **não prova** que a empresa atende ou deixou de atender
o município. Empresário individual não tem razão social nem nome fantasia. Sem e-mail, telefone, rua nem CEP.
""",
)
def empresas_operadora(request: Request, cnpj: str, date: Optional[str] = Query(None)) -> dict:
    d, doc = _data_e_doc(request, date)
    try:
        raiz = s.raiz_do_cnpj(cnpj)
        return s.operadora(doc, request.app.state.store.cadastro_empresas_faixa(d, raiz[:2]), raiz)
    except s.EmpresasErro as e:
        raise HTTPException(e.status, e.mensagem)
