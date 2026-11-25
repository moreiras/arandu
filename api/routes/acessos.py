# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoints de acessos de banda larga fixa declarados ao SICI (Anatel).

O SICI é a declaração mensal obrigatória das prestadoras. Os dados servidos aqui têm
DUAS datas: a do snapshot (`snapshot_date`) e o mês de referência da declaração
(`mes_referencia`) — sempre cite as duas.

Duas regras de leitura que valem para todos os endpoints:

  * `acessos_compartilhados` — quando um CNPJ tem mais de um ASN, o total é atribuído
    integralmente a CADA ASN. Somar ASes do mesmo CNPJ conta o mesmo assinante várias
    vezes. Agregue por CNPJ ou por grupo econômico.
  * `capacidade_mbps` é capacidade **contratada** (Σ velocidade × acessos), não
    capacidade de trânsito nem de backhaul. Links de backbone declarados como acesso
    distorcem a média — por isso `velocidade_mediana_mbps` acompanha a média, e a
    variante `_internet` exclui LINHA_DEDICADA/M2M/OUTROS.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.auth.deps import require_user
from api.ratelimit import limiter, LIMIT_CONTACTS
from api import contatos_cota
from api.routes.asns import _contacts_available, montar_contatos_operadora
from api.services.onde_atua import enriquecer_municipios_operadora
from api.store import Store

router = APIRouter()
_log = logging.getLogger("arandurape")

_DIGITS = re.compile(r"\D")

_OPERADORA_SORT = {"acessos", "acessos_pf", "acessos_pj", "capacidade_mbps",
                   "municipios", "velocidade_media_mbps", "empresa", "cnpj"}


def _meta(store: Store, date_str: str) -> dict:
    meta = store.sici_meta(date_str)
    if not meta:
        raise HTTPException(
            404, "Dados de acessos (SICI) não disponíveis para este snapshot. "
                 "Rode a coleta anatel_sici e a etapa sici primeiro.")
    return meta


