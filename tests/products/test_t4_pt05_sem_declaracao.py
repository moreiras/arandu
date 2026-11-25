# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 (PT-05): Sem declaração ao SICI: `grupo_declara` com três estados (RANKINGS-E2)."""
from tests.products.api_contract import ALLOWED
from tests.synth.world import T1


def _get(api, caminho, **params):
    r = api.get(f"/api/v1{caminho}", params={"date": T1, **params}, headers=ALLOWED)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_sem_declaracao_grupo_declara_aceita_tres_estados(api):
    """RANKINGS-E2: `false` não traz os sem grupo; `desconhecido` os traz; os três somam o total."""
    tot = lambda **kw: _get(api, "/sem-declaracao-sici", **kw)["total"]   # noqa: E731
    assert tot(grupo_declara="true") + tot(grupo_declara="false") + tot(grupo_declara="desconhecido") == tot()
    assert api.get("/api/v1/sem-declaracao-sici", params={"date": T1, "grupo_declara": "talvez"}, headers=ALLOWED).status_code == 400
