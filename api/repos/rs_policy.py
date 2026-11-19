# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Rejeições, communities e política dos route servers do IX.br publicadas: `rs_policy/*.json.gz`."""
from __future__ import annotations

from typing import Optional

from api.repos.base import ArtifactRepo


class RsPolicyRepo(ArtifactRepo):
    def ixps_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "rs_policy/ixps.json.gz")

    def asns_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "rs_policy/asns.json.gz")

    def communities_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "rs_policy/communities.json.gz")

    def grafo_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "rs_policy/grafo.json.gz")

    def linhas_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "rs_policy/linhas.json.gz")
