# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 (PT-05): Resolução de lugar com homônimos (LOC-E4)."""
from tests.products.api_contract import ALLOWED
from tests.synth.world import T1


def _get(api, caminho, **params):
    r = api.get(f"/api/v1{caminho}", params={"date": T1, **params}, headers=ALLOWED)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_resolve_place_homonimos(api, monkeypatch):
    """LOC-E4: nome em duas UFs sem UF não vira a mediana das duas; com UF (parâmetro ou "Nome/UF") resolve."""
    store = api.app.state.store
    vistos = []
    monkeypatch.setattr(store, "place_ufs", lambda d, nome: {"PI": 2, "RN": 1})
    monkeypatch.setattr(store, "resolve_place", lambda d, nome, uf=None: vistos.append((nome, uf)) or {"lat": -9.0, "lon": -44.3, "n": 2})
    amb = _get(api, "/resolve/place", q="Bom Jesus")
    assert amb["ambiguo"] is True and amb["ufs"] == {"PI": 2, "RN": 1} and amb["lat"] is None
    assert _get(api, "/resolve/place", q="Bom Jesus/PI")["lat"] == -9.0
    assert _get(api, "/resolve/place", q="Bom Jesus", uf="pi")["uf"] == "PI"
    assert vistos == [("Bom Jesus", "PI"), ("Bom Jesus", "PI")]