@router.get(
    "/acessos/stats",
    summary="Estatísticas nacionais de acessos de banda larga fixa (SICI/Anatel)",
    description="Totais do mês de referência, série histórica mensal, mix de "
                "tecnologia e meio, e as maiores operadoras.",
)
def acessos_stats(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    top: int = Query(20, ge=1, le=200, description="Quantas operadoras no ranking."),
    servico: str = Query("fixa", pattern="^(fixa|movel)$", description="`fixa` (banda larga fixa, padrão) ou `movel` (telefonia móvel, SMP): o mesmo contrato para os dois."),
) -> dict:
    if servico == "movel":
        from api.routes import acessos_movel as _m
        return _m.acessos_movel_stats(request, date, top)
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    meta = _meta(store, date_str)

    all_rows = store.operadora_index(date_str)
    rows = [r for r in all_rows if r.get("ativo")]

    # Cobertura de declaração: quantos licenciados (outorga SCM) de fato reportam ao
    # SICI, no total e restrito aos que têm ASN no Registro.br com o mesmo CNPJ.
    licenciados = [r for r in all_rows if r.get("licenciado")]
    licenciados_com_asn = [r for r in licenciados if r.get("asns")]
    licenciados_informaram = [r for r in licenciados if r.get("ativo")]
    licenciados_com_asn_informaram = [r for r in licenciados_com_asn if r.get("ativo")]
    cobertura_declaracao = {
        "licenciados": len(licenciados),
        "informaram_sici": len(licenciados_informaram),
        "pct_informaram_sici": round(100 * len(licenciados_informaram) / len(licenciados), 1)
            if licenciados else None,
        "licenciados_com_asn": len(licenciados_com_asn),
        "com_asn_informaram_sici": len(licenciados_com_asn_informaram),
        "pct_com_asn_informaram_sici": round(
            100 * len(licenciados_com_asn_informaram) / len(licenciados_com_asn), 1)
            if licenciados_com_asn else None,
    }

    por_tecnologia: dict[str, int] = {}
    por_meio: dict[str, int] = {}
    por_uf: dict[str, dict] = {}
    total_pf = total_pj = 0
    for r in rows:
        total_pf += r.get("acessos_pf", 0)
        total_pj += r.get("acessos_pj", 0)
    for ibge, mun in store.sici_municipios(date_str).items():
        uf = mun.get("uf") or "??"
        slot = por_uf.setdefault(uf, {"acessos": 0, "pf": 0, "pj": 0})
        slot["acessos"] += mun.get("acessos", 0)
        slot["pf"] += mun.get("pf", 0)
        slot["pj"] += mun.get("pj", 0)
    data = store._load_sici(date_str) or {}
    for agg in data.get("cnpjs", {}).values():
        for k, v in agg.get("por_tecnologia", {}).items():
            por_tecnologia[k] = por_tecnologia.get(k, 0) + v
        for k, v in agg.get("por_meio", {}).items():
            por_meio[k] = por_meio.get(k, 0) + v

    ranking = sorted(rows, key=lambda r: -r.get("acessos", 0))[:top]

    # Segunda ótica do mesmo ranking: maiores ASNs BR por usuários estimados (APNIC),
    # cruzados de volta ao CNPJ declarante no SICI — permite comparar o lado
    # "estimado por medição de tráfego" com o "declarado à Anatel" para os mesmos
    # operadores.
    asn_rows = [a for a in store.asn_index(date_str) if a.get("is_br") and a.get("apnic_users")]
    asn_rows.sort(key=lambda a: -(a.get("apnic_users") or 0))
    rows_by_cnpj = {r["cnpj"]: r for r in all_rows}
    top_por_apnic: list[dict] = []
    seen_cnpj: set[str] = set()
    for a in asn_rows:
        cnpj = store.sici_cnpj_for_asn(date_str, a["asn"])
        if not cnpj or cnpj in seen_cnpj:
            continue
        seen_cnpj.add(cnpj)
        op = rows_by_cnpj.get(cnpj)
        top_por_apnic.append({
            "cnpj": cnpj, "asn": a["asn"],
            "empresa": (op or {}).get("empresa") or a.get("name", ""),
            "apnic_users": a.get("apnic_users"),
            "acessos_sici": (op or {}).get("acessos"),
        })
        if len(top_por_apnic) >= top:
            break

    return {
        "snapshot_date": date_str,
        **meta,
        "acessos_pf": total_pf,
        "acessos_pj": total_pj,
        "operadoras_ativas": len(rows),
        "municipios_atendidos": len(store.sici_municipios(date_str)),
        "cobertura_declaracao": cobertura_declaracao,
        "por_tecnologia": dict(sorted(por_tecnologia.items(), key=lambda kv: -kv[1])),
        "por_meio": dict(sorted(por_meio.items(), key=lambda kv: -kv[1])),
        "por_uf": por_uf,
        "distrib_velocidade": store.sici_distrib_velocidade(date_str),
        "serie_total": store.sici_serie_total(date_str),
        "top_operadoras": [
            {k: r.get(k) for k in ("cnpj", "empresa", "razao_social", "acessos",
                                   "acessos_pf", "acessos_pj", "municipios",
                                   "tecnologia", "asns", "grupo_economico")}
            for r in ranking
        ],
        "top_operadoras_por_asn": top_por_apnic,
    }


