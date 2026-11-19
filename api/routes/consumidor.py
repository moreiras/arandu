# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Reclamações no Consumidor.gov.br.

  * `GET /consumidor/resumo` — o setor por mês, a janela de 12 meses, a cobertura da ligação empresa → CNPJ e do casamento da cidade ao IBGE.
  * `GET /consumidor/marcas?uf=&q=&com_cnpj=` — uma linha por empresa (alfabética, sem ranking) com os indicadores da janela ou da UF.
  * `GET /consumidor/municipios/{ibge}` — o total do município e as empresas com reclamações suficientes.
  * `include=consumidor` nos perfis de operadora, município e UF; coleção `consumidor_marca` do `/query`.

Só agregados, com base mínima (sexo e faixa etária de quem reclamou não são guardados). Sem ranking nem veredito.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.routes.qualidade import nomes_de
from api.services import consumidor as c

router = APIRouter()


def _doc(request: Request, date: Optional[str]) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.consumidor_doc(d)
    if not doc:
        raise HTTPException(404, f"Reclamações do Consumidor.gov.br não publicadas no snapshot {d}.")
    return doc


@router.get(
    "/consumidor/resumo",
    summary="Consumidor.gov.br: o setor de telecomunicações por mês, a janela e a cobertura da ligação",
    description="""
Reclamações **finalizadas** de consumidores contra operadoras de telecomunicações no Consumidor.gov.br (Senacon): o total do setor por mês (finalizadas, respondidas, índice de solução, tempo médio de resposta
e nota média, só com base mínima), a janela de 12 meses usada nos indicadores, **quanto das reclamações está ligado a um CNPJ** (tabela curada do Arandurapé) e quanto das cidades foi casado ao código IBGE.
Só agregados; sexo e faixa etária de quem reclamou não são guardados. Não é o total de reclamações contra a empresa (as da Anatel e as dos Procons são outras bases). Sem ranking.
""",
)
def consumidor_resumo(request: Request, date: Optional[str] = Query(None)) -> dict:
    return c.resumo(_doc(request, date))


@router.get(
    "/consumidor/marcas",
    summary="Reclamações no Consumidor.gov.br por empresa: finalizadas, índice de solução, tempo de resposta e nota",
    description="""
Uma linha por empresa (nome fantasia no Consumidor.gov.br) na janela de 12 meses ou, com `uf`, naquela UF: reclamações finalizadas, respondidas, avaliadas e resolvidas, % respondidas, **índice de solução**
(resolvidas ÷ avaliadas pelo consumidor), tempo médio de resposta em dias e nota média (1 a 5). Índice, tempo e nota só aparecem com pelo menos 30 casos (nulo = base insuficiente, não zero). `raizes` são as
raízes de CNPJ ligadas à empresa (`casamento` = curada ou automatico; vazio = sem CNPJ, nunca um palpite). `q` busca no nome. **Ordem alfabética: não há ordenação por volume, solução ou nota**.
Reclamação não é prova de falha da empresa e depende do tamanho da base de clientes.
""",
)
def consumidor_marcas(
    request: Request, uf: Optional[str] = Query(None, min_length=2, max_length=2), q_: Optional[str] = Query(None, alias="q", max_length=80),
    com_cnpj: Optional[bool] = Query(None, description="Só empresas com (true) ou sem (false) CNPJ ligado."), date: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    r = c.marcas(_doc(request, date), uf, q_, com_cnpj, limit, (page - 1) * limit)
    return {**r, "nomes": nomes_de(request, date, (x for m in r["items"] for x in m.get("cnpjs_matriz") or []))}


@router.get(
    "/consumidor/municipios/{ibge}",
    summary="Reclamações no Consumidor.gov.br no município: total e empresas, na janela de 12 meses",
    description="""
O total do município (a cidade digitada pelo consumidor é casada ao código IBGE por nome e UF; o que não casa fica fora) e, por empresa, as linhas com pelo menos 5 reclamações na janela, com os mesmos
indicadores de `/consumidor/marcas`. Só agregados. 404 se o município não tem reclamações no período.
""",
)
def consumidor_municipio(request: Request, ibge: str, date: Optional[str] = Query(None)) -> dict:
    store = request.app.state.store
    doc = _doc(request, date)
    d = store.resolve_date(date)
    cod = ibge.strip()
    uf = c.uf_do_municipio(doc, cod)
    r = c.municipio(store.consumidor_municipios_uf(d, uf) if uf else None, cod, doc)
    if r is None:
        raise HTTPException(404, f"Município {ibge} sem reclamações no Consumidor.gov.br no período.")
    return r
