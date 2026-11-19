# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — código de IXP com componente de caminho > 255 bytes vira 404, não 500.

O fuzz (test_t4_fuzz) achou o caso por acaso: `Path.exists()` levanta OSError(ENAMETOOLONG) e a rota
`/ixps/{code}/hilbert/v4/detail` respondia 500. Este teste fixa a entrada, sem depender da aleatoriedade do fuzz.
"""
import pytest

from tests.products.api_contract import ALLOWED

CODIGO_LONGO = "0" * 27 + "\u0080" * 200          # > 255 bytes em UTF-8


@pytest.mark.parametrize("sufixo", [
    "hilbert/v4/detail?slash8=0",
    "hilbert/v4/detail?slash8=0&peer=64500",
    "hilbert/v4",
    "hilbert/v6",
])
def test_codigo_de_ixp_longo_nao_gera_5xx(api, sufixo):
    r = api.get(f"/api/v1/ixps/{CODIGO_LONGO}/{sufixo}", headers=ALLOWED)
    assert r.status_code == 404, f"{sufixo} → {r.status_code}: {r.text[:200]}"
