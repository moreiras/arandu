# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoints de CDNs e CAPs — GET /cdns.

Serve a presença de CDNs (Content Delivery Networks) e CAPs (Content Anchor
Points) nos PTTs do IX.br, com a lista de IXPs em que cada CDN está presente.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.store import Store

router = APIRouter()


_ALCANCE_CACHE: dict = {}


@router.get(
    "/cdns/alcance",
    summary="Alcance de cada CDN por PTT: fração dos usuários BR em ASes membros dos PTTs onde ela é membro",
    description="""
Por CDN: a fração dos usuários estimados pela APNIC, nos ASes do Brasil, que estão em ASes **membros de algum PTT do IX.br onde a CDN também é membro** (lista de membros do IX.br, não sessão observada), no país e por UF da sede
do AS. Estimativa: usuários se repetem entre ASes da mesma operadora, membro registrado não quer dizer que o tráfego da CDN passe ali, e não mede tráfego nem qualidade.
""",
)
def cdns_alcance(request: Request, date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD).")) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    pres = store.cdn_presence(date_str)
    if pres is None:
        raise HTTPException(404, "Dados de presença de CDNs não disponíveis para este snapshot")
    if date_str not in _ALCANCE_CACHE:
        from api.services.interconexao import alcance_cdns
        idx = {a["asn"]: a for a in store.asn_index(date_str) if a.get("is_br") and a.get("apnic_users")}
        uf_de = {int(a): v.get("uf") for a, v in ((store.seguranca_doc(date_str) or {}).get("asns") or {}).items() if v.get("uf")}
        membros = {int(a): v.get("m", []) for a, v in store.asn_ix_presence(date_str).get("asns", {}).items()}
        _ALCANCE_CACHE[date_str] = alcance_cdns(pres["cdns"], membros, {a: x["apnic_users"] for a, x in idx.items()}, uf_de)
        while len(_ALCANCE_CACHE) > 2:
            _ALCANCE_CACHE.pop(next(iter(_ALCANCE_CACHE)))
    return {"snapshot_date": date_str, **_ALCANCE_CACHE[date_str]}


@router.get(
    "/cdns/presence",
    summary="Matriz de presença de CDNs nos IXPs",
    description="""
Retorna matriz de presença de CDNs/provedores nos IXPs do IX.br e externos. Em cada CDN, `ixbr` são os PTTs do IX.br onde um ASN da CDN consta no cadastro de participantes (membro);
`ixbr_rs` os que, além de membro, têm sessão com o route server; `ixbr_sem_rs` os de membro sem sessão observada (pode haver peering bilateral, que o route server não vê);
`ixbr_origem` os PTTs onde a CDN não é membro mas prefixos dela aparecem nas rotas, por outro participante (inferido, não indica cache local); `ixbr_sem_coleta` os PTTs sem coleta válida do looking glass;
`asns_sem_documento` os ASNs da lista curada sem documento no snapshot. Calculado na leitura, também para snapshots antigos.
""",
)
def get_cdn_presence(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    data = store.cdn_presence(date_str)
    if data is None:
        raise HTTPException(404, "Dados de presença de CDNs não disponíveis para este snapshot")

    return _com_estados(store, date_str, data)


@router.get(
    "/cdns/mudancas",
    summary="Mudanças na matriz de CDNs entre dois snapshots, com regra de comparabilidade",
    description="""
Diferença observada no cadastro de membros dos PTTs do IX.br entre dois snapshots (`a` anterior a `b`): CDNs que passaram a constar (`entradas`) ou deixaram de constar (`saidas`) como
membro de um PTT. Não diz que a CDN ligou ou desligou serviço, nem a causa. `catalogo` traz à parte as mudanças de curadoria da lista de CDNs (CDN incluída ou retirada, ASN incluído ou retirado)
e `nao_comparaveis` os pares CDN e PTT que não entram na conta (conjunto de ASNs da CDN diferente nas duas datas ou PTT sem lista de membros numa delas), com o motivo. Ordem neutra: por CDN e PTT.
""",
)
def cdns_mudancas(request: Request, a: str = Query(..., description="Data A, a mais antiga (AAAA-MM-DD)."), b: str = Query(..., description="Data B (AAAA-MM-DD).")) -> dict:
    import re
    from api.services import cdn_mudancas as cm

    store: Store = request.app.state.store
    for nome, v in (("a", a), ("b", b)):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise HTTPException(400, f"`{nome}` deve ser uma data AAAA-MM-DD; recebido {v!r}")
    da, db = sorted((a, b))
    datas = set(store.list_snapshots())
    docs = {}
    for d in (da, db):
        if d not in datas or store.cdn_presence(d) is None:
            raise HTTPException(404, f"Sem dados de presença de CDNs em {d}.")
        docs[d] = store.cdn_presence(d)
    return cm.mudancas(docs[da], docs[db], store.ixp_index(da), store.ixp_index(db))


#: estados de cada CDN por PTT (membro com sessão, membro sem sessão, só via outro AS), por data: o documento de cada ASN da lista curada é lido uma vez
_ESTADOS_CACHE: dict = {}


def _com_estados(store: Store, date_str: str, data: dict) -> dict:
    from api.services import cdn_estados as ce

    if date_str not in _ESTADOS_CACHE:
        direto: dict[str, set[int]] = {}
        coleta_ok: dict[str, bool] = {}
        for e in store.ixp_index(date_str):
            code = e.get("code")
            doc = (store.ixp_detail(date_str, code) or {}) if code else {}
            fams = [doc.get(a) for a in ("v6", "v4") if isinstance(doc.get(a), dict) and doc[a].get("coleta") == "ok"]
            direto[code] = {a for f in fams for a in f.get("asn_direct") or []}
            coleta_ok[code] = bool(fams)

        def origem_de(asn: int):
            d = store.asn_detail(date_str, asn)
            return None if d is None else set(d.get("ixps_origin") or [])

        _ESTADOS_CACHE[date_str] = ce.estados(data.get("cdns") or [], direto, coleta_ok, origem_de)
        while len(_ESTADOS_CACHE) > 2:
            _ESTADOS_CACHE.pop(next(iter(_ESTADOS_CACHE)))
    est = _ESTADOS_CACHE[date_str]
    return {**data, "cdns": [{**c, **est.get(c["name"], {})} for c in data.get("cdns") or []], "estados": ce.ESTADOS, "estados_limites": ce.LIMITES}
