# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Instalações do PeeringDB.

  * `GET /facilities` e `GET /facilities/{id}` — datacenters e pontos de interconexão do Brasil, com PTTs, carriers, campus e as redes vinculadas.
  * `GET /ixps/{code}/facilities` e `GET /ixps/{code}/portas` — instalações de um PTT (IX.br ou externo) e as portas dos PTTs externos.
  * `GET /asns/{asn}/facilities` e `GET /asns/{asn}/peering` — instalações do ASN e atributos de peering autodeclarados (escopo, IPv6, multicast, looking glass, route server).
  * Os mesmos blocos vêm em `?include=facilities,peering` do ASN e `?include=facilities,portas` do PTT; coleções `facilities`, `facilidades_rede` e `redes_peering` do `/query`.

Cadastro autodeclarado no PeeringDB, com atribuição e data da coleta. O indicador `cadastro` é inferência pelas datas de atualização, sem veredito sobre a empresa. Sem contatos.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.services import instalacoes as s

router = APIRouter()


def _data(request: Request, date: Optional[str]) -> str:
    d = request.app.state.store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return d


def _doc(request: Request, d: str) -> dict:
    doc = request.app.state.store.instalacoes_doc(d)
    if not doc:
        raise HTTPException(404, f"Instalações do PeeringDB não publicadas no snapshot {d}.")
    return doc


@router.get(
    "/facilities",
    summary="Instalações (datacenters, pontos de interconexão) do PeeringDB",
    description=f"""
Instalações cadastradas no PeeringDB no Brasil (`pais=BR`, o padrão; `pais=todos` inclui as de outros países que abrigam PTTs externos cadastrados), com cidade, UF, coordenadas, organização,
número de redes vinculadas, PTTs, carriers e o indicador `cadastro` (`recente`, `parado` ou `antigo`, pela data da última atualização do registro: **inferência** que mede a manutenção do cadastro, não a operação da instalação).
Filtros: `uf`, `q` (nome, organização ou cidade), `ptt` (código do PTT), `cadastro`, `com_ptt`, `com_carrier`. Ordem (`ordem`): {'; '.join(f'`{k}` = {v}' for k, v in s.ORDENS.items())}.
Dado autodeclarado no PeeringDB (https://www.peeringdb.com); fonte, data da coleta e limites vêm na resposta.
""",
)
def list_facilities(
    request: Request, date: Optional[str] = Query(None), pais: Optional[str] = Query(None, description="País ISO (padrão BR); `todos` inclui as instalações de PTTs externos."),
    uf: Optional[str] = Query(None), q: Optional[str] = Query(None, max_length=80), ptt: Optional[str] = Query(None, max_length=60), cadastro: Optional[str] = Query(None),
    com_ptt: bool = Query(False), com_carrier: bool = Query(False), ordem: str = Query("redes"), limit: int = Query(100, ge=1, le=500), page: int = Query(1, ge=1),
) -> dict:
    d = _data(request, date)
    try:
        site = {e["code"]: e.get("name") or e["code"] for e in request.app.state.store.ixp_index(d) if e.get("code")}
        return s.lista(_doc(request, d), pais, uf, q, ptt, cadastro, com_ptt, com_carrier, ordem, limit, (page - 1) * limit, site)
    except s.InstalacoesErro as e:
        raise HTTPException(e.status, e.mensagem)


@router.get(
    "/facilities/{fac_id}",
    summary="Uma instalação do PeeringDB com PTTs, carriers e redes vinculadas",
    description="""
Instalação do PeeringDB: organização, localização, datas de criação e atualização, o indicador `cadastro` (inferido das datas), os PTTs onde o cadastro diz que ela está (`ixps`, com o código do Arandurapé quando o PTT é conhecido),
carriers, campus e as redes vinculadas (`redes`, só nas instalações do Brasil). Vínculo é declaração no cadastro: não indica tráfego nem contrato.
`?include=redes_perfil` acrescenta a cada rede do Brasil a situação em cada PTT do IX.br do prédio (`situacao`: sessão com o route server, no cadastro sem sessão, só origina [inferido] ou sem presença),
usuários estimados do APNIC (`usuarios_apnic`) e IPv6, e o resumo por PTT em `redes_perfil`; PTTs externos vêm como "sem dado de sessão".
""",
)
def get_facility(
    fac_id: int, request: Request, date: Optional[str] = Query(None),
    include: Optional[str] = Query(None, description="`redes_perfil`: a situação de cada rede do Brasil em cada PTT do IX.br do prédio (sessão com o route server, no cadastro sem sessão, só origina, sem presença), com usuários APNIC e IPv6, e o resumo por PTT."),
) -> dict:
    d = _data(request, date)
    store = request.app.state.store
    extras = {x.strip() for x in (include or "").split(",") if x.strip()}
    if extras - {"redes_perfil"}:
        raise HTTPException(400, f"include inválido: {sorted(extras - {'redes_perfil'})}; válido: ['redes_perfil']")
    r = s.detalhe(_doc(request, d), store.vinculos_instalacoes_doc(d), fac_id)
    if r is None:
        raise HTTPException(404, f"Instalação {fac_id} não encontrada no snapshot {d}.")
    if "redes_perfil" in extras and r.get("escopo") == "brasil":
        r = _com_redes_perfil(store, d, r)
    return r


