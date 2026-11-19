# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Crédito público (BNDES) e sanções (CEIS e CNEP) por operadora. Funções puras sobre `financiamento/operadoras.json.gz`."""
from __future__ import annotations

from typing import Optional

from api.services.empresas import EmpresasErro, raiz_do_cnpj

_META = ("snapshot_date", "natureza", "fontes", "limites")
PARTES = ("financiamento", "sancoes")


def operadora(doc: dict, raiz: str, parte: Optional[str] = None) -> dict:
    """Documento da operadora pela raiz do CNPJ. `parte` limita a `financiamento` ou `sancoes`; 404 se a raiz não tem a parte pedida (ou nenhuma).

    Ausência significa "sem registro nas duas fontes recortadas" e NÃO "sem operação ou sem sanção": o BNDES entra só pelas operações diretas e a CGU na data do arquivo."""
    if parte is not None and parte not in PARTES:
        raise EmpresasErro(400, f"Parte inválida: use {' ou '.join(PARTES)}.")
    d = (doc.get("operadoras") or {}).get(raiz) or {}
    if parte:
        d = {parte: d[parte]} if parte in d else {}
    if not d:
        raise EmpresasErro(404, f"Operadora {raiz} sem {'registro de ' + parte if parte else 'financiamento do BNDES nem sanção do CEIS/CNEP'} neste snapshot (ausência não é prova de que não exista).")
    return {**{k: doc.get(k) for k in _META}, "raiz": raiz, **d}
