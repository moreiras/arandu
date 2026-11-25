# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 (PT-17, D12): `/sem-declaracao-sici` e os nomes antigos como alias (rota, collection)."""
from tests.products.api_contract import ALLOWED
from tests.synth.world import T1


def _get(api, caminho, **params):
    r = api.get(f"/api/v1{caminho}", params={"date": T1, **params}, headers=ALLOWED)
    assert r.status_code == 200, r.text[:300]
    return r


def test_rota_nova_e_alias_antigo_com_aviso_de_depreciacao(api):
    nova = _get(api, "/sem-declaracao-sici", limit=50)
    velha = _get(api, "/omissao-sici", limit=50)
    assert "aviso_depreciacao" not in nova.json() and "deprecation" not in nova.headers
    assert velha.headers["deprecation"] == "true" and "/sem-declaracao-sici" in velha.headers["link"]
    corpo = velha.json()
    assert "/sem-declaracao-sici" in corpo.pop("aviso_depreciacao")
    assert corpo == nova.json()
    assert nova.json()["total"] > 0


def test_alias_aceita_os_mesmos_parametros_e_recusa_os_mesmos_erros(api):
    for caminho in ("/sem-declaracao-sici", "/omissao-sici"):
        assert api.get(f"/api/v1{caminho}", params={"date": T1, "tipo": "x"}, headers=ALLOWED).status_code == 400
        assert api.get(f"/api/v1{caminho}", params={"date": T1, "grupo_declara": "talvez"}, headers=ALLOWED).status_code == 400
        assert _get(api, caminho, tipo="parou_de_declarar").json()["tipo"] == "parou_de_declarar"


def test_collection_antiga_responde_pela_nova_com_aviso(api):
    novo = api.post("/api/v1/query/sem_declaracao_sici", json={"limit": 5}, params={"date": T1}, headers=ALLOWED).json()
    velho = api.post("/api/v1/query/omissao_sici", json={"limit": 5}, params={"date": T1}, headers=ALLOWED).json()
    assert "aviso_obsoleta" not in novo and "sem_declaracao_sici" in velho.pop("aviso_obsoleta")
    assert velho == novo and novo["total"] > 0


def test_schema_da_collection_antiga_descreve_a_nova(api):
    r = api.get("/api/v1/schema", params={"collection": "omissao_sici"}, headers=ALLOWED)
    assert r.status_code == 200, r.text[:200]
    assert r.json()["collection"] == "sem_declaracao_sici" and "aviso_obsoleta" in r.json()
    assert "omissao_sici" not in api.get("/api/v1/schema", headers=ALLOWED).json()["collections"]
