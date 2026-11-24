# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""MOAS (prefixo com mais de um AS de origem): análise indisponível até haver coleta capaz.

A tabela global usada (`origin-prefixes-{afi}`) guarda uma origem por prefixo (`sources/fulltable_routeviews/collect.py`, os prefixos
do primeiro coletor prevalecem), então nenhuma contagem de MOAS sai dela: o resultado seria sempre 0, o que não é ausência de MOAS. O
pipeline grava `null` com o motivo, e a API e o MCP fazem o mesmo nos snapshots publicados antes (que traziam `[]` ou 0).
"""
from __future__ import annotations

MOTIVO = ("Análise de origem múltipla (MOAS) indisponível: a tabela global usada guarda uma origem por prefixo, então não detecta "
          "prefixos anunciados por mais de um AS. A ausência de dado aqui não indica ausência de MOAS.")


def retirar_da_analise(doc: dict) -> dict:
    """Cópia rasa de `routing_analysis.json` com `moas` nulo e o motivo."""
    return {**doc, "moas": None, "moas_indisponivel": MOTIVO}


def retirar_do_resumo(doc: dict | None) -> dict | None:
    """Cópia de `routing_analysis_resumo.json` com `saude.moas` nulo e o motivo (`None` passa como está)."""
    if not doc:
        return doc
    return {**doc, "saude": {**(doc.get("saude") or {}), "moas": None, "moas_indisponivel": MOTIVO}}
