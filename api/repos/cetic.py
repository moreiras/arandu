# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Pesquisas TIC do Cetic.br publicadas: `cetic/domicilios.json.gz` e `cetic/provedores.json.gz`."""
from __future__ import annotations

from typing import Optional

from api.repos.base import ArtifactRepo
from core.cetic_microdados import REGIOES_UF  # noqa: F401  (reexportado: api/services/cetic.py)

PESQUISAS = ("domicilios", "provedores")


class CeticRepo(ArtifactRepo):
    def doc(self, date_str: str, pesquisa: str) -> Optional[dict]:
        return self.ler(date_str, f"cetic/{pesquisa}.json.gz") if pesquisa in PESQUISAS else None

    def uf_doc(self, date_str: str) -> Optional[dict]:
        """Estimativas por UF dos microdados da TIC Domicílios: `cetic/domicilios_uf.json.gz`."""
        return self.ler(date_str, "cetic/domicilios_uf.json.gz")

    def demanda_oferta_doc(self, date_str: str) -> Optional[dict]:
        """Demanda × oferta de banda larga fixa: `mercado/demanda_oferta.json.gz`."""
        return self.ler(date_str, "mercado/demanda_oferta.json.gz")
