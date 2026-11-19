# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cadastro das empresas de telecom: consultas sobre `empresas/cadastro.json.gz` e as faixas de operadoras. Funções puras."""
from __future__ import annotations

import re
from typing import Optional

_META = ("snapshot_date", "natureza", "fonte", "dump_reference", "mes_referencia_sici", "limites")


class EmpresasErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


def raiz_do_cnpj(cnpj: str) -> str:
    """Raiz (8 dígitos) de um CNPJ com ou sem pontuação, de 8 ou 14 dígitos."""
    d = re.sub(r"\D", "", cnpj or "")
    if len(d) not in (8, 14):
        raise EmpresasErro(400, "CNPJ inválido: informe a raiz (8 dígitos) ou o CNPJ completo (14 dígitos).")
    return d[:8]


def mercado(doc: dict, uf: Optional[str] = None) -> dict:
    """Mercado de telecom do cadastro: entradas e baixas por ano (total ou de uma UF), ativas por UF e por porte."""
    m = doc["mercado"]
    out = {k: doc.get(k) for k in _META}
    if uf:
        u = uf.strip().upper()
        if u not in m["ativas_por_uf"] and not any(u in e["por_uf"] for e in m["entradas_por_ano"] + m["baixas_por_ano"]):
            raise EmpresasErro(404, f"UF {u} sem empresas de telecom no cadastro.")
        pega = lambda lista: [{"ano": e["ano"], "total": e["por_uf"].get(u, 0)} for e in lista if e["por_uf"].get(u)]      # noqa: E731
        return {**out, "uf": u, "entradas_por_ano": pega(m["entradas_por_ano"]), "baixas_por_ano": pega(m["baixas_por_ano"]), "ativas": m["ativas_por_uf"].get(u, 0), "resumo": doc["resumo"]}
    return {**out, "entradas_por_ano": [{"ano": e["ano"], "total": e["total"]} for e in m["entradas_por_ano"]], "baixas_por_ano": [{"ano": e["ano"], "total": e["total"]} for e in m["baixas_por_ano"]],
            "ativas_por_uf": m["ativas_por_uf"], "ativas_por_porte": m["ativas_por_porte"], "resumo": doc["resumo"]}


def operadora(meta: dict, faixa_doc: Optional[dict], raiz: str) -> dict:
    """Documento de uma operadora pela raiz do CNPJ; 404 se a raiz não tem cadastro."""
    d = ((faixa_doc or {}).get("operadoras") or {}).get(raiz)
    if not d:
        raise EmpresasErro(404, f"Operadora {raiz} sem cadastro de telecom no snapshot.")
    return {**{k: meta.get(k) for k in _META}, **d}
