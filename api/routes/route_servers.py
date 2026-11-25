# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Route servers do IX.br (níveis 0 e 1): sessões BGP dos membros vistas no Alice-LG, cruzadas com o cadastro de membros.

  * `GET /ixps/{code}/route-servers` — os route servers do PTT, o resumo e cada membro (sessões up e down, membro down, perto do limite, cadastrado sem sessão).
  * `GET /asns/{asn}/route-servers` — as sessões do ASN em cada PTT.
  * `GET /ranking/route-servers` — membros (ASN × PTT) ordenados por um número medido.
  * Os mesmos blocos vêm em `?include=route_servers` do PTT e do ASN; a coleção `rs_sessoes` do `/query` traz uma linha por sessão.

Fatos medidos no route server na data da coleta, sem causa nem veredito. Contatos não existem aqui: só ASN, nome cadastrado e IP do par na LAN do IX.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import route_servers as r

router = APIRouter()


def _data(request: Request, date: Optional[str]) -> str:
    d = request.app.state.store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return d


@router.get(
    "/ixps/{code}/route-servers",
    summary="Route servers de um PTT: sessões dos membros e divergência com o cadastro",
    description="""
Os route servers do PTT (estado no Alice, rotas importadas, se a consulta funcionou), o resumo (cadastrados com e sem sessão, sessões up e down, membros down
há 7 dias ou mais, membros perto do limite de importação) e os membros. `membros=destaque` (padrão) lista só os que têm algo a dizer: membros down, perto do limite, cadastrados sem sessão,
sessão sem cadastro; `membros=todos` lista todos (São Paulo passa de 2.700 membros). O `estado_rotas` (READY, BUSY, ERROR) é o do cache de rotas do Alice e não diz nada das sessões; o frescor delas é o `vizinhos_em` (`cached_at` do `neighbors`): sessão de route server cujo cache de vizinhos tem mais de 24 h, não tem esse dado ou não foi consultado vem marcada `rs_incerto` e não derruba o membro.
Fonte, data da coleta e limites vêm na resposta.
""",
)
def ixp_route_servers(code: str, request: Request, date: Optional[str] = Query(None), membros: str = Query("destaque", pattern="^(destaque|todos)$")) -> dict:
    d = _data(request, date)
    b = r.bloco_ixp(request.app.state.store.route_servers_ixps_doc(d), code.lower(), membros == "todos")
    if b is None:
        raise HTTPException(404, f"Route servers do PTT '{code}' não publicados no snapshot {d}.")
    return b


@router.get(
    "/asns/{asn}/route-servers",
    summary="Sessões de um ASN nos route servers do IX.br",
    description="Por PTT: se o ASN é cadastrado, as sessões (route server, família, estado, há quantos dias, último erro, rotas e uso do limite de importação) e o resumo.",
)
def asn_route_servers(asn: int, request: Request, date: Optional[str] = Query(None)) -> dict:
    d = _data(request, date)
    b = r.bloco_asn(request.app.state.store.route_servers_asns_doc(d), asn)
    if b is None:
        raise HTTPException(404, f"AS{asn} sem sessão nos route servers do IX.br no snapshot {d}.")
    return b


@router.get(
    "/ranking/route-servers",
    summary="Membros dos route servers ordenados por um número medido",
    description=f"""
Membros (ASN × PTT) em ordem neutra por padrão (`criterio=ptt_asn`: PTT e ASN crescentes, todos os membros com sessão). Os outros critérios ({', '.join(c for c in r.CRITERIOS if c != r.CRITERIO_PADRAO)}) ordenam do maior para o menor número medido e só trazem quem tem o número. `ixp` restringe a um PTT; `apenas_down=true` mantém só os que têm
todas as sessões down há 7 dias ou mais. Cada linha traz o nome cadastrado, as sessões up e down e o maior tempo de queda: dado medido no route server, sem causa
nem juízo, com a data da coleta. O ASN também está em `/asns/{{asn}}/route-servers`.
""",
)
def ranking_route_servers(
    request: Request, date: Optional[str] = Query(None), criterio: str = Query(r.CRITERIO_PADRAO), ixp: Optional[str] = Query(None),
    apenas_down: bool = Query(False), apenas_derrubados: bool = Query(False, include_in_schema=False, description="Alias antigo de `apenas_down`."), limit: int = Query(25, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    d = _data(request, date)
    doc = request.app.state.store.route_servers_ixps_doc(d)
    if not doc:
        raise HTTPException(404, f"Route servers não publicados no snapshot {d}.")
    try:
        return r.ranking(doc, criterio, ixp, apenas_down or apenas_derrubados, limit, (page - 1) * limit)
    except r.RouteServersErro as e:
        raise HTTPException(e.status, e.mensagem)
