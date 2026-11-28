# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Penetração e mercado não visto publicados: `territorio/municipios.json.gz`."""
from __future__ import annotations

from typing import Optional

from api.repos.base import ArtifactRepo


class TerritorioRepo(ArtifactRepo):
    def municipios_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "territorio/municipios.json.gz")

    def rede_doc(self, date_str: str) -> Optional[dict]:
        """`territorio/rede_territorio.json.gz`: IPv6 estimado, usuários atrás de ROV e dependência de trânsito."""
        return self.ler(date_str, "territorio/rede_territorio.json.gz")

    def area_influencia_doc(self, date_str: str) -> Optional[dict]:
        """`territorio/area_influencia_ptt.json.gz`: área de influência observada de cada PTT, por visão, e o índice por município."""
        return self.ler(date_str, "territorio/area_influencia_ptt.json.gz")

    def regiao_doc(self, date_str: str) -> Optional[dict]:
        """`territorio/regiao.json.gz`: ASNs por município e a tabela de fatos por ASN."""
        return self.ler(date_str, "territorio/regiao.json.gz")
