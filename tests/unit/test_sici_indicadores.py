# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Indicadores do SICI e outorgas sem declaração: séries plantadas com resultado conhecido."""
import gzip
import json

from products.sici_indicadores.build import (calcular_mercado_grupos, faixa_hhi, serie_municipios, calcular_indicadores, calcular_sem_declaracao, classificar_sem_declaracao, publicar_sici_indicadores,
                                             somar_meses)


class _Log:
    def info(self, *a, **k): pass
    warning = info


def _mes(**ops):
    """{cnpj: (acessos, {ibge: acessos})} -> cnpjs do cache de um mês."""
    out = {}
    for cnpj, (total, muns) in ops.items():
        out[cnpj] = {"empresa": f"EMP{cnpj}", "uf": "SP", "acessos": total,
                     "por_municipio": {i: {"uf": "SP" if i.startswith("35") else "RJ", "nome": f"M{i}", "acessos": a} for i, a in muns.items()}}
    return out


def test_somar_meses_atravessa_o_ano():
    assert somar_meses("2026-01", -1) == "2025-12"
    assert somar_meses("2026-08", -12) == "2025-08"
    assert somar_meses("2025-12", 1) == "2026-01"


def test_share_hhi_lider_e_variacoes():
    atual = _mes(**{"A": (800, {"3550308": 800}), "B": (200, {"3550308": 100, "3304557": 100})})
    ant = _mes(**{"A": (700, {"3550308": 700}), "B": (200, {"3550308": 100, "3304557": 100})})
    ano = _mes(**{"A": (500, {"3550308": 500}), "B": (400, {"3550308": 300, "3304557": 100})})
    r = calcular_indicadores("2026-08", {"2026-08": atual, "2026-07": ant, "2025-08": ano}, {})
    assert r["operadoras"]["A"]["share_br"] == 80.0 and r["operadoras"]["A"]["posicao_br"] == 1
    assert r["operadoras"]["A"]["var_mm"] == {"abs": 100, "pct": 14.29}
    assert r["operadoras"]["B"]["var_aa"] == {"abs": -200, "pct": -50.0}
    assert r["operadoras"]["B"]["ufs"] == {"SP": 100, "RJ": 100}
    sp = r["municipios"]["3550308"]
    assert sp["acessos"] == 900 and sp["n_operadoras"] == 2
    assert sp["hhi"] == round((100 * 800 / 900) ** 2 + (100 * 100 / 900) ** 2)
    assert sp["lider"] == {"cnpj": "A", "empresa": "EMPA", "share": 88.89}
    assert sp["ganho_aa"]["cnpj"] == "A" and sp["perda_aa"]["cnpj"] == "B"
    assert r["brasil"]["acessos"] == 1000 and "lider" not in r["brasil"]


def test_sem_mes_anterior_nao_inventa_variacao():
    r = calcular_indicadores("2026-08", {"2026-08": _mes(A=(10, {"3550308": 10}))}, {})
    assert "var_mm" not in r["operadoras"]["A"] and "var_mm_pct" not in r["municipios"]["3550308"]


def test_declinio_continuo_e_parou_de_declarar():
    def serie(valores, ate="2026-08"):
        return [[somar_meses(ate, -(len(valores) - 1 - i)), v, 0, v] for i, v in enumerate(valores)]
    meses = {"2026-08": _mes(A=(94, {"3550308": 94}), B=(50, {"3550308": 50}))}
    series = {
        "A": serie([100, 99, 98, 97, 96, 95, 94]),                  # 6 quedas seguidas
        "B": serie([40, 45, 50, 49, 50]),                           # sem declínio contínuo
        "C": serie([10, 10, 10], ate="2026-01"),                    # parou há 7 meses
        "D": serie([10, 10], ate="2026-06"),                        # 2 meses: ainda não
        "E": serie([10, 10], ate="2022-01"),                        # há 55 meses: inativo antigo
    }
    r = calcular_indicadores("2026-08", meses, series, {"C": "Empresa C"})
    assert r["parou_de_declarar"]["C"]["empresa"] == "Empresa C"
    assert r["operadoras"]["A"]["meses_declinio"] == 6 and r["operadoras"]["A"]["em_declinio"]
    assert not r["operadoras"]["B"]["em_declinio"]
    assert set(r["parou_de_declarar"]) == {"C"}
    assert r["parou_de_declarar"]["C"]["ultimo_mes_declarado"] == "2026-01" and r["parou_de_declarar"]["C"]["meses_sem_declarar"] == 7


