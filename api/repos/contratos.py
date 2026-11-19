# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Contratos públicos publicados: `contratos/operadoras.json.gz`, `municipios.json.gz` e `resumo.json.gz`."""
from __future__ import annotations

from typing import Optional

from api.repos.base import ArtifactRepo


class ContratosRepo(ArtifactRepo):
    def operadoras_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "contratos/operadoras.json.gz")

    def municipios_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "contratos/municipios.json.gz")

    def resumo_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "contratos/resumo.json.gz")
