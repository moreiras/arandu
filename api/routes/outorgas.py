# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Outorgas da Anatel num contrato só: SCM, SMP, STFC e SeAC.

  * `GET /outorgas`           — uma linha por CNPJ, com os serviços que ele tem; filtros combináveis por serviço, UF, porte…
  * `GET /outorgas/stats`     — totais de um serviço (`servico=`) ou dos quatro
  * `GET /outorgas/map`       — GeoJSON de um serviço
  * `GET /outorgas/{cnpj}`    — as outorgas do CNPJ em cada serviço (sem contatos)

As rotas por serviço (`/scms`, `/smps`, `/stfcs`, `/seacs`, `/map/scms`…) seguem como aliases com `Deprecation`.
"""
from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.routes import map as map_routes, scms, seac, smp, stfc
from api.store import Store

router = APIRouter()

SERVICOS = ("SCM", "SMP", "STFC", "SeAC")
_POR_SIGLA = {s.lower(): s for s in SERVICOS}
_SORT = {"razao_social", "cnpj", "uf", "municipio", "acessos", "acessos_fixo", "acessos_movel", "pj_fixo", "pj_movel", "municipios_fixo", "municipios_movel", "outorgas", "servicos", "asns", "data_outorga"}
_DIGITS = re.compile(r"\D")


def _servicos(valor: Optional[str]) -> list[str]:
    """`SCM,smp` → ["SCM", "SMP"]; levanta 400 para serviço desconhecido."""
    if not valor:
        return []
    out = []
    for x in valor.split(","):
        x = x.strip()
        if not x:
            continue
        s = _POR_SIGLA.get(x.lower())
        if s is None:
            raise HTTPException(400, f"servico inválido: {x!r}; válidos: {', '.join(SERVICOS)}")
        if s not in out:
            out.append(s)
    return out


def _data(store: Store, date: Optional[str]) -> str:
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return date_str


def _chave_ordem(campo: str):
    if campo in ("acessos", "acessos_fixo", "acessos_movel", "pj_fixo", "pj_movel", "municipios_fixo", "municipios_movel", "outorgas"):
        return lambda r: r.get(campo) or 0
    if campo == "servicos":
        return lambda r: len(r["servicos"])
    if campo == "asns":
        return lambda r: (len(r["asns"]), r["asns"][0] if r["asns"] else 0)
    if campo == "data_outorga":
        return lambda r: Store._data_br(r.get("data_outorga") or "")
    return lambda r: (r.get(campo) or "").lower()


def montar_lista(store: Store, date_str: str, *, servico: Optional[str] = None, todos: bool = False, uf: Optional[str] = None,
                 municipio: Optional[str] = None, q: Optional[str] = None, com_asn: Optional[bool] = None, ativo: Optional[bool] = None,
                 porte: Optional[str] = None, min_acessos: Optional[int] = None, sort_by: str = "acessos", sort_desc: bool = True,
                 page: int = 1, limit: int = 100) -> dict:
    """Corpo de `GET /outorgas` (e da tool `list_outorgas` do MCP): uma linha por CNPJ, filtros combináveis. Levanta `HTTPException` (400)."""
    quer = _servicos(servico)
    if sort_by not in _SORT:
        raise HTTPException(400, f"sort_by inválido: {sort_by!r}")
    linhas = store.outorgas_unificadas(date_str)
    if quer:
        linhas = [r for r in linhas if (all if todos else any)(s in r["servicos"] for s in quer)]
    if uf:
        linhas = [r for r in linhas if r["uf"].upper() == uf.upper()]
    if municipio:
        linhas = [r for r in linhas if municipio.lower() in r["municipio"].lower()]
    if q:
        ql, qd = q.lower(), _DIGITS.sub("", q)
        linhas = [r for r in linhas if ql in r["razao_social"].lower() or ql in r["nome_fantasia"].lower() or (qd and qd in r["cnpj"])]
    if com_asn is not None:
        linhas = [r for r in linhas if bool(r["asns"]) is com_asn]
    if ativo is not None:
        # com um só serviço, "declara" é o acesso daquele serviço: SCM = fixo, SMP = móvel. Sem isso a aba SCM contava quem só
        # declara móvel (9.919 contra 9.917 CNPJs com SCM no SICI fixo). Com vários ou nenhum, fixo ou móvel (`ativo`).
        campo = {("SCM",): "acessos_fixo", ("SMP",): "acessos_movel"}.get(tuple(quer), "acessos")
        linhas = [r for r in linhas if (r[campo] > 0) is ativo]
    if porte:
        linhas = [r for r in linhas if r["porte"].lower() == porte.lower()]
    if min_acessos is not None:
        linhas = [r for r in linhas if r["acessos"] >= min_acessos]
    linhas = sorted(linhas, key=_chave_ordem(sort_by), reverse=sort_desc)
    total = len(linhas)
    ini = (page - 1) * limit
    return {
        "snapshot_date": date_str, "total": total, "page": page, "limit": limit,
        "pages": (total + limit - 1) // limit if total else 0,
        "items": linhas[ini: ini + limit],
    }


def montar_do_cnpj(store: Store, date_str: str, cnpj: str, servico: Optional[str] = None) -> dict:
    """Corpo de `GET /outorgas/{cnpj}` (e da tool `get_outorgas`): as outorgas do CNPJ por serviço, sem contatos. Levanta `HTTPException`."""
    limpo = _DIGITS.sub("", cnpj)
    if len(limpo) != 14:
        raise HTTPException(400, "CNPJ deve ter 14 dígitos")
    por = store.outorgas_do_cnpj(date_str, limpo)
    quer = _servicos(servico)
    if quer:
        por = {s: v for s, v in por.items() if s in quer}
    if not por:
        raise HTTPException(404, f"CNPJ {limpo} sem outorgas{' nesses serviços' if quer else ''} no snapshot '{date_str}'.")
    return {"snapshot_date": date_str, "cnpj": limpo, "servicos": por}


@router.get(
    "/outorgas",
    summary="Outorgas da Anatel (SCM, SMP, STFC, SeAC): uma linha por CNPJ",
    description="""
