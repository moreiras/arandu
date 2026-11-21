# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoints de IXPs — GET /ixps, GET /ixps/{code} e sub-recursos.

Lista os IXPs do IX.br com métricas, serve o documento completo de um IXP
e seus membros/peers. Também serve IXPs externos (PeeringDB) e CDNs.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from api.respostas import JSONResponse

from api.schemas import IXPListResponse, IXPDocumentResponse
from api.store import Store

router = APIRouter()

# Campos grandes separados para o endpoint /members — não incluídos no doc principal
_MEMBER_LIST_FIELDS = frozenset({"asn_direct", "asn_stub", "br_asns_direct", "br_asns_origin"})
# GET /ixps/{code}?include=: o perfil consolidado da página do PTT
_INCLUDES_PTT = frozenset({"membros", "usuarios_estimados", "potencial", "assinantes", "indice", "totais", "historico", "historico_completo", "route_servers", "rejeicoes", "facilities", "portas"})


def _membros(store: Store, date_str: str, code: str, doc: dict, nomes: bool, extras: Optional[set] = None) -> dict:
    """Corpo de `GET /ixps/{code}/members`; também é o bloco `membros` do perfil (`include=`), onde `extras` são os membros cadastrados
    (sem par direto, não estão nas listas) que também precisam de nome."""
    result: dict = {"snapshot_date": date_str, "ixp": code}
    for afi in ("v4", "v6"):
        v = doc.get(afi)
        if isinstance(v, dict):
            result[afi] = {k: v[k] for k in _MEMBER_LIST_FIELDS if k in v}
        else:
            result[afi] = {}
    if nomes:
        asns = {int(a) for afi in ("v4", "v6") for lista in result[afi].values() if isinstance(lista, list)
                for a in lista if isinstance(a, int)} | {int(a) for a in (extras or ())}
        result["nomes"] = store.nomes_asns(date_str, sorted(asns), detalhe=True)
    return result


@router.get(
    "/ixps",
    response_model=IXPListResponse,
    summary="Listar IXPs do IX.br",
    description="""
Retorna a lista compacta de todos os IXPs do IX.br com métricas resumidas por AFI (v6/v4).

Cada entrada inclui contagens de ASNs, prefixos e percentuais de cobertura.
Quando não há dados coletados para um AFI, o campo correspondente é `{"status": "missing"}`.

Use `?status=ok` para ver apenas IXPs com coleta completa, ou `?uf=SP` para filtrar por estado.
""",
)
def list_ixps(
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
        examples=["2026-06-06"],
    ),
    status: Optional[str] = Query(
        None,
        description="Filtro por status de coleta: `ok` | `partial` | `missing`",
        examples=["ok"],
    ),
    uf: Optional[str] = Query(
        None,
        description="Filtro por Unidade Federativa (sigla de 2 letras)",
        examples=["SP"],
    ),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    index = store.ixp_index(date_str)

    if status:
        index = [e for e in index if e.get("status") == status]
    if uf:
        index = [e for e in index if e.get("uf", "").upper() == uf.upper()]

    return {
        "snapshot_date": date_str,
        "count": len(index),
        "ixps": index,
    }


