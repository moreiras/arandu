# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Prontidão em segurança de roteamento publicada: `prontidao/asns.json.gz`."""
from __future__ import annotations

from typing import Optional

from api.repos.base import ArtifactRepo


class ProntidaoRepo(ArtifactRepo):
    def asns_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "prontidao/asns.json.gz")

    def manrs_doc(self, date_str: str) -> Optional[dict]:
        """Agregado da participação no MANRS: só agregados, com a atribuição exigida pelos termos."""
        return self.ler(date_str, "manrs/resumo.json.gz")
