# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Exposição de serviços por ASN e por UF.

  * `GET /asns/{asn}/exposicao` — serviços que o Shodan observou no ASN (total, portas mais vistas, serviços em portas de risco por classe, CVEs se o plano tiver a faceta), com a data da leitura.
  * `GET /exposicao/ufs/{uf}` — agregado DERIVADO dos ASNs lidos da UF.
  * O mesmo bloco vem em `?include=exposicao` do ASN e da UF.

Só contagens (nunca lista de IPs nem host individual), com atribuição ao Shodan na resposta. Contagem observada não é prova de vulnerabilidade; ausência de leitura não é zero; sem ranking.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.routes.perfis import UFS
from api.services import exposicao as s

router = APIRouter()


def _data(request: Request, date: Optional[str]) -> str:
    d = request.app.state.store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return d


@router.get(
    "/asns/{asn}/exposicao",
    summary="Exposição de serviços de um ASN (contagens do Shodan)",
    description="""
Serviços que o Shodan observou no ASN na data da leitura (`lido_em`; rodízio de dias, `cobertura` diz quantos ASNs já foram lidos): total de serviços observados (banners, não IPs únicos), portas mais vistas, serviços
em portas de risco por classe (acesso remoto, gestão de roteador/CPE, banco de dados, compartilhamento) e, se o plano da conta do Shodan tiver a faceta, as CVEs mais vistas (senão `vulnerabilidades.disponivel` é falso).
**Só contagens**: nunca lista de IPs nem host individual. Não é prova de vulnerabilidade nem inventário da rede; ausência de leitura não quer dizer zero. Dados do Shodan, com atribuição na resposta.
""",
)
def asn_exposicao(asn: int, request: Request, date: Optional[str] = Query(None)) -> dict:
    d = _data(request, date)
    b = s.bloco_asn(request.app.state.store.exposicao_doc(d), asn)
    if b is None:
        raise HTTPException(404, f"AS{asn} sem leitura de exposição do Shodan (ainda não consultado pelo rodízio ou produto não publicado) no snapshot {d}.")
    return b


@router.get(
    "/exposicao/ufs/{uf}",
    summary="Exposição de serviços agregada por UF (derivada dos ASNs lidos)",
    description="""
Serviços observados e serviços em portas de risco (total, % e por classe e serviço) somados sobre os ASNs da UF já lidos pelo rodízio; a cobertura (ASNs do cadastro × ASNs lidos) vem junto.
**Derivado** dos ASNs pelo mapeamento ASN → UF do projeto. Só contagens; sem CVEs; sem ranking. Dados do Shodan, com atribuição na resposta; não é prova de vulnerabilidade.
""",
)
def uf_exposicao(uf: str, request: Request, date: Optional[str] = Query(None)) -> dict:
    d = _data(request, date)
    sigla = uf.strip().upper()
    if sigla not in UFS:
        raise HTTPException(404, f"UF inválida: {uf}")
    b = s.bloco_uf(request.app.state.store.exposicao_doc(d), sigla)
    if b is None:
        raise HTTPException(404, f"UF {sigla} sem leitura de exposição do Shodan (ou produto não publicado) no snapshot {d}.")
    return b
