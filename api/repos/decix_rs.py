# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""DE-CIX Rio e São Paulo nos route servers: `decix_rs/ixps.json.gz`."""
from __future__ import annotations

from typing import Optional

from api.repos.base import ArtifactRepo


class DecixRsRepo(ArtifactRepo):
    def ixps_doc(self, date_str: str) -> Optional[dict]:
        return self.ler(date_str, "decix_rs/ixps.json.gz")
