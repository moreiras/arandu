# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Endpoints de acessos de telefonia móvel (SMP) declarados ao SICI (Anatel).

Espelha api/routes/acessos.py, mas para o universo móvel — bem menor (~30 CNPJs
outorgados, ~17 declarando acesso no mês de referência). As mesmas duas regras de
leitura valem aqui:

  * `acessos_compartilhados` — CNPJ com mais de um ASN tem o total atribuído
    integralmente a CADA ASN; nunca somar ASes do mesmo CNPJ.
  * `acessos` já exclui M2M e PONTO_DE_SERVICO (ver sources/anatel_sici_movel/collect.py) —
    é o número de linhas móveis pessoais/corporativas, batendo com o total oficial
    da Anatel. Os dois ficam disponíveis à parte em `acessos_m2m`/`acessos_outros`.

NÃO inclui divergência APNIC×Anatel (não faz sentido do mesmo jeito para o universo
móvel) nem o endpoint de mapa por município.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.auth.deps import require_user
from api.ratelimit import limiter, LIMIT_CONTACTS
from api import contatos_cota
from api.routes.acessos import _operadora_rede
from api.routes.asns import _contacts_available, montar_contatos_operadora
from api.store import Store

router = APIRouter()
_log = logging.getLogger("arandurape")

_DIGITS = re.compile(r"\D")

_OPERADORA_SORT = {"acessos", "acessos_pf", "acessos_pj", "acessos_m2m",
                   "municipios", "empresa", "cnpj"}


def _meta(store: Store, date_str: str) -> dict:
    meta = store.sici_movel_meta(date_str)
    if not meta:
        raise HTTPException(
            404, "Dados de acessos móveis (SICI) não disponíveis para este snapshot. "
                 "Rode a coleta anatel_sici_movel e a etapa sici_movel primeiro.")
    return meta


