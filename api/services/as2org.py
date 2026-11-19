# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Organização por ASN (CAIDA) e abuso agregado (Feodo Tracker): blocos do ASN e tabela do `/query`. Funções puras sobre `as2org/asns.json.gz` e `abuso_agregado/asns.json.gz`.

A organização é inferência do CAIDA (WHOIS), não grupo societário; o abuso é contagem de terceiros, sem IPs e sem veredito. Toda resposta traz fonte, data e limites.
"""
from __future__ import annotations

from typing import Optional


def bloco_organizacao(doc: Optional[dict], asn: int) -> Optional[dict]:
    """Bloco `organizacao` do perfil do ASN; None se o produto não foi publicado ou o CAIDA não conhece o ASN."""
    if not doc or str(asn) not in doc["asns"]:
        return None
    return {"snapshot_date": doc["snapshot_date"], "coletado_em": doc.get("coletado_em"), "fonte": doc["fonte"], "limites": doc["limites"], **doc["asns"][str(asn)]}


def bloco_abuso(doc: Optional[dict], asn: int) -> Optional[dict]:
    """Bloco `abuso` do perfil do ASN: contagem do Feodo (0 se o ASN não consta). None só se o produto não foi publicado."""
    if not doc:
        return None
    x = doc["asns"].get(str(asn)) or {"feodo_c2": 0, "feodo_c2_online": 0, "feodo_malware": {}}
    return {"snapshot_date": doc["snapshot_date"], "coletado_em": doc.get("coletado_em"), "fonte": doc["fonte"], "urlhaus": doc.get("urlhaus"), "limites": doc["limites"],
            "registrado": str(asn) in doc["asns"], "feodo_total_mundo": doc.get("feodo_total_mundo"), **x}


def linhas(doc_org: Optional[dict], doc_abuso: Optional[dict]) -> list[dict]:
    """Uma linha por ASN do Brasil com organização (coleção `organizacoes_asn` do `/query`), com a contagem de C2 do Feodo."""
    if not doc_org:
        return []
    abuso = (doc_abuso or {}).get("asns") or {}
    out = []
    for a, o in doc_org["asns"].items():
        ln = {"asn": int(a), "org_id": o["org_id"], "org_nome": o.get("org_nome"), "org_pais": o.get("org_pais"), "membros_total": o.get("membros_total"),
              "n_irmaos_br": len(o.get("irmaos_br") or []), "irmaos_br": o.get("irmaos_br") or []}
        if doc_abuso:
            ln["feodo_c2"] = (abuso.get(a) or {}).get("feodo_c2", 0)
        out.append({k: v for k, v in ln.items() if v is not None})
    out.sort(key=lambda r: r["asn"])
    return out
