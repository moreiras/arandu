# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Exposição de serviços: bloco do ASN e da UF. Funções puras sobre `exposicao/asns.json.gz`.

Toda resposta traz a atribuição ao Shodan, o aviso ("não é prova de vulnerabilidade"), os limites e a cobertura. Só contagens, nunca host individual. Ausência de leitura não é zero.
"""
from __future__ import annotations

from typing import Optional


def _cabecalho(doc: dict) -> dict:
    return {"snapshot_date": doc["snapshot_date"], "coletado_em": doc.get("coletado_em"), "fonte": doc["fonte"], "licenca": doc["licenca"], "aviso": doc["aviso"],
            "limites": doc["limites"], "plano": doc.get("plano"), "cobertura": doc["cobertura"]}


def bloco_asn(doc: Optional[dict], asn: int) -> Optional[dict]:
    """Bloco `exposicao` do ASN; None se o produto não foi publicado ou o ASN ainda não foi lido pelo rodízio (ausência não é zero)."""
    if not doc or str(asn) not in doc["asns"]:
        return None
    return {**_cabecalho(doc), "asn": asn, "classes_de_risco": doc.get("classes"), **doc["asns"][str(asn)]}


def bloco_uf(doc: Optional[dict], uf: str) -> Optional[dict]:
    """Agregado DERIVADO dos ASNs lidos da UF; None se o produto não foi publicado ou a UF não tem ASN."""
    sigla = uf.upper()
    if not doc or sigla not in doc["por_uf"]:
        return None
    return {**_cabecalho(doc), "uf": sigla, "classes_de_risco": doc.get("classes"), **doc["por_uf"][sigla]}
