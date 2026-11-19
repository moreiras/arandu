# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — IBGE SIDRA (Censo 2022 e PNAD): resposta no formato original → normalizado, sem rede."""
import gzip
import json

import httpx
import pytest
import respx

from core.common import read_json_gz
from sources.ibge_censo_pnad import collect as fonte


def _r(fx, nome):
    return json.loads(fx("ibge_sidra", f"sidra_{nome}.json").read_text(encoding="utf-8"))


def _norm(fx):
    return fonte.normalizar_municipios(_r(fx, "4714"), _r(fx, "4712"), _r(fx, "6579"))


def test_normaliza_municipios_com_uf_pelo_codigo_e_sem_inventar_zero(fx):
    muns, ano, est_ano = _norm(fx)
    assert ano == "2022" and est_ano == "2026" and len(muns) == 7
    sp = muns["3550308"]
    assert sp == {"nome": "São Paulo", "uf": "SP", "populacao": 11451999, "populacao_estimada": 11911337, "area_km2": 1521.202, "domicilios": 4307665, "moradores": 11395157}
    novo = muns["5101837"]                                 # criado depois do Censo: só a estimativa
    assert novo == {"nome": "Boa Esperança do Norte", "uf": "MT", "populacao_estimada": 7000}
    assert muns["1100015"]["nome"] == "Alta Floresta D'Oeste" and muns["1100015"]["uf"] == "RO"
    df = muns["4306502"]                                   # "..." na SIDRA: sem o campo, nunca zero
    assert "domicilios" not in df and "moradores" not in df and df["populacao"] == 14000


def test_taxa_de_internet_por_uf_com_cv(fx):
    por, ano = fonte.normalizar_taxa_internet(_r(fx, "7307"))
    assert ano == "2025" and len(por) == 27 and "BR" not in por
    sp = por["SP"]
    assert 0 < sp["taxa"] <= 1 and sp["taxa"] == round(sp["com_internet_mil"] / sp["domicilios_mil"], 4)
    assert sp["cv_domicilios_pct"] > 0


def test_serie_de_domicilios_da_pnad_por_uf_e_ano(fx):
    serie = fonte.normalizar_serie_domicilios(_r(fx, "7307-serie"))
    assert len(serie) == 27 and set(serie["SP"]) == {"2022", "2023", "2024", "2025"}
    assert serie["SP"]["2025"] > serie["SP"]["2022"] > 0


def test_numero_trata_codigos_de_ausencia_da_sidra():
    assert fonte.numero("...") is None and fonte.numero("-") is None and fonte.numero("X") is None and fonte.numero("12.5") == 12.5


def _mock(fx):
    for nome, caminho in fonte.CONSULTAS.items():
        respx.get(fonte.BASE + caminho).respond(200, json=_r(fx, nome))


@respx.mock
def test_run_grava_bruto_e_normalizado(base, log, fx, date_str, monkeypatch):
    monkeypatch.setattr(fonte, "MINIMO_MUNICIPIOS", 5)
    _mock(fx)
    r = fonte.run(date_str, base, log, espera_s=0)
    assert r == {"municipios": 7, "censo_ano": "2022", "estimativa_ano": "2026", "pnad_ano": "2025"}
    norm = base / "normalized" / date_str / "summary"
    m = read_json_gz(norm / "ibge_municipios.json.gz")
    assert m["total"] == 7 and m["municipios"]["3304557"]["uf"] == "RJ" and m["censo_ano"] == "2022" and m["estimativa_ano"] == "2026"
    t = read_json_gz(norm / "ibge_taxa_internet.json.gz")
    assert len(t["ufs"]) == 27 and t["pnad_ano"] == "2025" and set(t["ufs"]["SP"]["domicilios_mil_por_ano"]) == {"2022", "2023", "2024", "2025"}
    assert t["brasil"]["domicilios_mil"] == sum(u["domicilios_mil"] for u in t["ufs"].values())
    bruto = base / "raw" / date_str / "summary" / "ibge-sidra-4714-2022.json.gz"
    assert json.loads(gzip.decompress(bruto.read_bytes()))[1]["D1C"] == "3550308"
    assert (base / "raw" / date_str / "summary" / "ibge-sidra-7307-2025.json.gz").exists()


@respx.mock
def test_resposta_truncada_falha_alto_e_nao_grava(base, log, fx, date_str):
    _mock(fx)                                              # 7 municípios < 5.500: parece truncada
    with pytest.raises(RuntimeError, match="municípios"):
        fonte.run(date_str, base, log, espera_s=0)
    assert not (base / "normalized" / date_str / "summary" / "ibge_municipios.json.gz").exists()


@respx.mock
def test_erro_http_tenta_de_novo_e_depois_falha(base, log, date_str, monkeypatch):
    monkeypatch.setattr(fonte, "ESPERA_S", 0)
    rota = respx.get(fonte.BASE + fonte.CONSULTAS["4714"]).respond(503)
    with pytest.raises(httpx.HTTPStatusError):
        fonte.run(date_str, base, log, espera_s=0)
    assert rota.call_count == 3
