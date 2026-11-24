# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Resolução de lugar com homônimos (LOC-E4)."""
from types import SimpleNamespace

import pytest

# ── LOC-E4: homônimos na resolução de lugar ──

def test_place_ufs_separa_homonimos():
    from api.store import Store
    orgs = {1: {"city": "Bom Jesus", "uf": "PI", "lat": -9.0, "lon": -44.3}, 2: {"city": "BOM JESUS", "uf": "RN", "lat": -5.9, "lon": -35.5},
            3: {"city": "Bom Jesus", "uf": "PI", "lat": -9.1, "lon": -44.4}, 4: {"city": "Bom Jesus", "uf": "RN", "lat": None, "lon": None}}
    fake = SimpleNamespace(_load_geo_orgs=lambda d: orgs)
    assert Store.place_ufs(fake, "d", "bom jesus") == {"PI": 2, "RN": 1}
    r = Store.resolve_place(fake, "d", "Bom Jesus", "PI")
    assert r["n"] == 2 and r["lat"] == pytest.approx(-9.05)
