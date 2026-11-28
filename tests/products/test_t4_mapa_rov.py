# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 — Mapa Explorer, `color_by="rov"`: a faixa por ASN usa a regra e o mínimo de amostras do produto `seguranca`."""
import pytest

from api.services.mapas import MapasService
from core.rov_faixas import MIN_AMOSTRAS, faixa_rov
from tests.products.api_contract import ALLOWED


@pytest.mark.parametrize("rov,esperado", [
    (None, "sem_dado"),
    ({}, "sem_dado"),
    ({"validates_pct": None, "amostras": 500}, "sem_dado"),
    ({"validates_pct": 99.0, "amostras": MIN_AMOSTRAS - 1}, "amostra_insuficiente"),
    ({"validates_pct": 99.0}, "amostra_insuficiente"),
    ({"validates_pct": 0.0, "amostras": MIN_AMOSTRAS}, "ate_10"),
    ({"validates_pct": 10.0, "amostras": 500}, "ate_10"),
    ({"validates_pct": 10.01, "amostras": 500}, "de_10_a_90"),
    ({"validates_pct": 90.0, "amostras": 500}, "de_10_a_90"),
    ({"validates_pct": 90.01, "amostras": 500}, "acima_de_90"),
])
def test_faixa_rov_do_asn(rov, esperado):
    assert faixa_rov(rov) == esperado


def test_valor_de_cor_rov_le_a_faixa_da_linha():
    assert MapasService._map_color_value({"rov_faixa": "acima_de_90"}, "rov") == "acima_de_90"
    assert MapasService._map_color_value({}, "rov") == "sem_dado"


def test_map_query_rov_traz_faixa_por_asn_do_dataset_sintetico(api):
    r = api.post("/api/v1/map/query", json={"layers": ["asns_geo"], "color_by": "rov"}, headers=ALLOWED)
    assert r.status_code == 200, r.text[:300]
    por_asn = {f["properties"]["asn"]: f["properties"] for f in r.json()["features"]}
    assert por_asn, "o dataset sintético deveria ter sedes de AS"
    assert 64503 in por_asn and 64505 in por_asn
    assert por_asn[64503]["color_value"] == "acima_de_90" and por_asn[64503]["rov_faixa"] == "acima_de_90" and por_asn[64503]["rov_pct"] == 97.0
    assert por_asn[64505]["color_value"] == "amostra_insuficiente"
    validos = {"ate_10", "de_10_a_90", "acima_de_90", "amostra_insuficiente", "sem_dado"}
    assert {p["color_value"] for p in por_asn.values()} <= validos
    assert all(p["color_value"] == p["rov_faixa"] for p in por_asn.values())


def test_outros_color_by_nao_trazem_campos_do_rov(api):
    r = api.post("/api/v1/map/query", json={"layers": ["asns_geo"], "color_by": "rpki"}, headers=ALLOWED)
    assert r.status_code == 200
    assert all("rov_faixa" not in f["properties"] for f in r.json()["features"])


def test_color_by_invalido_continua_rejeitado(api):
    r = api.post("/api/v1/map/query", json={"layers": ["asns_geo"], "color_by": "vermelho"}, headers=ALLOWED)
    assert r.status_code in (400, 422)
