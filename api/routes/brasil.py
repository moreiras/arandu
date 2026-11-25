# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`GET /brasil/indicadores`: agregados nacionais para "O Brasil em números" (home) e o Panorama
técnico, numa chamada só e aberta (a home é página de entrada).

- `ipv6`: adoção de IPv6 pelos usuários, somando as estimativas do APNIC por ASN do Brasil (Σ usuários IPv6 ÷ Σ usuários). É agregado dos
  ASes, não o número que o APNIC publica por país (que usa a própria amostra por país); a diferença costuma ser pequena e vem rotulada;
- `dnssec` e `rov`: o agregado nacional do produto de segurança de roteamento (medições do APNIC por ASN, com amostra mínima);
- `prontidao`: o índice de prontidão em segurança de roteamento do país (classes, média ponderada por usuários, pilares e componentes);
- `rpki` (Panorama técnico): `publicacao` (ASNs com ROA e ASPA, o mesmo corpo de `/rpki/summary`) e `rotas` (estado RPKI de origem das
  rotas brasileiras e totais de saúde da tabela, de `routing_analysis_resumo.json`; null em snapshot sem o arquivo).

Só números agregados do país: não é ranking de empresas. Fontes, datas e limites vêm na resposta."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.store import Store
from core import moas

router = APIRouter()
_CACHE: dict[tuple, dict] = {}


def ipv6_apnic(store: Store, date_str: str) -> dict:
    br = [a for a in store.asn_index(date_str) if a.get("is_br") and (a.get("apnic_users") or 0) > 0]
    usuarios = sum(a["apnic_users"] for a in br)
    v6 = sum(a.get("apnic_v6_users") or 0 for a in br)
    return {
        "usuarios": usuarios, "usuarios_ipv6": v6, "pct_usuarios_ipv6": round(100 * v6 / usuarios, 1) if usuarios else None,
        "asns_com_estimativa": len(br), "asns_com_ipv6": sum(1 for a in br if (a.get("apnic_v6_users") or 0) > 0),
        "fonte": "APNIC Labs: estimativas de usuários por ASN e de usuários com IPv6 (medição por anúncios, janela de 60 dias)",
        "nota": "Soma das estimativas por ASN do Brasil; não é o número que o APNIC publica por país, que usa a amostra do país.",
    }


def indicadores(store: Store, date_str: str) -> dict:
    chave = (id(store), date_str)
    if chave in _CACHE:
        return _CACHE[chave]
    out: dict = {"snapshot_date": date_str, "ipv6": ipv6_apnic(store, date_str)}
    seg = store.seguranca_doc(date_str)
    if seg:
        b = seg.get("brasil") or {}
        fontes = seg.get("fontes") or {}
        out["dnssec"] = {**(b.get("dnssec") or {}), "fonte": fontes.get("dnssec")}
        out["rov"] = {**(b.get("rov") or {}), "fonte": fontes.get("rov")}
        out["asns"] = b.get("asns")
    pr = store.prontidao_doc(date_str)
    if pr:
        from api.services import prontidao as p
        r = p.resumo(pr, None)
        regras = r.get("regras") or {}
        out["prontidao"] = {
            "natureza": r.get("natureza"), "agregado": r.get("agregado"),
            "pilares": {k: {"nome": v.get("nome"), "peso": v.get("peso"), "descricao": v.get("descricao"),
                            "componentes": {c: {"descricao": d.get("descricao")} for c, d in (v.get("componentes") or {}).items()}}
                        for k, v in (regras.get("pilares") or {}).items()},
            "limites": r.get("limites"),
        }
    from api.routes.rpki import montar_resumo
    publicacao = montar_resumo(store, date_str)
    publicacao.pop("snapshot_date", None)
    # `saude.moas` por família quando a coleta guardou todas as origens; nulo, com o motivo, nos que gravaram 0 sem medir (core/moas.py)
    out["rpki"] = {"publicacao": publicacao, "rotas": moas.resumo_publicado(store._read_json(store._pub(date_str) / "routing_analysis_resumo.json"))}
    if len(_CACHE) > 16:
        _CACHE.clear()
    _CACHE[chave] = out
    return out


@router.get(
    "/brasil/indicadores",
    summary="O Brasil em números: IPv6 (APNIC), DNSSEC, ROV, RPKI e prontidão em segurança de roteamento, no agregado do país",
    description="""
Agregados nacionais para a home e o Panorama técnico: `ipv6` (Σ usuários com IPv6 ÷ Σ usuários nas estimativas do APNIC por ASN do Brasil; não é o número por país do
APNIC), `dnssec` e `rov` (percentual medido pelo APNIC, mediana e média ponderada, só ASNs com amostra suficiente) e `prontidao` (índice do país por classe, média ponderada
por usuários, pilares e componentes, com as regras) e `rpki` (`publicacao`: ASNs com ROA e ASPA; `rotas`: estado RPKI de origem das rotas brasileiras, válidas,
inválidas e sem ROA, com o espaço de cada estado, e totais de saúde da tabela; `rotas` é null em snapshot anterior ao resumo). Só números do país: o detalhe por UF e porte está em `/seguranca/resumo` e `/prontidao/resumo`. Fontes e limites na resposta.
""",
)
def brasil_indicadores(request: Request, date: Optional[str] = Query(None)) -> dict:
    store: Store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return indicadores(store, d)


