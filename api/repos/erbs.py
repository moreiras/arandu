# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estações do SMP licenciadas publicadas: `erbs/resumo.json.gz`."""
from __future__ import annotations

from typing import Optional

from api.repos.base import ArtifactRepo


class ErbsRepo(ArtifactRepo):
    def resumo_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "erbs/resumo.json.gz")

    def grade_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "erbs/grade.json.gz")
