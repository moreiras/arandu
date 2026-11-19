# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estações do SMP por município, UF e operadora: valores plantados com resultado conhecido."""
from products.erbs.build import calcular, grade, publicar_erbs
from core.jsonio import carregar_json_gz, gravar_json_gz


class _Log:
    def info(self, *a, **k): pass
    warning = info


IBGE = {"1": {"nome": "Alfa", "uf": "AA", "populacao_estimada": 20000}, "2": {"nome": "Beta", "uf": "AA", "populacao": 5000}, "3": {"nome": "Gama", "uf": "BB", "populacao": 1000}}
SMPS = [{"cnpj": "11111111000111", "razao_social": "Operadora Um S.A."}]


def _e(ibge, marca, cnpj, ger, entidade="X", t5=()):
    return {"ibge": ibge, "marca": marca, "entidade": entidade, "cnpj": cnpj, "geracoes": ger, "tipo_5g": list(t5)}


EST = [_e("1", "UM", "11111111000111", ["4G", "5G"], t5=["SA"]), _e("1", "UM", "11111111000111", ["4G"]), _e("1", "DOIS", "22222222000122", ["2G", "4G"]),
       _e("2", "UM", None, ["4G"], entidade="OPERADORA UM S/A"), _e("2", "TRES", None, ["3G"], entidade="Sem Outorga"), _e("9", "UM", "11111111000111", ["4G"]), _e(None, "UM", "11111111000111", ["4G"])]


def test_contagens_por_municipio_uf_e_geracao():
    r = calcular([dict(e) for e in EST], IBGE, SMPS)
    m1 = r["municipios"]["1"]
    assert m1["estacoes"] == 3 and m1["geracoes"] == {"2G": 1, "3G": 0, "4G": 3, "5G": 1} and m1["por_10mil_hab"] == 1.5 and m1["operadoras"]["11111111000111"] == 2
    assert r["municipios"]["2"]["por_10mil_hab"] == 4.0 and "3" not in r["municipios"]
    aa = r["ufs"]["AA"]
    assert aa["estacoes"] == 5 and aa["municipios"] == 2 and aa["municipios_com_estacao"] == 2 and aa["municipios_com_5g"] == 1 and aa["operadoras"] == 3
    assert r["ufs"]["BB"]["estacoes"] == 0 and r["brasil"]["municipios_com_estacao"] == 2


def test_cnpj_recuperado_pela_razao_social_e_o_que_nao_casa_fica_so_com_a_marca():
    r = calcular([dict(e) for e in EST], IBGE, SMPS)
    c = r["casamento"]
    assert c["sem_cnpj_no_arquivo"] == 2 and c["sem_cnpj_apos_razao_social"] == 1 and c["marcas_sem_cnpj"] == ["TRES"]
    assert r["municipios"]["2"]["operadoras"] == {"11111111000111": 1, "TRES": 1}
    um = next(o for o in r["operadoras"] if o["cnpj"] == "11111111000111")
    assert um["estacoes"] == 5 and um["municipios"] == 2 and um["tipo_5g"] == {"SA": 1}
    assert r["operadoras"][0]["estacoes"] >= r["operadoras"][-1]["estacoes"]


def test_estacao_com_municipio_fora_do_ibge_ou_sem_municipio_conta_no_pais_mas_nao_no_municipio():
    r = calcular([dict(e) for e in EST], IBGE, SMPS)
    assert r["brasil"]["estacoes"] == 7 and r["brasil"]["estacoes_em_municipio_do_ibge"] == 5 and r["casamento"]["com_municipio_no_ibge"] == 5


def test_sanidade_contra_o_sici_movel():
    r = calcular([dict(e) for e in EST], IBGE, SMPS, {"1": {"acessos": 10}, "3": {"acessos": 5}, "2": {"acessos": 0}})
    assert r["casamento"]["sanidade_sici_movel"] == {"municipios_com_acessos_moveis": 2, "dos_quais_com_estacao": 1, "com_estacao_sem_acessos_moveis": 1}


def test_publicar_exige_as_entradas_e_rotula_como_cadastro(tmp_path):
    assert publicar_erbs(tmp_path, "2026-01-01", _Log()) == {}
    norm = tmp_path / "normalized" / "2026-01-01" / "summary"
    norm.mkdir(parents=True)
    gravar_json_gz(norm / "anatel_erbs.json.gz", {"estacoes": [dict(e) for e in EST], "data_arquivo": "Sun, 01 Nov 2026"})
    gravar_json_gz(norm / "ibge_municipios.json.gz", {"municipios": IBGE})
    out = publicar_erbs(tmp_path, "2026-01-01", _Log())
    assert out["estacoes"] == 7 and out["municipios_com_estacao"] == 2
    doc = carregar_json_gz(tmp_path / "published" / "2026-01-01" / "erbs" / "resumo.json.gz")
    assert doc["natureza"] == "cadastro_licenciamento" and "não é cobertura" in doc["limites"] and "sanidade_sici_movel" not in doc["casamento"]


def test_grade_agrega_em_celulas_de_2_km_e_ignora_estacao_sem_posicao():
    e = [dict(_e("1", "UM", "1", ["4G", "5G"]), lat=-23.601, lon=-46.701), dict(_e("1", "UM", "1", ["4G"]), lat=-23.605, lon=-46.705),
         dict(_e("1", "UM", "1", ["2G"]), lat=-10.0, lon=-50.0), dict(_e("1", "UM", "1", ["4G"]), lat=None, lon=None)]
    g = grade(e)
    assert len(g) == 2
    c = next(x for x in g if x[2] == 2)
    assert c[3:] == [0, 0, 2, 1] and abs(c[0] - (-46.71)) < 0.011 and abs(c[1] - (-23.61)) < 0.011
    assert next(x for x in g if x[2] == 1)[3:] == [1, 0, 0, 0]
