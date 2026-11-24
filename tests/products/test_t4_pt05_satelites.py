# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 (PT-05): NGEO um sistema por linha (REGULATORIO-E1)."""
from tests.products.api_contract import ALLOWED
from tests.synth.world import T1


def _get(api, caminho, **params):
    r = api.get(f"/api/v1{caminho}", params={"date": T1, **params}, headers=ALLOWED)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_satelites_ngeo_um_sistema_por_linha(api):
    """REGULATORIO-E1: registros por ano de agenda e cópias viram um sistema com a faixa declarada."""
    r = _get(api, "/satelites/resumo")
    assert r["resumo"]["ngeo"] == 4 and r["resumo"]["ngeo_sistemas"] == 2          # 5 linhas plantadas, 1 cópia exata
    novo = next(x for x in r["ngeo_sistemas"] if x["objeto"] == "Sistema Novo LEO")
    assert (novo["registros"], novo["constelacao"], novo["constelacao_min"], novo["constelacao_max"]) == (3, 960, 120, 960)
    assert novo["anos_agenda"] == [2024, 2025, 2026]
