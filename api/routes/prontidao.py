# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Prontidão em segurança de roteamento.

  * `GET /prontidao/resumo?uf=` — agregado do Brasil, por UF e por faixa de porte (ASNs por classe, média ponderada pelos usuários estimados, cobertura de cada pilar) e as regras do índice.
  * O índice de cada ASN vem em `GET /asns/{asn}?include=prontidao`; o da UF e da operadora (só o agregado do próprio recorte) em `?include=prontidao` dos perfis; a coleção `prontidao_agregado` do `/query`.

  * `GET /prontidao/asns` — lista pública por ASN (filtros e ordem), **ligada por padrão** (`PRONTIDAO_LISTA_NOMINAL`; decisão do mantenedor, com salvaguardas): ordem padrão por ASN, pilar sem dado "não medido" e fora do índice e da classe,
    `pilares_medidos` em cada linha e o aviso de método na resposta. Valem também a coleção `prontidao_asn` do `/query` e a coluna de `/asns?include=prontidao`. Com `PRONTIDAO_LISTA_NOMINAL=0` a rota e a coleção respondem 404.

O índice é soma ponderada de medições de terceiros, com regras públicas e versionadas; não é veredito sobre a empresa.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import prontidao as p

router = APIRouter()


@router.get(
    "/prontidao/resumo",
    summary="Prontidão em segurança de roteamento: agregado por UF e faixa de porte",
    description="""
Índice de prontidão dos ASNs do Brasil em quatro pilares (filtragem, anti-spoofing, coordenação e validação global): ASNs por classe (pronto, em progresso, atrasado, sem dados), média
ponderada pelos usuários estimados do APNIC, mediana e quantos ASNs têm dado em cada pilar. Sem `uf`, traz o país, todas as UFs e as faixas de porte; com `uf`, só aquela UF e o país.
Traz as `regras` (pesos, limiares, versão), as fontes com data e os limites, e `manrs` (participação agregada no MANRS, com atribuição). **Não é ranking de empresas** e não lista ASNs: o índice de um ASN está em `/asns/{asn}?include=prontidao`.
""",
)
def prontidao_resumo(request: Request, date: Optional[str] = Query(None), uf: Optional[str] = Query(None)) -> dict:
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.prontidao_doc(d)
    if not doc:
        raise HTTPException(404, f"Prontidão em segurança de roteamento não publicada no snapshot {d}.")
    try:
        return {**p.resumo(doc, uf), "manrs": store.manrs_doc(d)}
    except p.ProntidaoErro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/prontidao/asns",
    summary="Lista de ASNs com o índice de prontidão (pública, ordem padrão por ASN)",
    description="""
Lista paginada dos ASNs do Brasil com índice, classe, nota de cada pilar (nulo = não medido), quantos pilares foram medidos (`pilares_medidos`), usuários estimados (APNIC), porte, UF e quais pilares não têm dado.
Filtros: `uf`, `classe` (pronto, em_progresso, atrasado, sem_dados), `porte` e `min`/`max` do índice. Ordem: `asn` (padrão, crescente), `usuarios` ou `indice`, à escolha de quem consulta; ASN sem valor na chave vai ao fim.
O índice é soma ponderada de medições de terceiros com regras públicas (`regras`); **não é veredito sobre a empresa** e o anti-spoofing só existe para ~2% dos ASNs. A resposta traz `aviso_metodo`.
Responde 404 se a chave `PRONTIDAO_LISTA_NOMINAL` for desligada (`0`).
""",
)
def prontidao_asns(
    request: Request,
    date: Optional[str] = Query(None),
    uf: Optional[str] = Query(None, description="Sigla da UF da sede do ASN"),
    classe: Optional[str] = Query(None, description="pronto | em_progresso | atrasado | sem_dados"),
    porte: Optional[str] = Query(None, description="Faixa de porte por usuários estimados (sem_usuarios, ate_1000, … acima_de_1000000)"),
    min: Optional[float] = Query(None, ge=0, le=100, description="Índice mínimo"),
    max: Optional[float] = Query(None, ge=0, le=100, description="Índice máximo"),
    ordem: str = Query(p.ORDEM_PADRAO, description="asn (padrão) | usuarios | indice"),
    desc: bool = Query(False, description="Ordem decrescente"),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
) -> dict:
    if not p.lista_nominal_habilitada():
        raise HTTPException(404, "A lista de ASNs por índice de prontidão está desligada nesta instância (`PRONTIDAO_LISTA_NOMINAL=0`). Veja /prontidao/resumo e /asns/{asn}?include=prontidao.")
    store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    doc = store.prontidao_doc(d)
    if not doc:
        raise HTTPException(404, f"Prontidão em segurança de roteamento não publicada no snapshot {d}.")
    try:
        return p.lista_asns(doc, store.asn_names(d), uf, classe, porte, min, max, ordem, desc, page, limit)
    except p.ProntidaoErro as e:
        raise HTTPException(e.status, e.mensagem)
