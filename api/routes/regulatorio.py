# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Regulatório complementar.

  * `GET /fust/resumo?uf=` — compromissos do FUST: país, UFs, programas e editais.
  * `GET /fust/municipios?uf=&programa=&ordem=` — municípios com compromisso, por número, investimento previsto ou compromissos por 10 mil habitantes.
  * `include=fust` nos perfis de município e UF; coleção `fust_municipio` do `/query`.

Cadastro da Anatel (dados abertos): o arquivo não identifica a empresa executora, então não há operadora. O valor é o investimento previsto, não o desembolsado.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import fust as f

router = APIRouter()


def _doc(request: Request, date: Optional[str]) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.fust_doc(d)
    if not doc:
        raise HTTPException(404, f"FUST não publicado no snapshot {d}.")
    return doc


@router.get(
    "/fust/resumo",
    summary="FUST: compromissos por UF, programa e edital",
    description="""
Compromissos de aplicação do FUST registrados pela Anatel (conectividade de escolas e de unidades de saúde, redes de fibra, SMP 4G, favelas): totais do país, por UF, por programa e por
edital, com a situação (atendidos, a vencer, em apuração) e o investimento previsto. Com `uf`, só aquela UF. O arquivo **não identifica a empresa executora**; veja `limites`.
""",
)
def fust_resumo(request: Request, uf: Optional[str] = Query(None, description="Sigla da UF."), date: Optional[str] = Query(None)) -> dict:
    try:
        return f.resumo(_doc(request, date), uf)
    except f.FustErro as x:
        raise HTTPException(x.status, x.mensagem)


