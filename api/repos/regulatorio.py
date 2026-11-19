# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Produtos regulatórios publicados: `regulatorio/{fust,multas,faixas,satelites}.json.gz`."""
from __future__ import annotations

from typing import Optional

from api.repos.base import ArtifactRepo


class RegulatorioRepo(ArtifactRepo):
    def fust_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "regulatorio/fust.json.gz")

    def multas_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "regulatorio/multas.json.gz")

    def faixas_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "regulatorio/faixas.json.gz")

    def satelites_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "regulatorio/satelites.json.gz")
