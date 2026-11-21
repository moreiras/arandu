# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Histórico: séries por entidade, eventos ("o que mudou") e comparação entre duas datas, sobre `data/history/`.

  * `GET /history/asns/{asn}`, `/history/ixps/{code}`, `/history/operadoras/{cnpj}`, `/history/uf/{uf}` — a série da entidade, uma linha por
    snapshot com histórico (`metrics=` escolhe colunas; `from`/`to` recortam as datas).
  * `GET /changes` e `GET /changes/summary` — eventos por tipo, UF, ASN e estado (padrão: só os confirmados).
  * `GET /snapshots/diff?a=&b=` — resumo agregado da diferença entre dois snapshots.

Os eventos descrevem **diferenças observadas** entre snapshots, sem causa nem intenção e sem nome de empresa (só a chave). Os de provedor
(`provedor_novo`, `provedor_perdido`) vêm de uma inferência (ARC v1): trazem `natureza: "inferido"` e não aparecem na interface.
Acesso (api/auth/access_policy.py): consulta que alcança datas fora dos 2 snapshots mais recentes exige login.
"""
from __future__ import annotations

from typing import Optional

import os

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from api.repos.historico import HistoricoRepo
from api.services import historico as h
from core.site import SITE

router = APIRouter()



def _repo(request: Request) -> HistoricoRepo:
    repo = getattr(request.app.state, "historico", None)
    if repo is None:
        repo = request.app.state.historico = HistoricoRepo(request.app.state.store.base)
    return repo


def _ok(request: Request, fn, *a, **kw):
    try:
        return fn(_repo(request), *a, **kw)
    except h.HistoricoErro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/history/asns/{asn}",
    summary="Série histórica de um ASN",
    description="""
Uma linha por snapshot com histórico: usuários estimados (APNIC), prefixos, PTTs (diretos e cadastrados), provedores confirmados (ARC v1,
inferência), ROAs, ASPA, RPKI por estado e alertas. `metrics` escolhe colunas (apelidos: `users`, `v6users`, `prefixes_v4`, `prefixes_v6`,
`prefixes`, `ixps`, `provedores`, `roa`, `aspa`, `rpki`, `alertas`; ou as colunas); `from` e `to` recortam as datas.
Coluna ausente na linha = sem dado naquele snapshot (por exemplo `n_provedores` antes do bloco de relações), nunca zero inventado.
""",
)
def historico_asn(
    asn: int, request: Request,
    metrics: Optional[str] = Query(None, description="Colunas ou apelidos, separados por vírgula. Padrão: todas."),
    de: Optional[str] = Query(None, alias="from", description="Data inicial (AAAA-MM-DD)."),
    ate: Optional[str] = Query(None, alias="to", description="Data final (AAAA-MM-DD)."),
) -> dict:
    return _ok(request, h.serie_asn, asn, metrics, de, ate)


@router.get(
    "/history/ixps/{code}",
    summary="Série histórica de um PTT",
    description="Uma linha por snapshot: status da coleta, ASNs pares diretos e originadores (total e BR), membros cadastrados, rotas e prefixos por família.",
)
def historico_ixp(
    code: str, request: Request,
    de: Optional[str] = Query(None, alias="from"), ate: Optional[str] = Query(None, alias="to"),
) -> dict:
    return _ok(request, h.serie_ixp, code, de, ate)


@router.get(
    "/history/operadoras/{cnpj}",
    summary="Série histórica de uma operadora (CNPJ)",
    description="""
Soma dos ASNs brasileiros do CNPJ por snapshot, com `users_ma4` (média das amostras de usuários APNIC dos últimos 28 dias) e `n_ma4`
(amostras usadas). A estimativa da APNIC oscila de uma medição para outra: prefira a média. `grupo_id` é só o identificador do grupo societário.
""",
)
def historico_operadora(
    cnpj: str, request: Request,
    de: Optional[str] = Query(None, alias="from"), ate: Optional[str] = Query(None, alias="to"),
) -> dict:
    return _ok(request, h.serie_operadora, cnpj, de, ate)


@router.get(
    "/history/uf/{uf}",
    summary="Série histórica de uma UF",
    description="Soma dos ASNs brasileiros cuja organização tem sede na UF (não é a UF dos usuários), com `users_ma4` e `n_ma4`.",
)
def historico_uf(
    uf: str, request: Request,
    de: Optional[str] = Query(None, alias="from"), ate: Optional[str] = Query(None, alias="to"),
) -> dict:
    return _ok(request, h.serie_uf, uf, de, ate)


@router.get(
    "/changes",
    summary="O que mudou: eventos entre snapshots",
    description="""