def _com_redes_perfil(store, d: str, r: dict) -> dict:
    """Junta ao detalhe os documentos dos PTTs do IX.br do prédio (cadastro, sessão com o route server e originadores) e o índice de ASNs: tudo já carregado e em cache na API."""
    ptts: dict[str, dict] = {}
    externos = []
    for x in r.get("ixps") or []:
        doc = store.ixp_detail(d, x["code"]) if x.get("tipo") == "ixbr" and x.get("code") else None
        if doc is None:
            externos.append({k: x.get(k) for k in ("ix_id", "code", "nome", "tipo")})
            continue
        fam = {a: (doc.get(a) or {}) for a in ("v6", "v4")}
        ptts[x["code"]] = {"nome": x.get("nome") or doc.get("name") or x["code"], "coleta": {a: f.get("coleta") or "missing" for a, f in fam.items()},
                           "direto": {a for f in fam.values() if f.get("coleta") == "ok" for a in f.get("asn_direct") or []},
                           "origem": {a for f in fam.values() if f.get("coleta") == "ok" for a in f.get("br_asns_origin") or []},
                           "membros": store._load_ixp_members(d, x["code"])}
    mapa = store.asn_map(d)
    return s.redes_perfil(r, ptts, externos, lambda a: {"usuarios": (mapa.get(a) or {}).get("apnic_users"), "ipv6": (mapa.get(a) or {}).get("has_ipv6")})


@router.get(
    "/ixps/{code}/facilities",
    summary="Instalações de um PTT (IX.br ou externo) no PeeringDB",
    description="Instalações onde o PeeringDB diz que o PTT tem presença, com o número de redes de cada uma. Cadastro autodeclarado; o PTT pode estar em mais de uma instalação.",
)
def ixp_facilities(code: str, request: Request, date: Optional[str] = Query(None)) -> dict:
    d = _data(request, date)
    b = s.bloco_ixp(request.app.state.store.instalacoes_doc(d), code.lower())
    if b is None:
        raise HTTPException(404, f"PTT '{code}' sem instalação cadastrada no PeeringDB no snapshot {d}.")
    return b


@router.get(
    "/ixps/{code}/portas",
    summary="Portas (velocidade declarada) de um PTT externo no PeeringDB",
    description="""
Para um PTT externo cadastrado: quantas portas, quantos membros, a distribuição por velocidade (Mbps), a mediana, a maior e a soma das velocidades. A soma é capacidade contratada declarada,
não tráfego nem utilização. Só PTTs externos (o IX.br não entra neste produto). Cadastro autodeclarado no PeeringDB.
""",
)
def ixp_portas(code: str, request: Request, date: Optional[str] = Query(None)) -> dict:
    d = _data(request, date)
    b = s.bloco_portas(request.app.state.store.portas_externas_doc(d), code.lower())
    if b is None:
        raise HTTPException(404, f"PTT externo '{code}' sem portas publicadas no snapshot {d}.")
    return b


@router.get(
    "/asns/{asn}/facilities",
    summary="Instalações do Brasil onde uma rede declara estar (PeeringDB)",
    description="Instalações do Brasil a que o PeeringDB vincula o ASN (`netfac`), com a data do vínculo e os PTTs de cada instalação. Cadastro autodeclarado; instalações no exterior não são coletadas.",
)
def asn_facilities(asn: int, request: Request, date: Optional[str] = Query(None)) -> dict:
    d = _data(request, date)
    store = request.app.state.store
    b = s.bloco_asn(store.instalacoes_doc(d), store.vinculos_instalacoes_doc(d), asn)
    if b is None:
        raise HTTPException(404, f"AS{asn} sem instalação do Brasil vinculada no PeeringDB no snapshot {d}.")
    return b


@router.get(
    "/asns/{asn}/peering",
    summary="Atributos de peering autodeclarados de uma rede (PeeringDB)",
    description="""
Escopo geográfico, suporte a IPv6, multicast e unicast, se a rede declara não usar route server, URLs de looking glass e de route server, datas de criação e atualização do registro e o indicador
`cadastro` (inferido das datas), mais as portas da rede nos PTTs externos. Autodeclarado: pode estar desatualizado e as URLs não são verificadas.
""",
)
def asn_peering(asn: int, request: Request, date: Optional[str] = Query(None)) -> dict:
    d = _data(request, date)
    store = request.app.state.store
    b = s.bloco_peering(store.atributos_rede_doc(d), store.portas_externas_doc(d), store.vinculos_instalacoes_doc(d), asn)
    if b is None:
        raise HTTPException(404, f"AS{asn} sem registro de rede no PeeringDB no snapshot {d}.")
    return b
