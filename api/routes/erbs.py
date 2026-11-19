# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Estações do SMP licenciadas (ERBs).

  * `GET /erbs/resumo?uf=` — totais do país, por UF e por operadora (gerações 2G a 5G), com o casamento com o IBGE e o CNPJ.
  * `GET /erbs/municipios?uf=&geracao=&ordem=` — municípios com estação, por número de estações ou por estações por 10 mil habitantes.
  * `GET /map/erbs?geracao=` — camada "Antenas" do mapa: estações em células de ~2 km;
  * `include=erbs` nos perfis de município, UF e operadora; coleção `erbs_municipio` do `/query`.

É **cadastro de licenciamento da Anatel**, não cobertura: estação licenciada pode não estar em operação, uma estação não é uma torre e município sem estação pode ser atendido
por vizinhos. Fonte: Anatel, dados abertos (estações do SMP).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import erbs as e

router = APIRouter()


def _doc(request: Request, date: Optional[str]) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.erbs_doc(d)
    if not doc:
        raise HTTPException(404, f"Estações do SMP não publicadas no snapshot {d}.")
    return doc


@router.get(
    "/erbs/resumo",
    summary="Estações do SMP licenciadas: país, UFs e operadoras",
    description="""
Contagem das estações do SMP licenciadas na Anatel (cadastro, 2G a 5G): total do país, por UF (municípios com estação e com 5G, gerações, operadoras) e por operadora
(CNPJ quando conhecido, estações, municípios, UFs, gerações e tipo do 5G). Com `uf`, só aquela UF. **Cadastro de licenciamento, não cobertura**: veja `limites` na resposta.
""",
)
def erbs_resumo(request: Request, uf: Optional[str] = Query(None, description="Sigla da UF."), date: Optional[str] = Query(None)) -> dict:
    try:
        return e.resumo(_doc(request, date), uf)
    except e.ErbsErro as x:
        raise HTTPException(x.status, x.mensagem)


@router.get(
    "/erbs/municipios",
    summary="Municípios com estações do SMP licenciadas",
    description="""
Municípios com ao menos uma estação licenciada, com o número de estações em cada geração (`estacoes_2g` a `estacoes_5g`; uma estação conta em todas as gerações que tem),
estações por 10 mil habitantes e a operadora com mais estações. `geracao` mantém só os municípios com estação naquela geração; `ordem` = `estacoes` (na geração, se informada) ou
`por_10mil_hab`. Município sem estação não aparece. Cadastro de licenciamento, não cobertura.
""",
)
def erbs_municipios(
    request: Request, uf: Optional[str] = Query(None), geracao: Optional[str] = Query(None, description="2G, 3G, 4G ou 5G."),
    ordem: str = Query("estacoes", description="estacoes ou por_10mil_hab."), date: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    try:
        return e.municipios(_doc(request, date), uf, geracao, ordem, limit, (page - 1) * limit)
    except e.ErbsErro as x:
        raise HTTPException(x.status, x.mensagem)


@router.get(
    "/map/erbs",
    summary="Mapa: estações do SMP licenciadas em grade de ~2 km",
    description="""
GeoJSON de pontos, um por célula de ~2 km (0,02 grau) com ao menos uma estação do SMP licenciada: `n` (estações; só da geração pedida, se `geracao`) e `estacoes`, `g2` a `g5`
(estações da célula com cada geração). É agregado, não a posição de cada estação. Cadastro de licenciamento: não é cobertura. Camada "Antenas" do mapa Explorar.
""",
)
def map_erbs(request: Request, geracao: Optional[str] = Query(None, description="2G, 3G, 4G ou 5G."), date: Optional[str] = Query(None)) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.erbs_grade_doc(d)
    if not doc:
        raise HTTPException(404, f"Grade de estações do SMP não publicada no snapshot {d}.")
    try:
        return e.grade_geojson(doc, geracao)
    except e.ErbsErro as x:
        raise HTTPException(x.status, x.mensagem)