Eventos detectados entre snapshots consecutivos com histórico, do mais recente ao mais antigo. Cada evento é uma **diferença observada**
(ASN novo ou sumido, PTT, origem de prefixo, ROA/ASPA, RPKI inválido, outorga, alerta) com o `estado` da janela de confirmação:
`confirmado` (padrão), `pendente` ou `revertido`. `tipo` e `estado` aceitam lista; `estado=todos` não filtra. Eventos de provedor vêm de
uma inferência (ARC v1) e trazem `natureza: "inferido"`.
""",
)
def mudancas(
    request: Request,
    de: Optional[str] = Query(None, alias="from"), ate: Optional[str] = Query(None, alias="to"),
    tipo: Optional[str] = Query(None, description="Tipos separados por vírgula (ex.: asn_novo,mudanca_origem)."),
    uf: Optional[str] = Query(None, description="Sigla da UF (eventos de ASN)."),
    asn: Optional[int] = Query(None, description="Só eventos deste ASN."),
    estado: str = Query("confirmado", description="confirmado | pendente | revertido (lista) | todos."),
    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
    ixp: Optional[str] = Query(None, description="Código do PTT (ex.: sp): só eventos de entrada e saída nele (`ixp_entrada`, `ixp_saida` e as observadas)."),
) -> dict:
    return _ok(request, h.mudancas, de, ate, tipo, uf, asn, estado, limit, offset, ixp)


@router.get(
    "/changes/summary",
    summary="O que mudou: contagem de eventos por tipo, estado e data",
)
def mudancas_resumo(
    request: Request,
    de: Optional[str] = Query(None, alias="from"), ate: Optional[str] = Query(None, alias="to"),
) -> dict:
    return _ok(request, h.mudancas_resumo, de, ate)


@router.get(
    "/snapshots/diff",
    summary="Diferença agregada entre dois snapshots",
    description="Totais do Brasil (soma das UFs e dos PTTs) em cada data, a variação e o resumo dos eventos entre elas. Precisa de histórico nas duas datas.",
)
def diferenca(request: Request, a: str = Query(..., description="Data A (AAAA-MM-DD)."), b: str = Query(..., description="Data B (AAAA-MM-DD).")) -> dict:
    return _ok(request, h.diferenca, a, b)


def bloco_historico(request: Request, escopo: str, chave: str, completo: bool) -> Optional[dict]:
    """O bloco `historico` dos perfis consolidados: `include=historico` traz as datas atuais (`completo=False`) e `include=historico_completo`
    a série inteira, que a política de acesso reserva a quem tem login (api/auth/access_policy.py). A resposta depende só da URL, nunca de
    quem pede: o nginx e o cache da API guardam por URL, e um bloco que mudasse com o nível de acesso vazava a série a anônimos."""
    store = request.app.state.store
    return h.perfil(_repo(request), escopo, chave, completo, list(store.list_snapshots())[-2:])


def pede_historico(extras) -> Optional[bool]:
    """None se o `include` não pede histórico; senão, se pede a série completa."""
    if not extras:
        return None
    if "historico_completo" in extras:
        return True
    return False if "historico" in extras else None


@router.get(
    "/feed/mudancas.atom",
    summary="Feed Atom: o que mudou (só eventos confirmados dos snapshots atuais)",
    description="""
Feed Atom com as diferenças **observadas** entre snapshots, uma entrada por data e tipo, só as confirmadas e só as dos 2 snapshots mais recentes
(a série antiga exige login). Não traz eventos de provedor (inferência) nem nomes de empresas, e não atribui causa nem intenção.
""",
    response_class=Response,
)
def feed_mudancas(request: Request) -> Response:
    base_url = (os.environ.get("APP_BASE_URL") or SITE.url).rstrip("/")
    corpo = h.feed_atom(_repo(request), list(request.app.state.store.list_snapshots())[-2:], base_url)
    return Response(corpo, media_type="application/atom+xml", headers={"Cache-Control": "public, max-age=3600"})
