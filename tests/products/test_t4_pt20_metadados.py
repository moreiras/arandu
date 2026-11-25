# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 (PT-20, TRANSV-E12): `/schema` traz fonte, selo e licença por collection."""
from tests.products.api_contract import ALLOWED


def test_schema_de_uma_collection_traz_fontes_selo_e_licenca(api):
    r = api.get("/api/v1/schema", params={"collection": "bloqueios_asn"}, headers=ALLOWED)
    assert r.status_code == 200, r.text[:200]
    j = r.json()
    assert j["selo"] == "fato" and j["uso_comercial_efetivo"] == "restrito"
    assert [f["id"] for f in j["fontes"]] == ["ooni_bloqueios"] and j["fontes"][0]["licenca"]
    assert j["fields"]                                           # o resto do bloco segue igual


def test_schema_completo_cobre_todas_as_collections(api):
    j = api.get("/api/v1/schema", headers=ALLOWED).json()
    assert j["collections"]
    for nome, c in j["collections"].items():
        assert c["fontes"] and c["selo"] in ("fato", "inferido", "estimado") and c["uso_comercial_efetivo"], nome
