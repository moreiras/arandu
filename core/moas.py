# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""MOAS (prefixo com mais de um AS de origem): textos e o que a API e o MCP servem em cada snapshot.

A coleta da tabela global grava `origins-multi-{afi}` (`sources/fulltable_routeviews/collect.py`): todas as origens observadas, por
coletor, dos prefixos com mais de uma. Com ele, `routing_analysis` publica `moas` (lista dos prefixos brasileiros) e `moas_resumo`
(contagens por família e coletores); sem ele (snapshots anteriores, cuja coleta guardava uma origem por prefixo), `moas` é `null` com
o motivo em `moas_indisponivel`, e a API e o MCP fazem o mesmo nos snapshots publicados antes (que traziam `[]` ou 0).

MOAS é fato observado; a causa de cada caso não é medida e não vira rótulo. Exemplos de causa só no "Como ler", como hipótese.
"""
from __future__ import annotations

MOTIVO = ("Origem múltipla (MOAS) não medida neste snapshot: a coleta da tabela global deste snapshot guardou uma origem por prefixo, "
          "o que não permite detectar prefixos anunciados por mais de um AS. MOAS existe e é raro; a falta de número aqui é limite da "
          "coleta, não ausência de eventos.")

DEFINICAO = ("Prefixo com mais de um AS de origem (último AS do AS_PATH) entre as rotas observadas nos coletores da tabela global "
             "(RouteViews e RIPE RIS). A contagem global inclui todos os prefixos; a lista traz só os prefixos brasileiros (contidos em "
             "bloco alocado pelo Registro.br), com as origens e em quantos coletores cada uma foi vista.")

COMO_LER = ("É fato observado: o mesmo prefixo com origens diferentes, nos coletores e horários dos dumps usados. A causa não é medida. "
            "Hipóteses, a conferir caso a caso: anycast, multihoming com ASN privado removido pelo provedor, troca de origem entre os "
            "horários dos dumps, anúncio indevido de prefixo de terceiros. Uma origem vista por poucos coletores pode ser visão de "
            "poucos pontos de observação.")

LIMITES = ("Visão de poucos coletores: MOAS visível só fora deles não aparece. Cada coletor tem um dump de horário próprio, então uma troca "
           "de origem entre esses horários conta como MOAS. Num AS_SET final, a origem é o último ASN do conjunto.")


def medido(doc: dict | None) -> bool:
    """`routing_analysis.json` gerado com `origins-multi` (lista e resumo presentes)."""
    return bool(doc) and isinstance(doc.get("moas"), list) and isinstance(doc.get("moas_resumo"), dict)


def analise_publicada(doc: dict) -> dict:
    """Cópia rasa de `routing_analysis.json` como a API serve: medido passa como está; senão `moas` nulo e o motivo."""
    if medido(doc):
        return dict(doc)
    return {**doc, "moas": None, "moas_resumo": None, "moas_indisponivel": MOTIVO}


def _saude_medida(m) -> bool:
    return isinstance(m, dict) and ("v6" in m or "v4" in m)


def resumo_publicado(doc: dict | None) -> dict | None:
    """Cópia de `routing_analysis_resumo.json`: `saude.moas` por família quando medido; senão nulo e o motivo (`None` passa)."""
    if not doc:
        return doc
    saude = doc.get("saude") or {}
    if _saude_medida(saude.get("moas")):
        return doc
    return {**doc, "saude": {**saude, "moas": None, "moas_indisponivel": MOTIVO}}
