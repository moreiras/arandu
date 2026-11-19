# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Produto de reclamações no Consumidor.gov.br publicado: `consumidor/consumidor.json.gz` e as partes por UF dos municípios."""
from __future__ import annotations

from typing import Optional

from api.repos.base import ArtifactRepo


class ConsumidorRepo(ArtifactRepo):
    def consumidor_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "consumidor/consumidor.json.gz")

    def consumidor_municipios_uf(self, date_str: str, uf: str) -> Optional[dict]:
        return self.ler(date_str, f"consumidor/consumidor_municipios/{uf}.json.gz")
