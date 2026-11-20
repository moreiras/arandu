# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Comparação de IXPs — GET /ixp-compare/members.

Dado um conjunto de 2 a 4 IXPs (IX.br e/ou externos, misturáveis), devolve a
lista deduplicada de participantes (por ASN) já enriquecida com nome, CNPJ e
blocos IPv6/IPv4 (via `asn_detail`, que já resolve esse cruzamento no publish),
mais a lista de quais dos IXPs pedidos cada ASN integra — a mesma informação
que alimenta tanto o diagrama de Venn quanto o UpSet no frontend.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.store import Store
from core.common import codigo_valido

router = APIRouter()


def _parse_ixp_key(key: str) -> tuple[str, str]:
    if ":" not in key:
        raise HTTPException(400, f"Código de IXP inválido: '{key}' (use 'ixbr:<code>' ou 'ext:<code>')")
    kind, code = key.split(":", 1)
    if kind not in ("ixbr", "ext") or not codigo_valido(code):
        raise HTTPException(400, f"Código de IXP inválido: '{key}' (use 'ixbr:<code>' ou 'ext:<code>')")
    return kind, code


@router.get(
    "/ixp-compare/members",
    summary="Participantes enriquecidos de 2 a 4 IXPs (IX.br e/ou externos)",
    description="""
Recebe de 2 a 4 IXPs via `ixps=ixbr:sp,ixbr:rj,ext:megaix-miami` e devolve, por
ASN participante (união de todos os IXPs pedidos, sem duplicar), nome, CNPJ e
blocos IPv6/IPv4 do Registro.br, além de `member_of` — em quais dos IXPs
pedidos aquele ASN está presente — e `has_detail` — se o ASN tem documento no
snapshot (`GET /asns/{asn}`); o cadastro do IX.br inclui ASNs privados e ASNs
sem registro no Registro.br/LACNIC, que não têm página. É a base para os diagramas de Venn/UpSet e a
exportação em CSV da página de comparação.

**Requer autenticação** quando algum dos IXPs é externo — lista de membros
PeeringDB é dado redistribuído, mesma regra de `GET /external-ixps/{code}`.
""",
)
def ixp_compare_members(
    request: Request,
    ixps: str = Query(..., description="2 a 4 IXPs separados por vírgula, formato 'ixbr:<code>' ou 'ext:<code>'."),
    date: Optional[str] = Query(None, description="Data do snapshot (YYYY-MM-DD)."),
) -> dict:
    store: Store = request.app.state.store
    date_str = store.resolve_date(date)
    if date_str is None:
        raise HTTPException(404, "Nenhum snapshot disponível")

    keys = [k.strip() for k in ixps.split(",") if k.strip()]
    if len(keys) < 2 or len(keys) > 4:
        raise HTTPException(400, "Informe de 2 a 4 IXPs em 'ixps'")
    if len(set(keys)) != len(keys):
        raise HTTPException(400, "IXPs duplicados em 'ixps'")
    parsed = [_parse_ixp_key(k) for k in keys]

    membership: dict[str, set[int]] = {}
    for key, (kind, code) in zip(keys, parsed):
        if kind == "ixbr":
            doc = store.ixp_detail(date_str, code)
            if doc is None:
                raise HTTPException(404, f"IXP '{code}' não encontrado no snapshot '{date_str}'")
            membership[key] = set(store._load_ixp_members(date_str, code))
        else:
            doc = store.external_ixp_detail(date_str, code)
            if doc is None:
                raise HTTPException(404, f"IXP externo '{code}' não encontrado no snapshot '{date_str}'")
            membership[key] = {m["asn"] for m in doc.get("members", []) if m.get("asn")}

    all_asns: set[int] = set()
    for asns in membership.values():
        all_asns |= asns

    participants = []
    for asn in sorted(all_asns):
        member_of = [key for key in keys if asn in membership[key]]
        detail = store.asn_detail(date_str, asn)
        participants.append({
            "asn": asn,
            "name": detail.get("name") if detail else None,
            "cnpj": detail.get("cnpj") if detail else None,
            "ipv4_prefixes": detail.get("rir_prefixes_v4", []) if detail else [],
            "ipv6_prefixes": detail.get("rir_prefixes_v6", []) if detail else [],
            "member_of": member_of,
            "has_detail": detail is not None,
        })

    return {
        "snapshot_date": date_str,
        "ixps": keys,
        "count": len(participants),
        "participants": participants,
    }
