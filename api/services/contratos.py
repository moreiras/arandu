# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Contratos públicos: consultas sobre `contratos/*.json.gz`. Funções puras.

Toda resposta traz fonte, licença (dados abertos, sem licença nominal), aviso, limites e a cobertura do rodízio. 404 quer dizer "sem leitura (ainda)" ou "município sem contratação detalhada nas leituras";
raiz lida sem resultado é 200 com `resultado = sem_resultado_na_consulta` e a data da leitura. Ausência não é zero.
"""
from __future__ import annotations

import re
from typing import Optional

from api.services.empresas import EmpresasErro, raiz_do_cnpj  # noqa: F401  (reexportada para a rota e o MCP)

_META = ("snapshot_date", "coletado_em", "natureza", "fonte", "licenca", "aviso", "limites", "cobertura")


def operadora(doc: dict, raiz: str) -> dict:
    d = (doc.get("operadoras") or {}).get(raiz)
    if not d:
        raise EmpresasErro(404, f"Operadora {raiz} ainda sem leitura de contratos públicos neste snapshot (o rodízio ainda não chegou à raiz, ou ela está fora do universo de telecom); isso não quer dizer que não haja contratos.")
    return {**{k: doc.get(k) for k in _META}, **d}


def municipio(doc: dict, ibge: str) -> dict:
    cod = re.sub(r"\D", "", ibge or "")
    if len(cod) != 7:
        raise EmpresasErro(400, "Código IBGE inválido: informe os 7 dígitos.")
    d = (doc.get("municipios") or {}).get(cod)
    if not d:
        raise EmpresasErro(404, f"Município {cod} sem contratação de operadora nas leituras do snapshot (a leitura é parcial; ausência não prova que não haja).")
    return {**{k: doc.get(k) for k in _META}, "criterio_municipio": doc.get("criterio_municipio"), "ibge": cod, **d}


def resumo(doc: dict, uf: Optional[str] = None) -> dict:
    out = {k: doc.get(k) for k in _META}
    if not uf:
        return {**out, "por_ano": doc["por_ano"], "por_uf": doc["por_uf"], "por_esfera": doc["por_esfera"], "valor_homologado": doc["valor_homologado"]}
    sigla = uf.strip().upper()
    linha = next((x for x in doc["por_uf"] if x["uf"] == sigla), None)
    if not linha:
        raise EmpresasErro(404, f"UF {sigla} sem contratação de operadora nas leituras do snapshot.")
    return {**out, "uf": sigla, **{k: linha[k] for k in ("itens", "contratacoes", "valor")}}