@router.get(
    "/ixps/estimated-users",
    summary="Usuários finais BR estimados visíveis por IXP (todos)",
    description="""
Retorna `{code: estimated_users}` para todos os IXes — usuários finais BR estimados
visíveis via cada IXP (IPv4). Mesma metodologia de `/ixps/{code}/estimated-users`.
Cacheado por snapshot — use `staleTime: Infinity`.
""",
)
def all_ixp_estimated_users(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return store.all_ixp_estimated_users(date_str)


@router.get(
    "/ixps/{code}",
    response_model=IXPDocumentResponse,
    summary="Documento completo de um IXP",
    description="""
Retorna o documento completo de um IXP, com métricas detalhadas separadas por AFI.

**Métricas por AFI (v4 / v6):**
- `asn_direct` — lista completa de ASNs em peering direto
- `br_asns_direct` / `br_asns_origin` — subconjuntos brasileiros
- `br_prefix_coverage_pct` — % do espaço de endereços BR (Registro.br) visível aqui
- `ixp_vs_fulltable_space_pct` — % do espaço global coberto pelos prefixos deste IXP

Quando não há dados coletados para um AFI, o campo retorna `{"status": "missing"}`.

**Códigos de IXP:** `sp`, `rj`, `bsb`, `curitiba`, `poa`, `bel`, `manaus`, `fortaleza`, etc.
Consulte `/api/v1/ixps` para a lista completa.
""",
)
def get_ixp(
    code: str,
    request: Request,
    date: Optional[str] = Query(
        None,
        description="Data do snapshot (YYYY-MM-DD). Omita para usar o mais recente.",
        examples=["2026-06-06"],
    ),
    include: Optional[str] = Query(None, description="Perfil consolidado: blocos extras, separados por vírgula — `membros` (o corpo de `/ixps/{code}/members?nomes=true`, com nome também dos membros cadastrados sem par direto), `usuarios_estimados` (`/estimated-users`), `potencial` (`/potential`) e `assinantes` (`/assinantes`), `indice` (a linha deste PTT em `/ixps`, com as uniões de ASNs) `historico` (série e eventos recentes do PTT dos 2 snapshots atuais; `historico_completo` traz a série inteira e exige login) e `route_servers` (as sessões dos membros nos route servers do IX.br, `/ixps/{code}/route-servers`), `rejeicoes` (rotas rejeitadas e política nos route servers, `/ixps/{code}/rejeicoes`, 25 ASNs), `facilities` (instalações do PeeringDB onde o PTT tem presença), `portas` (portas de PTT externo; sempre `null` no IX.br) e `totais` (`total_asns_br`, `total_asns_global` e `br_apnic_users_total` do `summary` do snapshot). Cada um vem como chave de mesmo nome (`null` se o PTT não tem o dado). Os pares v6 e v4 ficam em `/ixps/{code}/peers`."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    extras = {x.strip() for x in (include or "").split(",") if x.strip()}
    if extras - _INCLUDES_PTT:
        raise HTTPException(400, f"include inválido: {sorted(extras - _INCLUDES_PTT)}; válidos: {sorted(_INCLUDES_PTT)}")

    doc = store.ixp_detail(date_str, code)
    if doc is None:
        raise HTTPException(404, f"IXP '{code}' não encontrado no snapshot '{date_str}'")

    # Retorna versão slim: listas grandes de ASNs ficam em GET /ixps/{code}/members
    slim: dict = {}
    for k, v in doc.items():
        if k in ("v4", "v6") and isinstance(v, dict):
            slim[k] = {fk: fv for fk, fv in v.items() if fk not in _MEMBER_LIST_FIELDS}
        else:
            slim[k] = v

    members = store._load_ixp_members(date_str, code)
    if members:
        slim["asn_members"] = sorted(members)
        slim["ixbr_members_count"] = len(members)

    if not extras:
        return slim
    if "membros" in extras:
        slim["membros"] = _membros(store, date_str, code, doc, True, set(members or ()))
    if "usuarios_estimados" in extras:
        slim["usuarios_estimados"] = store.ixp_estimated_users(date_str, code)
    if "potencial" in extras:
        slim["potencial"] = store.ixp_potential(date_str, code)
    if "assinantes" in extras:
        slim["assinantes"] = store.ixp_assinantes(date_str, code)
    from api.routes.historico import bloco_historico, pede_historico
    if (completo := pede_historico(extras)) is not None:
        slim["historico"] = bloco_historico(request, "ixp", code, completo)
    if "route_servers" in extras:
        from api.services.route_servers import bloco_ixp
        slim["route_servers"] = bloco_ixp(store.route_servers_ixps_doc(date_str), code)
    if "facilities" in extras:
        from api.services.instalacoes import bloco_ixp as _fac_ixp
        slim["facilities"] = _fac_ixp(store.instalacoes_doc(date_str), code)
    if "portas" in extras:
        from api.services.instalacoes import bloco_portas as _portas
        slim["portas"] = _portas(store.portas_externas_doc(date_str), code)
    if "rejeicoes" in extras:
        from api.services.rs_policy import bloco_ixp as _rej_ixp
        slim["rejeicoes"] = _rej_ixp(store.rs_policy_ixps_doc(date_str), code, limit=25)
    if "indice" in extras:
        slim["indice"] = next((e for e in store.ixp_index(date_str) if e.get("code") == code), None)
    if "totais" in extras:
        from api.routes.snapshots import get_snapshot

        resumo = (get_snapshot(date_str, request) or {}).get("summary") or {}
        slim["totais"] = {"total_asns_br": resumo.get("total_asns_br"),
                          "total_asns_global": (resumo.get("global_table") or {}).get("total_asns"),
                          "br_apnic_users_total": resumo.get("br_apnic_users_total")}
    return JSONResponse(slim)


@router.get(
    "/ixps/{code}/members",
    summary="Listas de membros de um IXP (endpoint leve separado)",
    description="""
Retorna as listas grandes de ASNs para cada AFI: `asn_direct`, `asn_stub`,
`br_asns_direct` e `br_asns_origin`. Separado do documento principal (`/ixps/{code}`)
para permitir carregamento progressivo — o doc principal retorna imediatamente com
métricas escalares; este endpoint carrega as tabelas de membros depois.

Sempre retorna HTTP 200. AFIs sem dados retornam dicts vazios.
""",
)
def ixp_members(
    code: str,
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    nomes: bool = Query(False, description="Acrescenta `nomes` = `{asn: {name, uf}}` de todos os ASNs das listas, para a página não baixar o dicionário inteiro."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    doc = store.ixp_detail(date_str, code)
    if doc is None:
        raise HTTPException(404, f"IXP '{code}' não encontrado no snapshot '{date_str}'")

    return _membros(store, date_str, code, doc, nomes)


@router.get(
    "/ixps/{code}/peers",
    summary="Estatísticas por peer direto de um IXP",
    description="""
Retorna estatísticas de prefixos por ASN em peering direto no IXP.

Para cada peer, inclui:
- `total_prefixes` — total de prefixos únicos anunciados
- `own_prefixes` — prefixos originados pelo próprio peer
- `third_prefixes` — prefixos de terceiros repassados pelo peer
- `origin_asns` — número de ASNs distintos originando prefixos via este peer
- `own_space_24` / `third_space_24` — espaço em equivalentes /24

Use `?afi=v6` para dados IPv6. `?peeringdb=1` acrescenta `peeringdb`: as portas que cada participante **declarou** no PeeringDB para este PTT (Mbps) e as
instalações **inferidas** (as instalações da rede no PeeringDB que também abrigam este PTT; o PeeringDB não diz em qual instalação fica cada porta).
""",
)
def ixp_peers(
    code: str,
    request: Request,
    afi: str = Query("v4", description="Família de endereços: v4 ou v6"),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    nomes: bool = Query(False, description="Acrescenta `nomes` = `{asn: {name, uf}}` dos peers."),
    peeringdb: bool = Query(False, description="Acrescenta `peeringdb` com portas declaradas e instalações inferidas."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    result = store.ixp_peers_stats(date_str, code, afi)
    if result is None:
        raise HTTPException(404, f"Dados não disponíveis para IXP '{code}' AFI '{afi}'")

    corpo = {"afi": afi, "peers": result}
    if nomes:
        corpo["nomes"] = store.nomes_asns(date_str, sorted(int(a) for a in result), detalhe=True)
    if peeringdb:
        corpo["peeringdb"] = peeringdb_dos_peers(store, date_str, code, [str(a) for a in result])
    return corpo


def peeringdb_dos_peers(store: Store, date_str: str, code: str, asns: list[str]) -> dict:
    """Portas declaradas no PeeringDB para este PTT (por ASN) e instalações inferidas: as da rede (`netfac`) que também abrigam o PTT (`ixfac`)."""
    portas_doc = store.portas_ixbr_doc(date_str) or {}
    portas = (portas_doc.get("ptts") or {}).get(code.lower(), {})
    inst = store.instalacoes_doc(date_str) or {}
    do_ptt = {str(f["id"]): f.get("nome") for f in (inst.get("instalacoes") or {}).values()
              if any((x or {}).get("code") == code.lower() for x in f.get("ixps") or [])}
    vinc = (store.vinculos_instalacoes_doc(date_str) or {}).get("por_asn") or {}
    instalacoes = {}
    for a in asns:
        comuns = [{"id": int(fid), "nome": do_ptt[str(fid)]} for fid, *_ in vinc.get(a, []) if str(fid) in do_ptt]
        if comuns:
            instalacoes[a] = sorted(comuns, key=lambda x: x["nome"] or "")
    return {
        "portas": {a: portas[a] for a in asns if a in portas},
        "instalacoes": instalacoes,
        "fonte": (portas_doc.get("fonte") or {"nome": "PeeringDB"}),
        "coletado_em": portas_doc.get("coletado_em") or inst.get("coletado_em"),
        "limites": ((portas_doc.get("limites") + " ") if portas_doc.get("limites") else "")
        + "Instalação inferida: as instalações da rede no PeeringDB que também abrigam este PTT; o PeeringDB não diz em qual delas fica cada porta.",
    }


@router.get(
    "/ixps/{code}/assinantes",
    summary="Empresas e assinantes SCM (SICI) dos peers diretos de um IXP",
    description="""
Para cada ASN em peering direto no IXP:

- `asns[asn]` — `cnpj`, `empresa`, badges de outorga (`has_scm`, `has_smp`,
  `has_stfc`, `has_seac`), `usuarios_apnic` e `assinantes_diretos` (acessos SICI
  pf + pj do CNPJ do peer).
- `peers[afi][asn]` — assinantes totais: acessos SICI dos CNPJs de todos os ASNs
  nos AS-paths anunciados pelo peer (ele próprio e seus clientes), deduplicados
  por CNPJ.

No nível do IXP: `assinantes_diretos`/`assinantes_total` e a distribuição
municipal `municipios_diretos`/`municipios_totais`. `mes_referencia` é o mês do
SICI, que difere da data do snapshot.
""",
)
def ixp_assinantes(
    code: str,
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    result = store.ixp_assinantes(date_str, code)
    if result is None:
        raise HTTPException(404, f"IXP '{code}' não encontrado no snapshot '{date_str}'")
    return result


@router.get(
    "/ixps/{code}/estimated-users",
    summary="Usuários finais BR estimados visíveis via o IXP (IPv4)",
    description="""
Estima quantos usuários finais brasileiros são "visíveis" via os prefixos IPv4
originados neste IXP.

Para cada AS BR originador, calcula `usuários_APNIC × (espaço IPv4 visível no IXP /
espaço IPv4 total anunciado do AS)` e soma. Retorna `estimated_users` e
`contributing_asns`. Cacheado por snapshot — use `staleTime: Infinity`.
""",
)
def ixp_estimated_users(
    code: str,
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return store.ixp_estimated_users(date_str, code)


@router.get(
    "/ixps/{code}/potential",
    summary="Indicadores de potencial de crescimento de um PTT",
    description="""
Indicadores de quanto um PTT do IX.br ainda pode crescer:

- `nearby_asn_count` — ASes com sede ou prefixos anunciados a até 80km de
  algum PIX do PTT que ainda não participam diretamente nem originam
  prefixos nele.
- `v4_prefixes_24` / `v6_prefixes_48` — prefixos já anunciados neste PTT
  (route server) ∪ todos os prefixos geolocalizados a até 80km de algum
  PIX — colapsados e contados em equivalentes /24 ou /48.
- `estimated_users_total` — para cada AS BR com prefixos IPv4 na union,
  `apnic_users × min(union_24 / space_v4_global, 1)`. Mesma metodologia
  de `/estimated-users` mas sobre a union de prefixos do potencial.

Cacheado por snapshot — use `staleTime: Infinity`.
""",
)
def ixp_potential(
    code: str,
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    result = store.ixp_potential(date_str, code)
    if result is None:
        raise HTTPException(404, f"IXP '{code}' não encontrado no snapshot '{date_str}'")
    return result


@router.get(
    "/ixps/{code}/hilbert/v4",
    summary="Mapa de densidade Hilbert IPv4 para um IXP",
    description="""
Retorna array de densidade /16 (65536 inteiros) para os prefixos IPv4 anunciados neste IXP.

Sem `peer`: retorna `{all: [65536]}` com todos os prefixos do IXP.

Com `?peer={asn}`: retorna `{own: [65536], third: [65536]}` separando prefixos próprios
(originados pelo peer) de prefixos de terceiros (repassados pelo peer).
""",
)
def ixp_hilbert_v4_endpoint(
    code: str,
    request: Request,
    peer: Optional[int] = Query(None, description="ASN do peer para filtrar (opcional)"),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    result = store.ixp_hilbert_v4(date_str, code, peer)
    if result is None:
        raise HTTPException(404, f"Dados Hilbert não disponíveis para IXP '{code}'")

    return result


@router.get(
    "/ixps/{code}/hilbert/v4/detail",
    summary="Blocos /24 dentro de um /8 para zoom do Hilbert IPv4",
)
def ixp_hilbert_v4_detail_endpoint(
    code: str,
    request: Request,
    slash8: int = Query(..., description="Número do bloco /8 (0-255)"),
    peer: Optional[int] = Query(None, description="ASN do peer (opcional)"),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    result = store.ixp_hilbert_v4_detail(date_str, code, slash8, peer)
    if result is None:
        raise HTTPException(404, f"Dados não disponíveis para IXP '{code}' /8 '{slash8}'")
    return result


@router.get(
    "/ixps/{code}/hilbert/v6",
    summary="Mapa de presença Hilbert IPv6 (esparso) para um IXP",
    description="""
Retorna índices de células /32 ativas por bloco RIR para os prefixos IPv6 deste IXP.

Sem `peer`: retorna `{all: {legacy: [...], lacnic: [...], ...}}`.

Com `?peer={asn}`: retorna `{own: {...}, third: {...}}` separando prefixos próprios
(originados pelo peer) de prefixos de terceiros (repassados pelo peer).
""",
)
def ixp_hilbert_v6_endpoint(
    code: str,
    request: Request,
    peer: Optional[int] = Query(None, description="ASN do peer para filtrar (opcional)"),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    result = store.ixp_hilbert_v6(date_str, code, peer)
    if result is None:
        raise HTTPException(404, f"Dados Hilbert IPv6 não disponíveis para IXP '{code}'")

    return result


@router.get(
    "/ixps/{code}/nearby",
    summary="ASes com prefixos próximos a um PTT, por status e gap de anúncio",
    description="""
Para o PTT `code`, lista os ASes cujos prefixos BR geolocalizados estão a ≤ `radius_km` de algum PIX, classificados por presença
no PTT (direct / origin / absent) e com a contagem de prefixos próximos **ainda não anunciados** no PTT. É o detalhamento por AS
do que `/ixps/{code}/potential` resume (raio fixo de 80 km); `/analytics/ixps/{code}/nearby` é o alias antigo.
""",
)
def ixp_nearby_do_ptt(
    code: str,
    request: Request,
    radius_km: float = Query(80.0, gt=0, le=2000, description="Raio em km a partir dos PIX."),
    limit: int = Query(500, ge=1, le=5000, description="Máximo de ASes retornados."),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    from api.routes.query import ixp_nearby
    return ixp_nearby(code, request, radius_km, limit, date)