def test_classes_sem_declaracao():
    assert classificar_sem_declaracao(5000, True) == "com_usuarios_apnic"
    assert classificar_sem_declaracao(99, True) == "sem_usuarios"
    assert classificar_sem_declaracao(None, True) == "sem_usuarios"
    assert classificar_sem_declaracao(None, False) == "nao_comparavel"


def test_sem_declaracao_usuarios_asns_do_cnpj_e_grupo():
    scms = [
        {"cnpj": "1", "razao_social": "Um", "uf": "MG", "asns": [10, 11], "data_outorga": "05/01/2021"},
        {"cnpj": "1", "razao_social": "Um", "uf": "MG", "asns": [10, 11], "data_outorga": "03/04/2019"},   # duas outorgas, uma linha
        {"cnpj": "2", "razao_social": "Dois", "uf": "MG", "asns": [], "data_outorga": "01/02/2020"},
        {"cnpj": "3", "razao_social": "Declara", "uf": "SP", "asns": [30]},
        {"cnpj": "4", "razao_social": "Filial", "uf": "SP", "asns": [40]},
    ]
    grupos = [{"grupo_id": "g1", "cnpjs": ["3", "4"]}]
    r = calcular_sem_declaracao("2026-08", scms, {"3"}, {10: 150, 11: 50, 40: 7}, grupos)
    assert set(r["itens"]) == {"1", "2", "4"}
    um = r["itens"]["1"]
    assert um["n_outorgas"] == 2 and um["usuarios_apnic"] == 200 and um["classe"] == "com_usuarios_apnic" and um["desde"] == "2019-04"
    assert r["itens"]["2"]["classe"] == "nao_comparavel" and r["itens"]["2"]["usuarios_apnic"] is None
    assert r["itens"]["4"]["grupo_declara"] is True and r["itens"]["4"]["classe"] == "sem_usuarios"
    assert r["por_uf"]["MG"] == {"cnpjs_sem_declaracao": 2, "com_usuarios_apnic": 1, "sem_usuarios": 0, "nao_comparavel": 1, "usuarios_apnic": 200,
                                  "grupo_declarou": 0, "credenciadas_rede_virtual": 0}


