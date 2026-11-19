# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Rejeições, communities e política de roteamento nos route servers do IX.br (níveis 2 e 3 do Alice-LG).

  * `GET /ixps/{code}/rejeicoes` — rotas que o route server rejeitou no PTT, por motivo decodificado e por ASN.
  * `GET /asns/{asn}/politica` — rejeições do ASN por motivo (com amostra de prefixos) e política declarada por communities (perfil INFERIDO, ações, blackhole, RPKI).
  * `GET /communities` — explorador: communities que aparecem nas rotas recebidas coletadas, com classe, rótulo e quem as usa.
  * Os mesmos blocos vêm em `?include=politica_rs` do ASN e `?include=rejeicoes` do PTT; `/query` traz as coleções `rs_communities` e `rs_filtradas`.

É a declaração do membro e a decisão do route server vistas pelo Alice-LG, não tráfego nem relação comercial. O perfil é inferido e só existe para quem teve as rotas recebidas coletadas
(rodízio dentro de um orçamento de requisições: veja `cobertura`). Sem contatos: só ASN, nome do membro como rotulado no route server, prefixos públicos de roteamento e communities.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import rs_policy as r

router = APIRouter()

CLASSES = ("rejeicao", "rpki", "blackhole", "nao_exportar_para", "exportar_somente_para", "nao_exportar_rir", "exportar_somente_rir", "nao_exportar_ptt", "nao_exportar_rtt",
           "nao_exportar_perda", "informativa", "outra")


def _data(request: Request, date: Optional[str]) -> str:
    d = request.app.state.store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return d


@router.get(
    "/ixps/{code}/rejeicoes",
    summary="Rotas rejeitadas pelo route server em um PTT, por motivo e por ASN",
    description="""
Por motivo decodificado pelo dicionário de communities do Alice (RPKI inválido, bogon, inválido no Registro.br ou nos RIRs, comprimento, nunca via route server, blackhole confirmado…): rotas e ASNs.
`rejeicoes.asns` lista os ASNs com mais rotas rejeitadas (paginado por `limit` e `page`; `motivo` mantém só os ASNs com aquele código, ex. `26162:300:0`). `politica` resume o PTT
(perfis inferidos, ações usadas, blackhole, RPKI das rotas recebidas). A `cobertura` diz quantos vizinhos foram coletados: rejeição é medida só de quem foi coletado.
Contagens exatas sobre as rotas do vizinho; prefixos de amostra por ASN em `/asns/{asn}/politica`.
""",
)
def ixp_rejeicoes(code: str, request: Request, date: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=500), page: int = Query(1, ge=1),
                  motivo: Optional[str] = Query(None, description="Código do motivo (community grande), ex.: 26162:300:0")) -> dict:
    d = _data(request, date)
    b = r.bloco_ixp(request.app.state.store.rs_policy_ixps_doc(d), code.lower(), limit, (page - 1) * limit, motivo)
    if b is None:
        raise HTTPException(404, f"Rejeições e política do PTT '{code}' não publicadas no snapshot {d}.")
    return b


@router.get(
    "/asns/{asn}/politica",
    summary="Política de roteamento de um ASN nos route servers do IX.br: rejeições e communities",
    description="""
Por PTT coletado: `rejeicoes` (rotas rejeitadas por motivo, com até 5 prefixos de amostra por motivo) e `politica` (perfil aberto, seletivo ou restritivo **inferido**, com o critério; ações por classe
e alvo, como "não exportar para AS" e "exportar somente para AS", com a fração das rotas; blackhole; RPKI das rotas recebidas). `evidencia_rs` soma as rotas rejeitadas por tipo, insumo para a prontidão:
evidência do route server, não veredito sobre o ASN. `ixp` restringe a um PTT. Só quem foi coletado tem dado: veja `limites` e a data de cada vizinho.
""",
)
def asn_politica(asn: int, request: Request, date: Optional[str] = Query(None), ixp: Optional[str] = Query(None)) -> dict:
    d = _data(request, date)
    b = r.bloco_asn(request.app.state.store.rs_policy_asns_doc(d), asn, ixp.lower() if ixp else None)
    if b is None:
        raise HTTPException(404, f"AS{asn} sem rejeição nem política coletadas nos route servers do IX.br no snapshot {d}.")
    return b


@router.get(
    "/communities",
    summary="Explorador de communities dos route servers do IX.br: o que cada uma significa e quem a usa",
    description=f"""
Communities (padrão, grande e estendida) das rotas recebidas coletadas, com `classe` ({', '.join(CLASSES)}), rótulo do dicionário do Alice, a `forma` da decodificação e, por PTT, quantos ASNs
a usam, em quantas rotas e os 10 que mais usam. `q` casa um trecho da community ou do rótulo; se for um número, também o ASN-alvo ("não exportar para AS" ou "exportar somente para AS" daquele ASN).
`ixp` restringe a um PTT, `classe` a uma classe. Só vê o que foi coletado (nível 3, PTTs prioritários e rodízio): ausência de uma community na lista não prova que ninguém a usa.
""",
)
def communities(request: Request, date: Optional[str] = Query(None), q: Optional[str] = Query(None, max_length=80), ixp: Optional[str] = Query(None),
                classe: Optional[str] = Query(None, pattern="^[a-z_]{3,30}$"), limit: int = Query(50, ge=1, le=500), page: int = Query(1, ge=1)) -> dict:
    d = _data(request, date)
    b = r.communities(request.app.state.store.rs_policy_communities_doc(d), q, ixp.lower() if ixp else None, classe, limit, (page - 1) * limit)
    if b is None:
        raise HTTPException(404, f"Communities dos route servers não publicadas no snapshot {d}.")
    return b