@router.get(
    "/acessos/operadoras",
    summary="Listar operadoras por acessos declarados",
    description="Uma linha por CNPJ. Inclui licenciados sem acesso declarado quando "
                "`ativo=false` (metade da base de outorgas SCM não declara operação).",
)
def acessos_operadoras(
    request: Request,
    date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    uf: Optional[str] = Query(None, description="UF da sede (cadastro SCM)."),
    q: Optional[str] = Query(None, description="Busca por empresa, razão social ou CNPJ."),
    com_asn: Optional[bool] = Query(None, description="Filtra por ter/não ter ASN brasileiro vinculado (mesmo CNPJ, mesma raiz ou marca curada; ver `asn_vinculo`)."),
    ativo: Optional[bool] = Query(None, description="true = só quem declara acesso no mês; false = só quem não declara. "
                                  "Omitido: `fixa` = true (a lista do SICI fixo); `movel` = todas (outorgadas e credenciadas "
                                  "do SMP, com e sem declaração)."),
    min_acessos: Optional[int] = Query(None, ge=0),
    tecnologia: Optional[str] = Query(None, description="Tecnologia predominante (ex: FTTH)."),
    sort_by: str = Query("acessos", description=f"Um de: {', '.join(sorted(_OPERADORA_SORT))}"),
    sort_desc: bool = Query(True),
    servico: str = Query("fixa", pattern="^(fixa|movel)$", description="`fixa` (banda larga fixa, padrão) ou `movel` (telefonia móvel, SMP): o mesmo contrato para os dois."),
) -> dict:
    if servico == "movel":
        # o padrão `true` da lista fixa não vale para o móvel: omitido = o universo (OPERADORAS-E2, a aba SMP mostrava 17 de 256)
        from api.routes import acessos_movel as _m
        return _m.acessos_movel_operadoras(request, date, page, limit, uf, q, com_asn, ativo, min_acessos, sort_by, sort_desc)
    if ativo is None:
        ativo = True
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    meta = _meta(store, date_str)

    rows = store.operadora_index(date_str)
    if ativo is not None:
        rows = [r for r in rows if bool(r.get("ativo")) is ativo]
    if uf:
        u = uf.upper()
        rows = [r for r in rows if (r.get("uf_sede") or "").upper() == u]
    if com_asn is not None:
        rows = [r for r in rows if bool(r.get("com_asn")) is com_asn]
    if min_acessos is not None:
        rows = [r for r in rows if r.get("acessos", 0) >= min_acessos]
    if tecnologia:
        t = tecnologia.upper()
        rows = [r for r in rows if (r.get("tecnologia") or "").upper() == t]
    if q:
        ql = q.lower()
        qd = _DIGITS.sub("", q)
        rows = [
            r for r in rows
            if ql in (r.get("empresa") or "").lower()
            or ql in (r.get("razao_social") or "").lower()
            or ql in (r.get("nome_fantasia") or "").lower()
            or (qd and qd in r.get("cnpj", ""))
        ]

    field = sort_by if sort_by in _OPERADORA_SORT else "acessos"
    if field in ("empresa", "cnpj"):
        rows.sort(key=lambda r: (r.get(field) or "").lower(), reverse=sort_desc)
    else:
        rows.sort(key=lambda r: r.get(field) or 0, reverse=sort_desc)

    total = len(rows)
    start = (page - 1) * limit
    return {
        "snapshot_date": date_str,
        "mes_referencia": meta["mes_referencia"],
        "total": total, "page": page, "limit": limit,
        "pages": (total + limit - 1) // limit if total else 0,
        "items": rows[start : start + limit],
    }


def _asn_rede_detail(full: dict) -> dict:
    """Resumo de um ASN para a tabela por-ASN da página da operadora."""
    alerts = full.get("alerts") or []
    return {
        "asn": full.get("asn"),
        "name": full.get("name") or "",
        "apnic_users": full.get("apnic_users"),
        "apnic_v6_users": full.get("apnic_v6_users"),
        "rir_prefixes_v4_count": full.get("rir_prefixes_v4_count") or 0,
        "rir_prefixes_v6_count": full.get("rir_prefixes_v6_count") or 0,
        "global_prefixes_v4_count": full.get("global_prefixes_v4_count") or 0,
        "global_prefixes_v6_count": full.get("global_prefixes_v6_count") or 0,
        "has_rpki": bool(full.get("roa_list")),
        "has_aspa": bool(full.get("aspa_providers")),
        "ixps_direct_count": len(full.get("ixps_direct") or []),
        "alerts_count": len(alerts),
    }


