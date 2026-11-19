# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Instalações do PeeringDB publicadas: `instalacoes/{instalacoes,vinculos,atributos_rede,portas_externas,portas_ixbr}.json.gz`."""
from __future__ import annotations

from typing import Optional

from api.repos.base import ArtifactRepo


class InstalacoesRepo(ArtifactRepo):
    def instalacoes_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "instalacoes/instalacoes.json.gz")

    def vinculos_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "instalacoes/vinculos.json.gz")

    def atributos_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "instalacoes/atributos_rede.json.gz")

    def portas_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "instalacoes/portas_externas.json.gz")

    def portas_ixbr_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "instalacoes/portas_ixbr.json.gz")
