# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""core/geoip.py: UF pelo nome do estado e município a partir da "cidade" da base (DB-IP)."""
from core.geoip import extrair_geo, municipio, normaliza, uf_do_registro


def _dbip(cidade, estado, lat, lon, pais="BR"):
    # Formato do DB-IP City Lite: sem iso_code na subdivisão, cidade só em inglês.
    return {"city": {"names": {"en": cidade}}, "country": {"iso_code": pais},
            "subdivisions": [{"names": {"en": estado}}], "location": {"latitude": lat, "longitude": lon}}


def test_uf_pelo_nome_do_estado_e_federal_district():
    assert uf_do_registro(_dbip("Brasília", "Federal District", -15.8, -47.9)) == "DF"
    assert uf_do_registro(_dbip("Recife", "Pernambuco", -8.05, -34.9)) == "PE"


def test_uf_do_geolite_continua_lida_e_fora_do_brasil_fica_vazia():
    assert uf_do_registro({"country": {"iso_code": "BR"}, "subdivisions": [{"iso_code": "BR-SP"}]}) == "SP"
    assert uf_do_registro(_dbip("Miami", "Florida", 25.7, -80.2, pais="US")) == ""


def test_municipio_por_nome_e_sem_acento():
    assert municipio("Sao Paulo", "SP", -23.55, -46.63) == "São Paulo"
    assert municipio("Belo Horizonte (Centro)", "MG", -19.9, -43.9) == "Belo Horizonte"


def test_bairro_vira_o_municipio_pelo_centroide_em_raios():
    # Pinheiros, na capital paulista: o centroide de Osasco está mais perto em km, mas São Paulo é bem maior.
    assert municipio("Pinheiros", "SP", -23.5611, -46.6876) == "São Paulo"


def test_nome_com_erro_de_grafia_e_aceito_se_o_municipio_estiver_perto():
    assert municipio("Culaba", "MT", -15.6, -56.1) == "Cuiabá"
    # Parecido com "Serro", mas o ponto está a centenas de km: mantém o que a base diz.
    assert municipio("Serra", "MG", -30.0, -51.0) == "Serra"


def test_extrair_geo_resolve_municipio_so_no_brasil():
    g = extrair_geo(_dbip("Pinheiros", "São Paulo", -23.5611, -46.6876))
    assert g == {"lat": -23.5611, "lon": -46.6876, "city": "São Paulo", "country": "BR", "uf": "SP"}
    fora = extrair_geo(_dbip("Miami", "Florida", 25.7, -80.2, pais="US"))
    assert fora["city"] == "Miami" and fora["uf"] == ""
    assert extrair_geo({"city": {"names": {"en": "X"}}}) is None


def test_normaliza():
    assert normaliza("São João d'Aliança") == "SAO JOAO D ALIANCA"
