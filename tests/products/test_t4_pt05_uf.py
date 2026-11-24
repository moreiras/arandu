# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 (PT-05): Operadoras presentes na UF (UF-E2)."""
import pytest

from tests.products.api_contract import ALLOWED
from tests.synth.world import T1


def _get(api, caminho, **params):
    r = api.get(f"/api/v1{caminho}", params={"date": T1, **params}, headers=ALLOWED)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_operadoras_presentes_na_uf(api):
    """UF-E2: quem tem acesso na UF, com os acessos na UF; soma = total da UF; um CNPJ, uma linha."""
    for uf in ("SP", "ES", "MG", "RJ"):
        r = api.get(f"/api/v1/ufs/{uf}", params={"date": T1}, headers=ALLOWED)
        if r.status_code != 200:
            continue
        p = r.json()
        pres = p["operadoras_presentes"]
        if not pres["total"]:
            continue
        assert pres["acessos"] == p["totais"]["acessos"]
        itens = pres["items"]
        assert len({i["cnpj"] for i in itens}) == len(itens)
        assert all(i["acessos"] <= i["acessos_brasil"] for i in itens)
        assert [i["acessos"] for i in itens] == sorted((i["acessos"] for i in itens), reverse=True)
        if pres["total"] <= 10:
            assert sum(i["share"] for i in itens) == pytest.approx(100, abs=0.1)
        return
    pytest.fail("nenhuma UF do sintético com operadoras presentes")