@router.get(
    "/fust/municipios",
    summary="Municípios com compromissos do FUST",
    description="""
Municípios com ao menos um compromisso do FUST: total, atendidos, a vencer, em apuração, investimento previsto e compromissos por 10 mil habitantes. `programa` mantém só os municípios
com compromisso naquele programa (código, ex.: `1.1`); `ordem` = `compromissos`, `investimento`, `por_10mil_hab`, `atendidos`, `a_vencer` ou `em_apuracao`. Município sem compromisso não aparece.
""",
)
def fust_municipios(
    request: Request, uf: Optional[str] = Query(None), programa: Optional[str] = Query(None, description="Código do programa, ex.: 1.1."),
    ordem: str = Query("compromissos"), date: Optional[str] = Query(None), limit: int = Query(25, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    try:
        return f.municipios(_doc(request, date), uf, programa, ordem, limit, (page - 1) * limit)
    except f.FustErro as x:
        raise HTTPException(x.status, x.mensagem)


# ── multas, faixas e satélites ──────────────────────────────────────────────

from api.services import regulatorio as r   # noqa: E402


def _doc_de(request: Request, date: Optional[str], nome: str, rotulo: str) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = getattr(store, f"{nome}_doc")(d)
    if not doc:
        raise HTTPException(404, f"{rotulo} não publicado(s) no snapshot {d}.")
    return doc


@router.get(
    "/multas/resumo",
    summary="Multas constituídas da Anatel: totais por serviço e por ano",
    description="""
Multas constituídas pela Anatel contra **pessoas jurídicas** prestadoras de SCM, SMP, STFC e SeAC: totais do país e por grupo de serviço (número de empresas e de multas, valor original, pago e
saldo devedor atualizado) e multas por ano de aplicação. Pessoa física, radiodifusão e serviços privados ficam de fora. **Multa constituída não é condenação definitiva**; veja `limites`.
""",
)
def multas_resumo(request: Request, date: Optional[str] = Query(None)) -> dict:
    return r.multas_resumo(_doc_de(request, date, "multas", "Multas"))


@router.get(
    "/multas/empresas",
    summary="Multas constituídas por empresa (raiz do CNPJ) e serviço",
    description="""
Uma linha por empresa (raiz do CNPJ: matriz e filiais) e grupo de serviço, com multas, valor original, pago, saldo devedor atualizado, situações (Quitado, Devedor, Parcial) e primeiro e último
ano de aplicação. `grupo` filtra por SCM, SMP, STFC ou SeAC; `q` busca no nome ou na raiz do CNPJ; `ordem` = `empresa` (padrão: ordem alfabética pelo nome, neutra), `saldo`, `multas`, `original` ou `pago` (estas, do maior para o menor, por escolha de quem consulta); a resposta traz a regra em `regra_ordem`. **Multa constituída não é condenação definitiva.** Só pessoa jurídica.
""",
)
def multas_empresas(
    request: Request, grupo: Optional[str] = Query(None, description="SCM, SMP, STFC ou SeAC."), q: Optional[str] = Query(None, max_length=80), ordem: str = Query("empresa"),
    date: Optional[str] = Query(None), limit: int = Query(25, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    try:
        return r.multas_empresas(_doc_de(request, date, "multas", "Multas"), grupo, q, ordem, limit, (page - 1) * limit)
    except r.RegulatorioErro as x:
        raise HTTPException(x.status, x.mensagem)


@router.get(
    "/espectro/faixas",
    summary="Quadro de faixas de frequência (PDFF): serviços destinados e atribuídos",
    description="""
Faixas do Plano de Destinação de Frequências da Anatel, com os serviços destinados e atribuídos no Brasil (caráter primário ou secundário). `de` e `ate` (MHz) recortam o intervalo;
`servico` busca no nome do serviço destinado (e `carater` restringe ao primário ou ao secundário). Sem filtro, devolve também as faixas de interesse para a Internet (`referencias`).
**É norma, não licença**: não diz quem explora a faixa nem se está em uso.
""",
)
def espectro_faixas(
    request: Request, de: Optional[float] = Query(None, ge=0, description="Início do intervalo, em MHz."), ate: Optional[float] = Query(None, ge=0, description="Fim do intervalo, em MHz."),
    servico: Optional[str] = Query(None, max_length=80), carater: Optional[str] = Query(None, description="Primário ou Secundário."), date: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    try:
        return r.faixas(_doc_de(request, date, "faixas", "Faixas"), de, ate, servico, carater, limit, (page - 1) * limit)
    except r.RegulatorioErro as x:
        raise HTTPException(x.status, x.mensagem)


@router.get(
    "/espectro/resumo",
    summary="Faixas de interesse para a Internet e contagens do quadro de frequências",
    description="Contagens do quadro de frequências e as faixas de interesse (700 MHz, 3,5 GHz, Wi-Fi 6 GHz...) com os serviços destinados a cada uma. Os nomes das faixas são referência do Arandurapé.",
)
def espectro_resumo(request: Request, date: Optional[str] = Query(None)) -> dict:
    return r.faixas_resumo(_doc_de(request, date, "faixas", "Faixas"))


@router.get(
    "/satelites/resumo",
    summary="Satélites: totais, constelações NGEO e satélites em operação",
    description="Totais dos direitos de exploração de satélite no Brasil (por tipo e status), as constelações de órbita não geoestacionária e os satélites em operação comercial, segundo a Anatel.",
)
def satelites_resumo(request: Request, date: Optional[str] = Query(None)) -> dict:
    return r.satelites_resumo(_doc_de(request, date, "satelites", "Satélites"))


@router.get(
    "/satelites/direitos",
    summary="Direitos de exploração de satélite no Brasil",
    description="""
Direitos de exploração de satélite (operadora, satélite, código, posição orbital, banda, tipo Brasileiro ou Estrangeiro, status, lançamento e validade; `vencido` = validade anterior à data do
snapshot). `operadora` busca no nome da operadora ou do satélite. Direito concedido não é capacidade em uso.
""",
)
def satelites_direitos(
    request: Request, operadora: Optional[str] = Query(None, max_length=80), tipo: Optional[str] = Query(None), status: Optional[str] = Query(None, max_length=60),
    date: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    try:
        return r.satelites_direitos(_doc_de(request, date, "satelites", "Satélites"), operadora, tipo, status, limit, (page - 1) * limit)
    except r.RegulatorioErro as x:
        raise HTTPException(x.status, x.mensagem)
