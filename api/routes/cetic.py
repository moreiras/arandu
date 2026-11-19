# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Pesquisas TIC do Cetic.br|NIC.br: tabelas oficiais da TIC Domicílios e da TIC Provedores em formato longo.

  * `GET /cetic/tabelas?pesquisa=` — as tabelas da edição (código, título, universo, notas).
  * `GET /cetic/indicadores?pesquisa=&tabela=&dimensao=&recorte=&item=&resposta=` — linhas com proporção, total e margens de erro.
  * `GET /cetic/estimativas` e `GET /cetic/estimativas/uf/{uf}` — estimativas por UF dos microdados da TIC Domicílios, **do Arandurapé**, com erro-padrão.
  * As coleções `cetic_indicadores` (tabelas) e `cetic_estimativas_uf` (estimativas) do `/query` trazem as mesmas linhas.

Valores do Cetic.br sem alteração (CC BY 4.0, citação "Cetic.br|NIC.br"). São estimativas amostrais, com margem de erro; não há dado de pessoa nem de empresa.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import cetic as c
from api.services import demanda_oferta as do

router = APIRouter()

_PESQ = Query("domicilios", description="domicilios (TIC Domicílios) ou provedores (TIC Provedores).")


def _doc(request: Request, pesquisa: str, date: Optional[str]) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    if pesquisa not in ("domicilios", "provedores"):
        raise HTTPException(400, "pesquisa inválida: use domicilios ou provedores.")
    doc = store.cetic_doc(d, pesquisa)
    if not doc:
        raise HTTPException(404, f"Tabelas do Cetic.br ({pesquisa}) não publicadas no snapshot {d}.")
    return doc


@router.get(
    "/cetic/tabelas",
    summary="Pesquisas TIC do Cetic.br: tabelas da edição",
    description="Lista as tabelas da edição vigente da pesquisa (código, título, universo e notas), com a citação e a licença (CC BY 4.0).",
)
def cetic_tabelas(request: Request, pesquisa: str = _PESQ, date: Optional[str] = Query(None)) -> dict:
    return c.tabelas(_doc(request, pesquisa, date))


@router.get(
    "/cetic/indicadores",
    summary="Pesquisas TIC do Cetic.br: indicadores em formato longo",
    description="""
Linhas das tabelas oficiais da TIC Domicílios ou da TIC Provedores: para cada tabela, recorte (região, área, classe social, renda, porte do provedor), item da pergunta e
resposta, a `proporcao` (%), o `total` estimado e as margens de erro (`margem_proporcao` em pontos percentuais, `margem_total` em unidades). Os filtros `dimensao`, `recorte`,
`item` e `resposta` aceitam parte do texto, sem diferença de maiúsculas. Estimativas amostrais do Cetic.br|NIC.br, não contagens; cite a edição.
""",
)
def cetic_indicadores(
    request: Request, pesquisa: str = _PESQ, tabela: Optional[str] = Query(None, description="Aba, ex.: A1 (veja /cetic/tabelas)."),
    dimensao: Optional[str] = Query(None), recorte: Optional[str] = Query(None), item: Optional[str] = Query(None), resposta: Optional[str] = Query(None),
    date: Optional[str] = Query(None), limit: int = Query(100, ge=1, le=1000), page: int = Query(1, ge=1),
) -> dict:
    try:
        return c.indicadores(_doc(request, pesquisa, date), tabela, dimensao, recorte, item, resposta, limit, (page - 1) * limit)
    except c.CeticErro as e:
        raise HTTPException(e.status, e.mensagem)


def _uf_doc(request: Request, date: Optional[str]) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.cetic_uf_doc(d)
    if not doc:
        raise HTTPException(404, f"Estimativas por UF da TIC Domicílios não publicadas no snapshot {d}.")
    return doc


@router.get(
    "/cetic/estimativas",
    summary="TIC Domicílios: estimativas por UF, região e Brasil (microdados)",
    description="""
Estimativas do **Arandurapé** (não são números do Cetic.br) calculadas dos microdados públicos da TIC Domicílios: para Brasil, cada grande região e cada UF, a proporção de domicílios com acesso à
Internet, com computador e com banda larga fixa, o total estimado, o erro-padrão e a margem de erro de 95% (200 pesos de réplica). Grupo com menos de 30 domicílios entrevistados é suprimido. A
resposta traz a `validacao` contra as tabelas oficiais: a estimativa pontual coincide, a margem oficial é maior que a estimada aqui.
""",
)
def cetic_estimativas(
    request: Request, tipo: Optional[str] = Query(None, description="brasil, regiao ou uf."), indicador: Optional[str] = Query(None, description="internet, computador ou banda_larga_fixa."),
    date: Optional[str] = Query(None),
) -> dict:
    try:
        return c.estimativas(_uf_doc(request, date), tipo, indicador)
    except c.CeticErro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/cetic/estimativas/uf/{uf}",
    summary="TIC Domicílios: estimativas de uma UF, com a região e o Brasil para comparar",
    description="As estimativas do Arandurapé (microdados da TIC Domicílios) da UF, com erro-padrão e margem de 95%, ao lado das da grande região e do Brasil.",
)
def cetic_estimativas_uf(uf: str, request: Request, date: Optional[str] = Query(None)) -> dict:
    try:
        return c.estimativas_uf(_uf_doc(request, date), uf)
    except c.CeticErro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/mercado/demanda-oferta",
    summary="Demanda × oferta de banda larga fixa por UF (TIC Domicílios × IBGE × SICI)",
    description="""
Estimativa do **Arandurapé**: a proporção de domicílios com banda larga fixa (TIC Domicílios, Cetic.br|NIC.br) aplicada aos domicílios do IBGE projetados é a **demanda**; os acessos
fixos de pessoa física declarados ao SICI são a **oferta**. Devolve a razão oferta ÷ demanda e o mercado não visto, ambos com intervalo de 95% (só da amostra da TIC, menor que o
oficial) e a `classe`: `oferta_abaixo_da_demanda`, `compativel`, `oferta_acima_da_demanda` ou `indeterminado` (precisão baixa). Sem `uf`, traz Brasil, regiões e as 27 UFs. Razão baixa
é sinal para investigar, não prova de provedor sem declaração: acesso não é domicílio e os períodos das fontes diferem.
""",
)
def demanda_oferta(request: Request, uf: Optional[str] = Query(None, description="Sigla da UF."), date: Optional[str] = Query(None)) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.demanda_oferta_doc(d)
    if not doc:
        raise HTTPException(404, f"Demanda × oferta não publicada no snapshot {d}.")
    try:
        return do.resposta(doc, uf)
    except do.DemandaOfertaErro as e:
        raise HTTPException(e.status, e.mensagem)
