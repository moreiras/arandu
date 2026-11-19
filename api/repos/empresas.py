# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cadastro das empresas de telecom publicado: `empresas/cadastro.json.gz` (mercado) e `empresas/operadoras/{NN}.json.gz` (operadoras, em faixas pela raiz do CNPJ)."""
from __future__ import annotations

from typing import Optional

from api.repos.base import ArtifactRepo


class EmpresasRepo(ArtifactRepo):
    def cadastro_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "empresas/cadastro.json.gz")

    def operadoras_faixa(self, date_str: str, faixa: str) -> Optional[dict]:
        return self.ler(date_str, f"empresas/operadoras/{faixa}.json.gz")
