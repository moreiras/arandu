# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Demanda × oferta de banda larga fixa: UFs plantadas com a classe conhecida."""
from products.demanda_oferta.build import calcular, publicar_demanda_oferta
from core.jsonio import carregar_json_gz, gravar_json_gz


class _Log:
    def info(self, *a, **k): pass
    warning = info


def _bl(prop, se, precisao="adequada"):
    return {"indicadores": {"banda_larga_fixa": {"proporcao": prop, "erro_padrao": se, "margem": round(1.96 * se, 3), "cv": se / prop, "precisao": precisao}}}


PEN = {"SP": {"domicilios_projetados": 1_000_000, "acessos_pf": 650_000},
       "RJ": {"domicilios_projetados": 1_000_000, "acessos_pf": 900_000},
       "AL": {"domicilios_projetados": 1_000_000, "acessos_pf": 300_000},
       "AC": {"domicilios_projetados": 100_000, "acessos_pf": 10_000}}
TIC = {"SP": _bl(65, 2), "RJ": _bl(60, 2), "AL": _bl(60, 2), "AC": _bl(50, 20, "baixa"),
       "Sudeste": _bl(62.5, 1.5), "Nordeste": _bl(60, 2), "Norte": _bl(50, 20, "baixa"), "BR": _bl(61, 1)}


def test_classes_e_valores_plantados():
    r = calcular(PEN, TIC)
    sp, rj, al = r["ufs"]["SP"], r["ufs"]["RJ"], r["ufs"]["AL"]
    assert sp["demanda_domicilios"] == 650_000 and sp["razao"] == 1.0 and sp["classe"] == "compativel"
    assert sp["nao_visto"] == 0 and sp["nao_visto_max"] == 39_200 and sp["nao_visto_min"] == 0
    assert al["classe"] == "oferta_abaixo_da_demanda" and al["nao_visto"] == 300_000 and al["razao_max"] < 1
    assert al["nao_visto_min"] == 300_000 - 39_200
    assert rj["classe"] == "oferta_acima_da_demanda" and rj["nao_visto"] == 0 and rj["razao_min"] > 1


def test_precisao_baixa_e_indeterminada_e_sem_conclusao():
    ac = calcular(PEN, TIC)["ufs"]["AC"]
    assert ac["classe"] == "indeterminado" and "precisão baixa" in ac["motivo"]


def test_grupo_sem_estimativa_e_indeterminado_sem_inventar_numero():
    r = calcular(PEN, {k: v for k, v in TIC.items() if k != "SP"})
    assert r["ufs"]["SP"]["classe"] == "indeterminado" and "razao" not in r["ufs"]["SP"]


def test_regiao_e_brasil_somam_as_ufs_e_usam_a_proporcao_do_proprio_grupo():
    r = calcular(PEN, TIC)
    sud = r["regioes"]["Sudeste"]
    assert sud["domicilios_projetados"] == 2_000_000 and sud["oferta_acessos_pf"] == 1_550_000
    assert sud["demanda_domicilios"] == 1_250_000 and sud["proporcao_bl_fixa"] == 62.5
    assert r["brasil"]["domicilios_projetados"] == 3_100_000 and r["brasil"]["oferta_acessos_pf"] == 1_860_000


def test_publicar_exige_penetracao_e_tic(tmp_path):
    assert publicar_demanda_oferta(tmp_path, "2026-01-01", _Log()) == {}
    pub = tmp_path / "published" / "2026-01-01"
    (pub / "territorio").mkdir(parents=True)
    (pub / "cetic").mkdir()
    gravar_json_gz(pub / "territorio" / "municipios.json.gz", {"ufs": PEN, "mes_referencia_sici": "2026-08", "pnad_ano": "2025"})
    gravar_json_gz(pub / "cetic" / "domicilios_uf.json.gz", {"grupos": TIC, "edicao": 2025})
    out = publicar_demanda_oferta(tmp_path, "2026-01-01", _Log())
    assert out["ufs"] == 4 and out["oferta_abaixo_da_demanda"] == 1
    doc = carregar_json_gz(pub / "mercado" / "demanda_oferta.json.gz")
    assert doc["natureza"] == "estimativa_arandurape" and doc["tic_edicao"] == 2025 and doc["mes_referencia_sici"] == "2026-08"
