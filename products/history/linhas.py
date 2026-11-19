# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Linha de histórico de um ASN a partir do documento publicado. Função pura."""
from __future__ import annotations

import hashlib
from typing import Iterable, Optional

from products.history.esquema import LinhaAsn

# Provedor "confirmado ou superior" do ARC v1: declarado (ASPA) e confirmado. Mesma definição de `n_provedores` em
# products/as_relationships/por_asn.py (duplicada de propósito: produto não importa produto, e o histórico só lê o resultado).
NIVEIS_PROVEDOR_FIRME = frozenset({"declarado", "confirmado"})


def hash_conjunto(itens: Iterable) -> Optional[str]:
    """Hash curto e estável de um conjunto; conjunto vazio = None."""
    ordenados = sorted(str(i) for i in itens)
    if not ordenados:
        return None
    return hashlib.sha1("\n".join(ordenados).encode("utf-8")).hexdigest()[:12]


def provedores_firmes(doc: dict) -> Optional[list[int]]:
    """ASNs provedores de nível confirmado+; None se o documento não tem o bloco de relações."""
    rel = doc.get("relacoes")
    if not isinstance(rel, dict) or "provedores" not in rel:
        return None
    return sorted(int(p["asn"]) for p in rel["provedores"] if p.get("nivel") in NIVEIS_PROVEDOR_FIRME)


def prefixos_globais(doc: dict) -> list[str]:
    return list(doc.get("global_prefixes_v4") or []) + list(doc.get("global_prefixes_v6") or [])


def linha_asn(doc: dict) -> dict:
    """Linha enxuta (sem campos None) do ASN; ordem dos campos fixa pelo esquema."""
    prov = provedores_firmes(doc)
    rpki = doc.get("rpki_validation") if isinstance(doc.get("rpki_validation"), dict) else {}
    estados = list(rpki.values())
    alertas = doc.get("alerts")
    ixd = doc.get("ixps_direct") or []
    ixm = doc.get("ixp_member_codes") or []
    linha = LinhaAsn(
        asn=int(doc["asn"]),
        is_br=bool(doc.get("is_br")),
        cnpj=(doc.get("cnpj") or None) if doc.get("is_br") else None,
        uf=((doc.get("geo_org") or {}).get("uf") or None) if doc.get("is_br") else None,
        users=doc.get("apnic_users"),
        v6users=doc.get("apnic_v6_users"),
        p4=int(doc.get("global_prefixes_v4_count") or 0),
        p6=int(doc.get("global_prefixes_v6_count") or 0),
        n_ixd=len(ixd),
        n_ixm=len(ixm),
        n_provedores=None if prov is None else len(prov),
        n_roa=len(doc.get("roa_list") or []),
        n_aspa=len(doc.get("aspa_providers") or []),
        rpki_valid=estados.count("valid"),
        rpki_invalid=estados.count("invalid"),
        rpki_not_found=estados.count("not_found"),
        n_alertas=None if alertas is None else len(alertas),
        hash_alertas=None if alertas is None else hash_conjunto(a["id"] for a in alertas),
        hash_relacoes=None if prov is None else hash_conjunto(prov),
        hash_ixd=hash_conjunto(ixd),
        hash_ixm=hash_conjunto(ixm),
        hash_pfx=hash_conjunto(prefixos_globais(doc)),
    )
    return linha.model_dump(exclude_none=True)
