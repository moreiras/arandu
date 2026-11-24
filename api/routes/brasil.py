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
    # `saude.moas` sai nulo também nos snapshots que gravaram 0 (a coleta não detecta MOAS, ver core/moas.py)
    out["rpki"] = {"publicacao": publicacao, "rotas": moas.retirar_do_resumo(store._read_json(store._pub(date_str) / "routing_analysis_resumo.json"))}
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
