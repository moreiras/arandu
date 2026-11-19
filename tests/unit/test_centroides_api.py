# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""A API lê uma cópia dos centróides (a imagem dela não leva o frontend/): precisa ser igual à do frontend."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def test_centroides_da_api_e_do_frontend_sao_iguais():
    assert (RAIZ / "config" / "municipios-centroides.json").read_bytes() == \
        (RAIZ / "frontend" / "public" / "municipios-centroides.json").read_bytes()