def _operadora_rede(store: Store, date_str: str, asns: list[int], vinculos: Optional[dict[int, str]] = None) -> Optional[dict]:
    """Agrega dados de BGP/RPKI/IX.br/alertas de todos os ASNs de um CNPJ.

    `asns` são os da mesma pessoa jurídica (vínculos `cnpj` e `raiz`, D5); `vinculos` ({asn: vínculo}) marca cada linha de `asns` da resposta.

    Soma direta (usuários, blocos) + união (IXPs, RPKI/ASPA) + alertas agrupados
    por categoria/severidade (concatenados, nunca somados — cada alerta é de um
    ASN específico). Lê os documentos de ASN já publicados (alerts pré-computados
    no `saude_asn`), sem recalcular nada.
    """
    if not asns:
        return None
    docs = [d for d in (store.asn_full(date_str, a) for a in asns) if d]
    if not docs:
        return None

    ixps_direct = sorted({code for d in docs for code in (d.get("ixps_direct") or [])})
    ixps_origin = sorted({code for d in docs for code in (d.get("ixps_origin") or [])})

    alerts_by_key: dict[tuple[str, str], dict] = {}
    total_alerts = 0
    for d in docs:
        for a in (d.get("alerts") or []):
            total_alerts += 1
            key = (a.get("category", ""), a.get("severity", ""))
            entry = alerts_by_key.setdefault(key, {
                "category": a.get("category", ""), "severity": a.get("severity", ""),
                "count": 0, "asns": [],
            })
            entry["count"] += 1
            entry["asns"].append({"asn": d.get("asn"), "title": a.get("title", "")})

    _SEVERITY_RANK = {"critico": 0, "aviso": 1, "info": 2}
    alertas_por_categoria = sorted(
        alerts_by_key.values(),
        key=lambda e: (_SEVERITY_RANK.get(e["severity"], 9), -e["count"]),
    )

    return {
        "asn_count": len(docs),
        "total_apnic_users": sum(d.get("apnic_users") or 0 for d in docs),
        "total_apnic_v6_users": sum(d.get("apnic_v6_users") or 0 for d in docs),
        "total_rir_prefixes_v4": sum(d.get("rir_prefixes_v4_count") or 0 for d in docs),
        "total_rir_prefixes_v6": sum(d.get("rir_prefixes_v6_count") or 0 for d in docs),
        "total_global_prefixes_v4": sum(d.get("global_prefixes_v4_count") or 0 for d in docs),
        "total_global_prefixes_v6": sum(d.get("global_prefixes_v6_count") or 0 for d in docs),
        "ixps_direct": ixps_direct,
        "ixps_origin": ixps_origin,
        "has_rpki": any(d.get("roa_list") for d in docs),
        "has_aspa": any(d.get("aspa_providers") for d in docs),
        "alertas": {"total": total_alerts, "por_categoria": alertas_por_categoria},
        "asns": [{**_asn_rede_detail(d), **({"vinculo": vinculos.get(d.get("asn"))} if vinculos else {})} for d in docs],
    }


def vinculo_da_operadora(store: Store, date_str: str, cnpj: str) -> dict:
    """Campos do vínculo ASN ↔ CNPJ (D5) na resposta de uma operadora e a rede sobre os ASNs da mesma pessoa jurídica (`cnpj` e `raiz`)."""
    from api.services.operadoras import REGRA_VINCULO

    vinculados = store.asns_vinculados(date_str, cnpj)
    mesma_pj = {v["asn"]: v["vinculo"] for v in vinculados if v["vinculo"] in ("cnpj", "raiz")}
    return {
        "asn_vinculo": vinculados[0]["vinculo"] if vinculados else "nenhum",
        "asns_vinculados": vinculados,
        "regra_vinculo": REGRA_VINCULO,
        "rede": _operadora_rede(store, date_str, sorted(mesma_pj), mesma_pj),
    }