Uma linha por CNPJ que tem outorga de qualquer serviço, com `servicos` (os que ele tem), `outorgas`, sede, `asns`, `porte`
(declarado ao SICI) e os acessos declarados (`acessos_fixo`, `acessos_movel`, `acessos`; `ativo` = declarou algum). O filtro
`ativo` com um só serviço (SCM ou SMP) olha o acesso daquele serviço.

`data_outorga` é a mais antiga entre os serviços (`data_outorga_por_servico` traz cada uma); `pj_*`, `municipios_*` e
`tecnologia_fixo` vêm do SICI.

`servico` aceita vários valores (`SCM,SMP`): o CNPJ entra se tem **qualquer** um deles; com `todos=true`, só se tem **todos**.
Os demais filtros se combinam (E). Sem contatos: os valores ficam em `/asns/{asn}/contacts` e `/acessos/operadora/{cnpj}/contacts`
(com login).
""",
)
def listar_outorgas(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    servico: Optional[str] = Query(None, description="SCM, SMP, STFC e/ou SeAC, separados por vírgula. Omitido = todos."),
    todos: bool = Query(False, description="Com vários serviços: exige todos (E) em vez de qualquer um (OU)."),
    uf: Optional[str] = Query(None, description="UF da sede."),
    municipio: Optional[str] = Query(None, description="Município da sede (substring)."),
    q: Optional[str] = Query(None, description="Razão social, nome fantasia ou CNPJ."),
    com_asn: Optional[bool] = Query(None, description="true = só com ASN; false = só sem ASN."),
    ativo: Optional[bool] = Query(None, description="true = só quem declara acessos ao SICI; false = só quem não declara. "
                                  "Com `servico=SCM` sozinho conta só o acesso fixo; com `servico=SMP` sozinho, só o móvel; "
                                  "nos demais casos, fixo ou móvel."),
    porte: Optional[str] = Query(None, description="Porte declarado ao SICI (ex.: Pequeno Porte, Grande Porte)."),
    min_acessos: Optional[int] = Query(None, ge=0),
    sort_by: str = Query("acessos", description=f"Um de: {', '.join(sorted(_SORT))}"),
    sort_desc: bool = Query(True),
) -> dict:
    store: Store = request.app.state.store
    return montar_lista(store, _data(store, date), servico=servico, todos=todos, uf=uf, municipio=municipio, q=q, com_asn=com_asn,
                        ativo=ativo, porte=porte, min_acessos=min_acessos, sort_by=sort_by, sort_desc=sort_desc, page=page, limit=limit)


@router.get(
    "/outorgas/stats",
    summary="Estatísticas das outorgas de um serviço (ou dos quatro)",
    description="Com `servico=SCM` devolve o mesmo corpo de `/scms/stats` (e assim por diante); sem `servico`, `{SCM: …, SMP: …, STFC: …, SeAC: …}`, omitindo os serviços sem dados.",
)
def stats_outorgas(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    servico: Optional[str] = Query(None, description="SCM, SMP, STFC ou SeAC."),
) -> dict:
    chamar = {
        "SCM": scms.scm_stats, "SMP": smp.smp_stats, "STFC": stfc.stfc_stats, "SeAC": seac.seac_stats,
    }
    alvo = _servicos(servico)
    if len(alvo) > 1:
        raise HTTPException(400, "stats aceita um serviço por vez")
    if alvo:
        return chamar[alvo[0]](request, date)
    out = {}
    for s, fn in chamar.items():
        try:
            out[s] = fn(request, date)
        except HTTPException as e:
            if e.status_code != 404:
                raise
    if not out:
        raise HTTPException(404, "Dados de outorgas não disponíveis para este snapshot.")
    return out


@router.get(
    "/outorgas/map",
    summary="Mapa das outorgas de um serviço (GeoJSON)",
    description="Mesmo corpo de `/map/scms`, `/map/smps`, `/map/stfcs` e `/map/seacs`, escolhido por `servico`.",
)
def mapa_outorgas(
    request: Request,
    servico: str = Query(..., description="SCM, SMP, STFC ou SeAC."),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    uf: Optional[str] = Query(None, min_length=2, max_length=2, description="UF (sigla)."),
    com_asn: bool = Query(False, description="Só pontos com ASN identificado."),
) -> dict:
    alvo = _servicos(servico)
    if len(alvo) != 1:
        raise HTTPException(400, "informe um serviço")
    fn = {"SCM": map_routes.map_scms, "SMP": map_routes.map_smps, "STFC": map_routes.map_stfcs, "SeAC": map_routes.map_seacs}[alvo[0]]
    return fn(request, date, uf, com_asn)


@router.get(
    "/outorgas/{cnpj}",
    summary="As outorgas de um CNPJ em cada serviço",
    description="`servicos` = `{SCM: [...], SMP: [...], ...}` com as outorgas do CNPJ, sem telefone nem e-mail. 404 se o CNPJ não tem nenhuma; `servico=` restringe.",
)
def outorgas_do_cnpj(
    request: Request,
    cnpj: str,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    servico: Optional[str] = Query(None, description="Restringe a estes serviços (SCM,SMP,...)."),
) -> dict:
    store: Store = request.app.state.store
    return montar_do_cnpj(store, _data(store, date), cnpj, servico)
