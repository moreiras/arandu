# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Alerta `ptt_proximo_sem_participar`, versão 2 (ASN-E6): quando avaliar e o que dizer.

Política editorial: o alerta diz só o fato geográfico (a sede do AS fica a menos de N km de tantos PTTs onde o AS não consta como participante), sem
recomendação de negócio nem benefício presumido ("pode reduzir custo e latência" saiu). E só se avalia AS que tem prefixo na tabela global e cujo
CNPJ não está baixado: para AS sem prefixo ou com cadastro baixado o alerta não descreve nada útil. A regra (`products/alerts`) e a cópia de paridade
(`api/asn_health.py`) usam este módulo, para não divergirem.
"""
from __future__ import annotations

from typing import Optional


def cnpj_baixado(store, date_str: str, asn: int) -> bool:
    """O CNPJ do AS consta como BAIXADA no cadastro da Receita (campo `descricao_situacao_cadastral`). Sem cadastro carregado, falso."""
    carregar = getattr(store, "_load_geo_orgs", None)
    if carregar is None:
        return False
    org = (carregar(date_str) or {}).get(asn) or {}
    return (org.get("descricao_situacao_cadastral") or "").strip().upper() == "BAIXADA"


def deve_avaliar(store, date_str: str, asn: int, doc: dict) -> bool:
    """Só AS com prefixo na tabela global (v4 ou v6) e CNPJ não baixado."""
    tem_prefixo = bool(doc.get("global_prefixes_v4") or doc.get("global_prefixes_v6"))
    return tem_prefixo and not cnpj_baixado(store, date_str, asn)


def detalhe(near: list[dict], km: int) -> str:
    """Texto do alerta: o fato, com cada PTT e a distância, sem benefício nem recomendação."""
    def um(x: dict) -> str:
        km_txt = str(x['dist_km']).replace('.', ',')
        nome = x.get('name')
        return f"{nome} ({x['code'].upper()}, {km_txt} km)" if nome and nome.upper() != x['code'].upper() else f"{x['code'].upper()} ({km_txt} km)"
    lista = ", ".join(um(x) for x in near[:10])
    n = len(near)
    return f"A sede do AS fica a menos de {km} km de {n} {'PTT do IX.br' if n == 1 else 'PTTs do IX.br'} onde o AS não consta como participante: {lista}."