@router.get(
    "/acessos/operadora/{cnpj}",
    summary="Dados de uma operadora, por CNPJ",
    description="""
Unifica, por CNPJ: outorga(s) SCM, ASNs do Registro.br com agregação de rede
(usuários, blocos IPv4/v6, IX.br, RPKI/ASPA, alertas) e, quando a operadora
declara ao SICI, os acessos de banda larga fixa. Existe se **qualquer** desses
três existir — o bloco `sici` vem ausente quando não há declaração.

`municipios_detalhe` traz, por município, os acessos da operadora e, do total declarado no município (mês `mes_referencia` do SICI): `municipio_acessos`, `share`
(parcela da operadora em %, nula sem o índice do município), `municipio_operadores` (declarantes) e `municipio_hhi` (HHI local por CNPJ, método do projeto).

`asns` são os registrados com o mesmo CNPJ (fato). `asns_vinculados` traz todos os ASNs ligados ao CNPJ, cada um com `vinculo`
(`cnpj`, `raiz` = outro CNPJ da mesma raiz de 8 dígitos, `marca` = tabela curada, `estrangeiro` = AS de fora ligado pela marca) e
`selo` (fato só no `cnpj`); `asn_vinculo` é o mais forte (ou `nenhum`). `rede` soma os ASNs de `cnpj` e `raiz` (a mesma pessoa
jurídica) e marca o `vinculo` de cada um; os de `marca` e `estrangeiro` não entram na soma. Regra em `regra_vinculo`.
""",
)
def acessos_operadora(
    request: Request,
    cnpj: str,
    date: Optional[str] = Query(None),
    servico: str = Query("fixa", pattern="^(fixa|movel)$", description="`fixa` (banda larga fixa, padrão) ou `movel` (telefonia móvel, SMP): o mesmo contrato para os dois."),
) -> dict:
    if servico == "movel":
        from api.routes import acessos_movel as _m
        return _m.acessos_movel_operadora(request, cnpj, date)
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    clean = _DIGITS.sub("", cnpj)
    if len(clean) != 14:
        raise HTTPException(400, "CNPJ deve ter 14 dígitos")

    asns = store.cnpj_asns_index(date_str).get(clean, [])
    outorgas = store.scm_for_cnpj(date_str, clean)
    agg = store.sici_for_cnpj(date_str, clean)

    if not asns and not outorgas and not agg:
        raise HTTPException(404, "Não há informação para este CNPJ.")

    result: dict = {
        "snapshot_date": date_str,
        "cnpj": clean,
        "asns": asns,
        "outorgas_scm": outorgas,
        **vinculo_da_operadora(store, date_str, clean),
    }

    if agg:
        meta = store.sici_meta(date_str) or {}
        municipios = sorted(
            ({"ibge": ibge, **mun} for ibge, mun in agg.get("por_municipio", {}).items()),
            key=lambda m: -m["acessos"],
        )
        municipios = enriquecer_municipios_operadora(municipios, store.sici_municipios(date_str))      # parcela, declarantes e HHI locais (PT-23)
        result.update({
            "mes_referencia": meta.get("mes_referencia"),
            **{k: v for k, v in agg.items() if k != "por_municipio"},
            "municipios_detalhe": municipios,
            "serie": store.sici_serie(date_str, clean),
            "grupo_cnpjs": store.grupo_irmaos(date_str, agg.get("grupo", ""), clean),
        })

    # razao_social/nome_fantasia de fallback quando não há SICI (usa a 1a outorga)
    if "empresa" not in result and outorgas:
        result["empresa"] = outorgas[0].get("razao_social", "")

    # Apenas contagens — sem valores. Contatos de verdade só em .../contacts (protegido).
    scm_contacts = store.scm_for_cnpj_with_contacts(date_str, clean)
    pdb_contacts = [c for a in asns for c in store.peeringdb_contacts_for_asn(date_str, a)]
    geo_orgs = store._load_geo_orgs(date_str) or {}
    geo_org = next((geo_orgs.get(a) for a in asns if geo_orgs.get(a)), {}) or {}
    result["contacts_available"] = _contacts_available(scm_contacts, pdb_contacts, geo_org)

    return result