# ── Destaques da home: números fixos, no lugar de `/query/*` genérico (D9, TRANSV-E20) ──────────────────────────────────────────────
# As mesmas consultas dos cartões de `frontend/src/features/home/cartoes.json` (`tests/unit/test_destaques_home.py` confere que não divergem),
# executadas aqui com `limit` 1 só para o `total`. A rota é fixa e aberta; `/query` continua medido, porque aceita qualquer corpo.
_DESTAQUES_QUERY: dict[str, tuple[str, dict]] = {
    "grandes-sem-asn": ("operadoras", {"filter": {"and": [{"field": "acessos", "op": "gte", "value": 5000}, {"field": "com_asn", "op": "eq", "value": False}]}}),
    "sem-rpki": ("asns", {"filter": {"and": [{"field": "is_br", "op": "eq", "value": True}, {"field": "global_prefixes_v6_count", "op": "gte", "value": 1},
                                             {"field": "has_rpki", "op": "eq", "value": False}, {"field": "ixps_direct_count", "op": "gte", "value": 3}]}}),
    "monopolio-local": ("acessos_municipio", {"filter": {"and": [{"field": "share", "op": "gte", "value": 80}, {"field": "municipio_acessos", "op": "gte", "value": 1000}]}}),
}
_DIVERGENCIAS = {"k_pf": 5, "k_pj": 30, "min_razao": 10}          # os parâmetros padrão de `/acessos/divergencias/scm`, que é a lista de destino
_O_QUE_MUDOU = {"filter": {"and": [{"field": "tipo", "op": "eq", "value": "asn_novo"}, {"field": "estado", "op": "eq", "value": "confirmado"}]},
                "select": ["asn", "uf", "data"], "sort": [{"field": "data", "dir": "desc"}], "limit": 1}
_CACHE_DESTAQUES: dict[tuple, dict] = {}


def destaques_home(store: Store, date_str: str) -> dict:
    chave = (id(store), date_str)
    if chave in _CACHE_DESTAQUES:
        return _CACHE_DESTAQUES[chave]
    from api.auth.access_policy import N_DATAS_ATUAIS
    out: dict = {"snapshot_date": date_str, "destaques": {}}
    for id_, (colecao, corpo) in _DESTAQUES_QUERY.items():
        out["destaques"][id_] = {"total": store.query(date_str, colecao, {**corpo, "limit": 1}).get("total", 0)}
    out["destaques"]["divergencias"] = {"total": len(store.sici_divergencias_scm(date_str, **_DIVERGENCIAS))}
    # "O que mudou" só na janela dos snapshots atuais: a rota é aberta e a mesma URL serve a todos, então não alcança o histórico (EXP-E4)
    janela_de = store.list_snapshots()[-N_DATAS_ATUAIS:][0]
    r = store.query(date_str, "eventos", {**_O_QUE_MUDOU, "de": janela_de})
    ultimo = (r.get("items") or [None])[0]
    out["o_que_mudou"] = {"total": r.get("total", 0), "de": janela_de, "mais_recente": (ultimo or {}).get("data")}
    if len(_CACHE_DESTAQUES) > 16:
        _CACHE_DESTAQUES.clear()
    _CACHE_DESTAQUES[chave] = out
    return out


@router.get(
    "/brasil/destaques",
    summary="Destaques da home: o total de cada pergunta pronta e os ASes novos da janela atual",
    description="""
Os números fixos dos destaques da página inicial, numa chamada aberta: `destaques` traz o `total` de cada pergunta pronta (operadoras com mais de 5 mil acessos sem ASN
próprio, ASes brasileiros em 3 ou mais PTTs com IPv6 e sem ROA, municípios com uma operadora de 80% ou mais da banda larga fixa e ASNs com usuários APNIC 10 vezes ou mais acima do esperado
pelos acessos SCM) e `o_que_mudou` os ASes brasileiros novos e confirmados desde `de`, a data do snapshot atual mais antigo (a rota é aberta, então não alcança o histórico). Cada total é
o da lista de destino do destaque. As consultas são fixas; a consulta genérica (`/query`) segue medida.
""",
)
def brasil_destaques(request: Request, date: Optional[str] = Query(None)) -> dict:
    store: Store = request.app.state.store
    d = store.resolve_date(date)
    if d is None:
        raise HTTPException(404, "Nenhum snapshot disponível")
    return destaques_home(store, d)