def _gz(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(obj, f)


def test_publicar_grava_os_dois_artefatos(tmp_path):
    d = "2026-10-11"
    cache = tmp_path / "normalized" / "sici_cache" / "months"
    _gz(cache / "2026-08.json.gz", {"mes": "2026-08", "cnpjs": _mes(A=(100, {"3550308": 100}))})
    _gz(cache / "2026-07.json.gz", {"mes": "2026-07", "cnpjs": _mes(A=(90, {"3550308": 90}))})
    pub = tmp_path / "published" / d
    _gz(pub / "sici.json.gz", {"mes_referencia": "2026-08", "serie_por_cnpj": {"A": [["2026-07", 90, 0, 90], ["2026-08", 100, 0, 100]]}})
    _gz(pub / "scm.json.gz", {"scms": [{"cnpj": "Z", "razao_social": "Z", "uf": "MG", "asns": [9]}]})
    (pub / "asns").mkdir()
    (pub / "asns" / "index.json").write_text(json.dumps([{"asn": 9, "is_br": True, "apnic_users": 321}]))
    assert publicar_sici_indicadores(tmp_path, d, _Log()) == {"operadoras": 1, "municipios": 1, "sem_declaracao": 1}
    serie = json.loads(gzip.open(pub / "sici_serie_municipio.json.gz").read())
    assert serie["meses"][-1] == "2026-08" and len(serie["meses"]) == 13 and serie["municipios"]["3550308"]["acessos"][-2:] == [90, 100]
    ind = json.loads(gzip.open(pub / "sici_indicadores.json.gz").read())
    om = json.loads(gzip.open(pub / "sem_declaracao_sici.json.gz").read())
    assert ind["mes_anterior"] == "2026-07" and ind["mes_ano_anterior"] is None and ind["operadoras"]["A"]["var_mm"]["abs"] == 10
    assert om["itens"]["Z"]["usuarios_apnic"] == 321 and om["itens"]["Z"]["classe"] == "com_usuarios_apnic"


def test_publicar_sem_o_mes_no_cache_nao_grava(tmp_path):
    pub = tmp_path / "published" / "2026-10-11"
    _gz(pub / "sici.json.gz", {"mes_referencia": "2026-08", "serie_por_cnpj": {}})
    _gz(pub / "scm.json.gz", {"scms": []})
    assert publicar_sici_indicadores(tmp_path, "2026-10-11", _Log()) == {}
    assert not (pub / "sici_indicadores.json.gz").exists()


def test_serie_municipios_tem_participacao_por_mes_e_ponto_vazio_sem_o_mes():
    meses = ["2026-06", "2026-07", "2026-08"]
    cache = {"2026-07": _mes(A=(60, {"3550308": 60}), B=(40, {"3550308": 40})),
             "2026-08": _mes(A=(70, {"3550308": 70}), B=(30, {"3550308": 30}), C=(5, {"3550308": 5}))}
    r = serie_municipios("2026-08", meses, cache.get)
    m = r["3550308"]
    assert m["acessos"] == [None, 100, 105]                                           # mês ausente do cache = sem ponto, não zero
    assert m["hhi"][0] is None and m["hhi"][1] == round(60 ** 2 + 40 ** 2)
    a = next(x for x in m["lideres"] if x["cnpj"] == "A")
    assert a["share"] == [None, 60.0, round(100 * 70 / 105, 2)] and a["empresa"] == "EMPA"
    assert [x["cnpj"] for x in m["lideres"]][:2] == ["A", "B"]                         # ordem pelo mês de referência
    assert serie_municipios("2026-09", meses, cache.get) == {}                         # sem o mês de referência, nada


def test_serie_limita_os_lideres():
    ops = {f"X{i}": (100 - i, {"3550308": 100 - i}) for i in range(7)}
    r = serie_municipios("2026-08", ["2026-08"], {"2026-08": _mes(**ops)}.get)
    assert len(r["3550308"]["lideres"]) == 4


def _mun(uf, **ops):
    return {"uf": uf, "nome": "M", "operadores": [{"cnpj": c, "empresa": f"E{c}", "acessos": a} for c, a in ops.items()]}


def test_hhi_por_grupo_junta_cnpjs_do_mesmo_grupo_e_muda_de_faixa():
    muns = {"1": _mun("SP", A=40, B=40, C=20), "2": _mun("SP", A=50, D=50)}
    grupos = [{"grupo_id": "g1", "cnpjs": ["A", "B"], "classificacao": "total"}, {"grupo_id": "gi", "cnpjs": ["D"], "classificacao": "individual"}]
    r = calcular_mercado_grupos(muns, grupos)
    m1, m2 = r["municipios"]["1"], r["municipios"]["2"]
    assert m1["hhi_cnpj"] == 3600 and m1["hhi_grupo"] == 6800                         # 40²+40²+20² × 1 ; (80)²+20²
    assert (m1["faixa_cnpj"], m1["faixa_grupo"]) == ("concentrado", "concentrado")
    assert m1["n_cnpjs"] == 3 and m1["n_grupos"] == 2 and m1["lider_grupo"]["id"] == "g1" and m1["lider_grupo"]["e_grupo"]
    assert m2["hhi_grupo"] == m2["hhi_cnpj"] == 5000                                  # individual não funde nada
    assert r["resumo"]["grupos_com_mais_de_um_cnpj_no_mercado"] == 1
    assert r["ufs"]["SP"]["hhi_grupo"] >= r["ufs"]["SP"]["hhi_cnpj"]


def test_mudanca_de_faixa_e_contada():
    muns = {"1": _mun("SP", A=20, B=20, C=20, D=20, E=20)}            # HHI 2000 por CNPJ: moderado
    r = calcular_mercado_grupos(muns, [{"grupo_id": "g", "cnpjs": ["A", "B", "C"], "classificacao": "total"}])   # grupo: 60² + 20² + 20² = 4400: concentrado
    assert r["resumo"]["mudam_de_faixa"] == 1 and r["resumo"]["transicoes"] == {"moderado → concentrado": 1}
    assert [faixa_hhi(x) for x in (1499, 1500, 2499, 2500, None)] == ["competitivo", "moderado", "moderado", "concentrado", None]


def test_sobreposicao_conta_municipios_em_comum_e_marca_mesmo_grupo():
    muns = {"1": _mun("SP", A=10, B=5), "2": _mun("SP", A=10, B=5, C=1), "3": _mun("RJ", A=10, C=1)}
    r = calcular_mercado_grupos(muns, [{"grupo_id": "g", "cnpjs": ["A", "B"], "classificacao": "parcial"}])
    a = r["sobreposicao"]["A"]
    assert [x["cnpj"] for x in a] == ["B", "C"] and a[0]["municipios_em_comum"] == 2 and a[0]["mesmo_grupo"] is True
    assert a[0]["acessos_dele_nos_comuns"] == 10 and a[0]["acessos_dela_nos_comuns"] == 20 and a[1]["mesmo_grupo"] is False