@router.get(
    "/acessos/operadora/{cnpj}/contacts",
    summary="Contatos de uma operadora, por CNPJ (protegido por login)",
    description="""
Contatos consolidados (PeeringDB POC de todos os ASNs do CNPJ, Receita/CNPJ, Anatel/SCM)
com origem e função. **Requer autenticação**. Os contatos NUNCA são servidos em lote —
apenas por operadora aqui, espelhando /asns/{asn}/contacts.
""",
)
@limiter.limit(LIMIT_CONTACTS)
def get_operadora_contacts(
    cnpj: str,
    request: Request,
    user: dict = Depends(require_user),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    servico: str = Query("fixa", pattern="^(fixa|movel)$", description="`fixa` (banda larga fixa, padrão) ou `movel` (telefonia móvel, SMP): o mesmo contrato para os dois."),
) -> dict:
    if servico == "movel":
        from api.routes import acessos_movel as _m
        return _m.get_operadora_movel_contacts(cnpj, request, user, date)
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    clean = _DIGITS.sub("", cnpj)
    if len(clean) != 14:
        raise HTTPException(400, "CNPJ deve ter 14 dígitos")

    asns = store.cnpj_asns_index(date_str).get(clean, [])
    # Cota de contatos: a operadora custa o número de ASNs do CNPJ (mínimo 1), porque revela os contatos de todos eles de uma vez.
    restante = contatos_cota.exigir(request, user, max(1, len(asns)))
    contacts = montar_contatos_operadora(store, date_str, clean, asns, "fixa")

    _log.info("contact_access cnpj=%s conta=%s asns=%d count=%d", clean, (user.get("conta_id") or user.get("provider")), len(asns), len(contacts))
    return {"cnpj": clean, "contacts": contacts, "cota": {"restante_hoje": restante}}


@router.get(
    "/acessos/municipios",
    summary="Acessos por município",
    description="Agregado por município, com número de operadores, share do maior e "
                "HHI (concentração: 10000 = monopólio).",
)
def acessos_municipios(
    request: Request,
    date: Optional[str] = Query(None),
    uf: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Busca por nome do município."),
    sort_by: str = Query("acessos", description="acessos | operadores | hhi | nome"),
    sort_desc: bool = Query(True),
    limit: int = Query(500, ge=1, le=6000),
    servico: str = Query("fixa", pattern="^(fixa|movel)$", description="`fixa` (banda larga fixa, padrão) ou `movel` (telefonia móvel, SMP): o mesmo contrato para os dois."),
) -> dict:
    if servico == "movel":
        from api.routes import acessos_movel as _m
        return _m.acessos_movel_municipios(request, date, uf, q, sort_by, sort_desc, limit)
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    meta = _meta(store, date_str)

    rows = []
    for ibge, mun in store.sici_municipios(date_str).items():
        if uf and (mun.get("uf") or "").upper() != uf.upper():
            continue
        if q and q.lower() not in (mun.get("nome") or "").lower():
            continue
        rows.append({
            "ibge": ibge, "nome": mun.get("nome", ""), "uf": mun.get("uf", ""),
            "acessos": mun.get("acessos", 0), "pf": mun.get("pf", 0),
            "pj": mun.get("pj", 0),
            "capacidade_mbps": mun.get("capacidade_mbps", 0.0),
            "operadores": mun.get("operadores_count", 0),
            "hhi": mun.get("hhi", 0), "share_maior": mun.get("share_maior", 0.0),
        })
    key = {"acessos": "acessos", "operadores": "operadores", "hhi": "hhi",
           "nome": "nome"}.get(sort_by, "acessos")
    rows.sort(key=lambda r: (r[key] or 0) if key != "nome" else r["nome"].lower(),
              reverse=sort_desc)
    return {
        "snapshot_date": date_str,
        "mes_referencia": meta["mes_referencia"],
        "total": len(rows),
        "items": rows[:limit],
    }


