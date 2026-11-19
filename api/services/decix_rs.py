# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""DE-CIX Rio e São Paulo: o bloco `route_server` que estende `GET /external-ixps/{code}`, o resumo nas linhas do índice e as colunas do `/query`.

Funções puras sobre `decix_rs/ixps.json.gz`. O bloco vem do Alice-LG do DE-CIX (sessão no route server e rotas lidas por vizinho em rodízio), nunca do PeeringDB: a origem
é um piso (`rotas.parcial`) e `asn_direct` é sessão up, não o primeiro salto do IX.br. Só existe para `decix-sp` e `decix-rj` e só quando a coleta rodou; sem ela o documento do
IXP externo sai exatamente como antes.
"""
from __future__ import annotations

from typing import Optional


def bloco(rs_doc: Optional[dict], code: str) -> Optional[dict]:
    """O bloco do PTT com o cabeçalho (data, fonte, aviso, bloqueio) ou None se não houver."""
    b = ((rs_doc or {}).get("ixps") or {}).get(code)
    if not b:
        return None
    cab = {k: rs_doc.get(k) for k in ("snapshot_date", "coletado_em", "rotas_coletadas_em", "fonte", "versao_alice", "aviso", "bloqueio") if rs_doc.get(k) is not None}
    return {**cab, **b}


def anexar(doc: dict, rs_doc: Optional[dict], code: str) -> dict:
    """Cópia de `doc` (IXP externo) com `route_server` se houver bloco do DE-CIX para `code`; `doc` não é alterado."""
    b = bloco(rs_doc, code)
    return {**doc, "route_server": b} if b else doc


def resumo(rs_doc: Optional[dict], code: str) -> Optional[dict]:
    """Os números do PTT para a lista e o `/query`: sessões up, ASNs diretos e originadores (piso) e se a origem é parcial."""
    b = ((rs_doc or {}).get("ixps") or {}).get(code)
    if not b:
        return None
    r = b.get("resumo") or {}
    return {"sessoes_up": r.get("sessoes_up"), "asn_direct_count": r.get("asn_direct_count"), "asn_origin_count": r.get("asn_origin_count"),
            "origem_parcial": (b.get("rotas") or {}).get("parcial")}


def com_resumo(entradas: list[dict], rs_doc: Optional[dict]) -> list[dict]:
    """Entradas do índice dos IXPs externos, as do DE-CIX com `route_server` (resumo)."""
    out = []
    for e in entradas:
        r = resumo(rs_doc, e.get("code", ""))
        out.append({**e, "route_server": r} if r else e)
    return out


def linhas_query(entradas: list[dict], rs_doc: Optional[dict]) -> list[dict]:
    """Linhas da collection `external_ixps` do `/query`, com as colunas planas `rs_*` para o DE-CIX (nulas nos demais)."""
    out = []
    for e in entradas:
        r = resumo(rs_doc, e.get("code", "")) or {}
        out.append({**e, "rs_sessoes_up": r.get("sessoes_up"), "rs_asn_direct_count": r.get("asn_direct_count"), "rs_asn_origin_count": r.get("asn_origin_count")})
    return out
