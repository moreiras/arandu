# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cloudflare Radar: bloco do ASN e da UF. Funções puras sobre `radar/asns.json.gz`.

Toda resposta traz a licença (CC BY-NC 4.0), a atribuição, o aviso, os limites e a cobertura. Ausência de dado não é zero; o agregado por UF é derivado dos ASNs.
"""
from __future__ import annotations

from typing import Optional


def _cabecalho(doc: dict) -> dict:
    return {"snapshot_date": doc["snapshot_date"], "coletado_em": doc.get("coletado_em"), "fonte": doc["fonte"], "licenca": doc["licenca"], "aviso": doc["aviso"],
            "limites": doc["limites"], "janela_ipv6": doc.get("janela_ipv6"), "cobertura": doc["cobertura"]}


def bloco_asn(doc: Optional[dict], asn: int) -> Optional[dict]:
    """Bloco `radar` do ASN; None se o produto não foi publicado ou o Radar não tem nenhum dado do ASN (ausência não é zero)."""
    if not doc or str(asn) not in doc["asns"]:
        return None
    return {**_cabecalho(doc), "asn": asn, **doc["asns"][str(asn)], "bgp_janela": doc["bgp"], "quedas": doc["quedas"]}


def bloco_uf(doc: Optional[dict], uf: str) -> Optional[dict]:
    """Agregado DERIVADO dos ASNs da UF; None se o produto não foi publicado ou a UF não tem ASN."""
    sigla = uf.upper()
    if not doc or sigla not in doc["por_uf"]:
        return None
    return {**_cabecalho(doc), "uf": sigla, **doc["por_uf"][sigla], "bgp_janela": doc["bgp"], "quedas": doc["quedas"]}