@router.get(
    "/acessos/municipios/mapa",
    summary="Índice IBGE → operadores para o Localizador",
    description="Como /acessos/municipios, mas com a lista de operadores (CNPJ, "
                "acessos) de cada município em vez de só a contagem — usado para "
                "geolocalizar no Localizador combinando com o centróide do IBGE.",
)
def acessos_municipios_mapa(
    request: Request,
    date: Optional[str] = Query(None),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    meta = _meta(store, date_str)

    municipios = {
        ibge: {
            "nome": mun.get("nome", ""),
            "uf": mun.get("uf", ""),
            "acessos": mun.get("acessos", 0),
            "operadores": mun.get("operadores", []),
        }
        for ibge, mun in store.sici_municipios(date_str).items()
    }
    return {
        "snapshot_date": date_str,
        "mes_referencia": meta["mes_referencia"],
        "total": len(municipios),
        "municipios": municipios,
    }


@router.get(
    "/acessos/municipio/{ibge}",
    summary="Quem oferece banda larga em um município",
)
def acessos_municipio(
    request: Request,
    ibge: str,
    date: Optional[str] = Query(None),
    servico: str = Query("fixa", pattern="^(fixa|movel)$", description="`fixa` (banda larga fixa, padrão) ou `movel` (telefonia móvel, SMP): o mesmo contrato para os dois."),
) -> dict:
    if servico == "movel":
        from api.routes import acessos_movel as _m
        return _m.acessos_movel_municipio(request, ibge, date)
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    meta = _meta(store, date_str)

    mun = store.sici_municipio(date_str, ibge.strip())
    if not mun:
        raise HTTPException(404, f"Município IBGE {ibge} sem acessos declarados.")
    return {"snapshot_date": date_str, "mes_referencia": meta["mes_referencia"], **mun}


@router.get(
    "/acessos/divergencias",
    summary="Divergências entre usuários estimados (APNIC) e acessos declarados (Anatel)",
    description="""
Duas medições independentes da mesma população: o APNIC **observa** usuários e atribui
a ASN; a operadora **declara** contratos por CNPJ. A razão deveria orbitar o número de
pessoas por domicílio (mediana medida: 3,97).

A divergência é **hipótese a investigar, nunca erro de uma das fontes**. Razão alta
sugere CGNAT, trânsito/atacado ou CNPJ mal atribuído; razão baixa sugere acessos
espalhados por vários ASes, saída por AS de trânsito ou links B2B sem usuários
observáveis.

ASNs cujo CNPJ tem mais de um ASN saem como `nao_comparavel` — incluí-los produziria
um ranking de operadoras multi-ASN, que é artefato, não achado.
""",
)
def acessos_divergencias(
    request: Request,
    date: Optional[str] = Query(None),
    classificacao: Optional[str] = Query(
        None, description="normal | apnic_alto | apnic_baixo | nao_comparavel | sem_dados"),
    limit: int = Query(100, ge=1, le=2000),
    sort_desc: bool = Query(True, description="True = maiores razões primeiro."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    meta = _meta(store, date_str)

    divs = store.sici_divergencias(date_str)
    names = {a["asn"]: a.get("name", "") for a in store.asn_index(date_str)}
    rows = []
    dist: dict[str, int] = {}
    for asn_str, d in divs.items():
        dist[d["classificacao"]] = dist.get(d["classificacao"], 0) + 1
        if classificacao and d["classificacao"] != classificacao:
            continue
        if "razao" not in d:
            continue
        asn = int(asn_str)
        rows.append({"asn": asn, "name": names.get(asn, ""),
                     "cnpj": store.sici_cnpj_for_asn(date_str, asn), **d})
    rows.sort(key=lambda r: r.get("razao", 0), reverse=sort_desc)
    return {
        "snapshot_date": date_str,
        "mes_referencia": meta["mes_referencia"],
        "distribuicao": dist,
        "total": len(rows),
        "items": rows[:limit],
    }


_ORDENS_DIV_SCM = ("apnic_users", "razao", "esperado", "acessos_pf", "acessos_pj", "asn", "name")


def _ordenar_div_scm(rows: list[dict], campo: str, asc: bool) -> list[dict]:
    """Ordena a lista inteira (o corte vem depois); vazios no fim nos dois sentidos, para a versão reduzida mostrar quem lidera."""
    texto = campo == "name"
    cheios = [r for r in rows if r.get(campo) not in (None, "")]
    vazios = [r for r in rows if r.get(campo) in (None, "")]
    cheios.sort(key=lambda r: str(r[campo]).casefold() if texto else r[campo], reverse=not asc)
    return cheios + vazios


@router.get(
    "/acessos/divergencias/scm",
    summary="Usuários estimados (APNIC) acima do esperado pelos acessos SCM declarados",
    description="""
Variante da divergência que estima quantos usuários os acessos de banda larga fixa (SCM)
declarados ao SICI explicariam:

    esperado = k_pf × acessos PF (B2C) + k_pj × acessos PJ (B2B)

e lista os ASNs cujos usuários estimados pelo APNIC chegam a `min_razao` × o esperado
(esperado 0 sempre entra). `k_pf` reflete
pessoas por domicílio; `k_pj` é uma estimativa folgada de usuários por empresa.

O universo são os CNPJs com outorga SCM e um único ASN — por isso operadoras que não
declaram acessos aparecem com `esperado = 0` (e `razao = null`). Ordenado por usuários
APNIC, decrescente, ou pela coluna de `ordem` (sempre sobre a lista inteira, antes do `limit`). ASNs com menos de 100 usuários estimados ficam de fora. Acessos móveis (SMP)
não entram no cálculo, embora o APNIC conte usuários móveis que saem pelo AS.

Como no endpoint geral, a divergência é **hipótese a investigar**, não erro de fonte.
""",
)
def acessos_divergencias_scm(
    request: Request,
    date: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=2000),
    k_pf: float = Query(5, ge=0, le=1000, description="Usuários esperados por acesso PF (B2C)."),
    k_pj: float = Query(30, ge=0, le=100000, description="Usuários esperados por acesso PJ (B2B)."),
    min_razao: float = Query(10, ge=1, le=1000000, description="Razão mínima APNIC / esperado."),
    ordem: str = Query("apnic_users", description="Coluna da ordem, aplicada à lista inteira antes do `limit`: "
                       + ", ".join(_ORDENS_DIV_SCM) + "."),
    asc: bool = Query(False, description="Ordem crescente; vazios sempre no fim."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    meta = _meta(store, date_str)

    rows = store.sici_divergencias_scm(date_str, k_pf=k_pf, k_pj=k_pj, min_razao=min_razao)
    if ordem not in _ORDENS_DIV_SCM:
        raise HTTPException(422, f"ordem deve ser uma de: {', '.join(_ORDENS_DIV_SCM)}")
    if ordem != "apnic_users" or asc:
        rows = _ordenar_div_scm(rows, ordem, asc)
    return {
        "snapshot_date": date_str,
        "mes_referencia": meta["mes_referencia"],
        "k_pf": k_pf,
        "k_pj": k_pj,
        "min_razao": min_razao,
        "total": len(rows),
        "sem_acessos": sum(1 for r in rows if not r["esperado"]),
        "items": rows[:limit],
    }