@router.get(
    "/acessos-movel/stats",
    summary="Estatísticas nacionais de acessos de telefonia móvel (SICI/Anatel)",
    description="Totais do mês de referência, série histórica mensal, mix de "
                "geração/modalidade, e as maiores operadoras móveis.",
)
def acessos_movel_stats(
    request: Request,
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
    top: int = Query(20, ge=1, le=200),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    meta = _meta(store, date_str)

    all_rows = store.operadora_movel_index(date_str)
    rows = [r for r in all_rows if r.get("ativo")]

    licenciados = [r for r in all_rows if r.get("licenciado")]
    licenciados_informaram = [r for r in licenciados if r.get("ativo")]
    cobertura_declaracao = {
        "licenciados": len(licenciados),
        "informaram_sici": len(licenciados_informaram),
        "pct_informaram_sici": round(100 * len(licenciados_informaram) / len(licenciados), 1)
            if licenciados else None,
    }

    por_geracao: dict[str, int] = {}
    por_modalidade: dict[str, int] = {}
    total_pf = total_pj = total_m2m = 0
    for r in rows:
        total_pf += r.get("acessos_pf", 0)
        total_pj += r.get("acessos_pj", 0)
        total_m2m += r.get("acessos_m2m", 0)
    data = store._load_sici_movel(date_str) or {}
    for agg in data.get("cnpjs", {}).values():
        for k, v in agg.get("por_geracao", {}).items():
            por_geracao[k] = por_geracao.get(k, 0) + v
        for k, v in agg.get("por_modalidade", {}).items():
            por_modalidade[k] = por_modalidade.get(k, 0) + v

    ranking = sorted(rows, key=lambda r: -r.get("acessos", 0))[:top]

    return {
        "snapshot_date": date_str,
        **meta,
        "acessos_pf": total_pf,
        "acessos_pj": total_pj,
        "acessos_m2m": total_m2m,
        "operadoras_ativas": len(rows),
        "municipios_atendidos": len(store.sici_movel_municipios(date_str)),
        "cobertura_declaracao": cobertura_declaracao,
        "por_geracao": dict(sorted(por_geracao.items(), key=lambda kv: -kv[1])),
        "por_modalidade": dict(sorted(por_modalidade.items(), key=lambda kv: -kv[1])),
        "distrib_modalidade": store.sici_movel_distrib_modalidade(date_str),
        "serie_total": store.sici_movel_serie_total(date_str),
        "top_operadoras": [
            {k: r.get(k) for k in ("cnpj", "empresa", "razao_social", "acessos",
                                   "acessos_pf", "acessos_pj", "acessos_m2m",
                                   "municipios", "geracao_predominante", "asns",
                                   "grupo_economico")}
            for r in ranking
        ],
    }


@router.get(
    "/acessos-movel/operadoras",
    summary="Listar operadoras móveis por acessos declarados",
)
def acessos_movel_operadoras(
    request: Request,
    date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    uf: Optional[str] = Query(None, description="UF da sede (cadastro SMP)."),
    q: Optional[str] = Query(None, description="Busca por empresa, razão social ou CNPJ."),
    com_asn: Optional[bool] = Query(None),
    ativo: Optional[bool] = Query(None, description="True = só operadoras que declaram "
                                  "acesso; False = só licenciadas sem declaração; "
                                  "omitido = todas. (Universo pequeno: default aberto "
                                  "aqui, ao contrário de /acessos/operadoras.)"),
    min_acessos: Optional[int] = Query(None, ge=0),
    sort_by: str = Query("acessos", description=f"Um de: {', '.join(sorted(_OPERADORA_SORT))}"),
    sort_desc: bool = Query(True),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    meta = _meta(store, date_str)

    rows = store.operadora_movel_index(date_str)
    if ativo is not None:
        rows = [r for r in rows if bool(r.get("ativo")) is ativo]
    if uf:
        u = uf.upper()
        rows = [r for r in rows if (r.get("uf_sede") or "").upper() == u]
    if com_asn is not None:
        rows = [r for r in rows if bool(r.get("asns")) is com_asn]
    if min_acessos is not None:
        rows = [r for r in rows if r.get("acessos", 0) >= min_acessos]
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


@router.get(
    "/acessos-movel/operadora/{cnpj}",
    summary="Dados de uma operadora móvel, por CNPJ",
    description="""
Unifica, por CNPJ: outorga(s) SMP, ASNs do Registro.br com agregação de rede e,
quando a operadora declara ao SICI, os acessos móveis. Existe se **qualquer** desses
três existir — o bloco de acessos vem ausente quando não há declaração.
""",
)
def acessos_movel_operadora(
    request: Request,
    cnpj: str,
    date: Optional[str] = Query(None),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    clean = _DIGITS.sub("", cnpj)
    if len(clean) != 14:
        raise HTTPException(400, "CNPJ deve ter 14 dígitos")

    asns = store.cnpj_asns_index(date_str).get(clean, [])
    outorgas = store.smp_for_cnpj(date_str, clean)
    agg = store.sici_movel_for_cnpj(date_str, clean)

    if not asns and not outorgas and not agg:
        raise HTTPException(404, "Não há informação para este CNPJ.")

    result: dict = {
        "snapshot_date": date_str,
        "cnpj": clean,
        "asns": asns,
        "outorgas_smp": outorgas,
        "rede": _operadora_rede(store, date_str, asns),
    }

    if agg:
        meta = store.sici_movel_meta(date_str) or {}
        municipios = sorted(
            ({"ibge": ibge, **mun} for ibge, mun in agg.get("por_municipio", {}).items()),
            key=lambda m: -m["acessos"],
        )
        result.update({
            "mes_referencia": meta.get("mes_referencia"),
            **{k: v for k, v in agg.items() if k != "por_municipio"},
            "municipios_detalhe": municipios,
            "serie": store.sici_movel_serie(date_str, clean),
            "grupo_cnpjs": store.grupo_irmaos(date_str, agg.get("grupo", ""), clean),
        })

    if "empresa" not in result and outorgas:
        result["empresa"] = outorgas[0].get("razao_social", "")

    smp_contacts = store.smp_for_cnpj_with_contacts(date_str, clean)
    pdb_contacts = [c for a in asns for c in store.peeringdb_contacts_for_asn(date_str, a)]
    geo_orgs = store._load_geo_orgs(date_str) or {}
    geo_org = next((geo_orgs.get(a) for a in asns if geo_orgs.get(a)), {}) or {}
    result["contacts_available"] = _contacts_available(smp_contacts, pdb_contacts, geo_org)

    return result


@router.get(
    "/acessos-movel/operadora/{cnpj}/contacts",
    summary="Contatos de uma operadora móvel, por CNPJ (protegido por login)",
    description="Contatos consolidados (PeeringDB POC, Receita/CNPJ, Anatel/SMP). "
                "**Requer autenticação**.",
)
@limiter.limit(LIMIT_CONTACTS)
def get_operadora_movel_contacts(
    cnpj: str,
    request: Request,
    user: dict = Depends(require_user),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
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
    contacts = montar_contatos_operadora(store, date_str, clean, asns, "movel")

    _log.info("contact_access_movel cnpj=%s conta=%s asns=%d count=%d", clean, (user.get("conta_id") or user.get("provider")), len(asns), len(contacts))
    return {"cnpj": clean, "contacts": contacts, "cota": {"restante_hoje": restante}}


@router.get(
    "/acessos-movel/municipios",
    summary="Acessos móveis por município",
)
def acessos_movel_municipios(
    request: Request,
    date: Optional[str] = Query(None),
    uf: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Busca por nome do município."),
    sort_by: str = Query("acessos", description="acessos | operadores | hhi | nome"),
    sort_desc: bool = Query(True),
    limit: int = Query(500, ge=1, le=6000),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    meta = _meta(store, date_str)

    rows = []
    for ibge, mun in store.sici_movel_municipios(date_str).items():
        if uf and (mun.get("uf") or "").upper() != uf.upper():
            continue
        if q and q.lower() not in (mun.get("nome") or "").lower():
            continue
        rows.append({
            "ibge": ibge, "nome": mun.get("nome", ""), "uf": mun.get("uf", ""),
            "acessos": mun.get("acessos", 0), "pf": mun.get("pf", 0),
            "pj": mun.get("pj", 0),
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
    "/acessos-movel/municipio/{ibge}",
    summary="Quem oferece telefonia móvel em um município",
)
def acessos_movel_municipio(
    request: Request,
    ibge: str,
    date: Optional[str] = Query(None),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    meta = _meta(store, date_str)

    mun = store.sici_movel_municipio(date_str, ibge.strip())
    if not mun:
        raise HTTPException(404, f"Município IBGE {ibge} sem acessos móveis declarados.")
    return {"snapshot_date": date_str, "mes_referencia": meta["mes_referencia"], **mun}
