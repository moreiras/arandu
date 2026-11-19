# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Produtos de qualidade e reclamações publicados: `qualidade/{rqual,reclamacoes}.json.gz` e as partes por UF dos municípios."""
from __future__ import annotations

from typing import Optional

from api.repos.base import ArtifactRepo


class QualidadeRepo(ArtifactRepo):
    def rqual_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "qualidade/rqual.json.gz")

    def reclamacoes_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "qualidade/reclamacoes.json.gz")

    def rqual_municipios_uf(self, date_str: str, uf: str) -> Optional[dict]:
        return self.ler(date_str, f"qualidade/rqual_municipios/{uf}.json.gz")

    def reclamacoes_municipios_uf(self, date_str: str, uf: str) -> Optional[dict]:
        return self.ler(date_str, f"qualidade/reclamacoes_municipios/{uf}.json.gz")
