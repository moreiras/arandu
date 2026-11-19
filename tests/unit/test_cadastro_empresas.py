# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cadastro das empresas de telecom: o CNPJ da Receita cruzado com o SICI, por operadora e por mercado."""
from core import receita_cnpj as rc
from products.cadastro_empresas import build as b

POR_NOME = {("SP", "SAO PAULO"): "3550308", ("RJ", "RIO DE JANEIRO"): "3304557", ("MG", "BELO HORIZONTE"): "3106200"}
NOMES = {"3550308": ("São Paulo", "SP"), "3304557": ("Rio de Janeiro", "RJ"), "3106200": ("Belo Horizonte", "MG")}


def est(c, m, s, d, uf, mu, p="6110803", x=(), ds=None, n=None):
    e = {"c": c, "m": m, "s": s, "d": d, "ds": ds, "u": uf, "mu": mu, "p": p, "x": list(x)}
    if n:
        e["n"] = n
    return e


RFB = {
    "dump_reference": "2026-10",
    "municipios_rfb": {"7107": "SÃO PAULO", "6001": "RIO DE JANEIRO", "4123": "BELO HORIZONTE", "9999": "LUGAR QUE NAO EXISTE"},
    "cnaes": {"6110803": "Serviços de comunicação multimídia - SCM"}, "naturezas": {"2062": "Sociedade Empresária Limitada"},
    "empresa": {"11111111": {"nat": "2062", "capital": 1000000.0, "porte": "05", "razao": "FIBRA UM LTDA"}, "22222222": {"nat": "2062", "capital": 5.0, "porte": "03", "razao": "DOIS"},
                "33333333": {"nat": "2135", "capital": 1.0, "porte": "01"}},
    "simples": {"22222222": {"simples": True, "mei": False}, "33333333": {"simples": True, "mei": True}},
    "estabelecimentos": {
        "11111111": [est("11111111000191", 1, "02", "2010-01-01", "SP", "7107", n="FIBRA UM"), est("11111111000272", 2, "02", "2012-05-05", "RJ", "6001", p="4321500"),
                     est("11111111000353", 2, "08", "2013-01-01", "MG", "4123", ds="2020-02-02"), est("11111111000434", 2, "02", "2014-01-01", "SP", "9999")],
        "22222222": [est("22222222000102", 1, "02", "2018-03-01", "MG", "4123", p="6190699")],
        "33333333": [est("33333333000183", 1, "08", "2015-01-01", "SP", "7107", ds="2019-06-01")],       # empresário individual, baixada, fora das operadoras
    },
}
FIXO = {"mes_referencia": "2026-09", "municipios": {
    "3550308": {"operadores": [{"cnpj": "11111111000191", "acessos": 600}, {"cnpj": "99999999000100", "acessos": 5}]},
    "3304557": {"operadores": [{"cnpj": "11111111000191", "acessos": 40}]},
    "3106200": {"operadores": [{"cnpj": "22222222000102", "acessos": 7}, {"cnpj": "11111111000191", "acessos": 1}]}}}
MOVEL = {"municipios": {"3550308": {"operadores": [{"cnpj": "11111111000191", "acessos": 1000}]}}}


def rodar(operadoras={"11111111", "22222222"}, fixo=FIXO, movel=MOVEL):
    return b.calcular(RFB, fixo, movel, operadoras, POR_NOME, NOMES, "2026-11-07")


def test_operadora_tem_matriz_estabelecimentos_e_porte():
    _, docs = rodar()
    d = docs["11111111"]
    assert d["razao_social"] == "FIBRA UM LTDA" and d["nome_fantasia"] == "FIBRA UM" and d["porte"] == "demais"
    assert d["matriz"] == {"cnpj": "11111111000191", "uf": "SP", "ibge": "3550308", "municipio": "São Paulo", "situacao": "ativa", "inicio": "2010-01-01", "cnae": "6110803",
                           "cnae_descricao": "Serviços de comunicação multimídia - SCM"}
    assert d["estabelecimentos"] == {"total": 4, "ativos": 3, "baixados": 1, "filiais_ativas": 2}
    assert d["natureza_juridica"] == {"codigo": "2062", "descricao": "Sociedade Empresária Limitada"} and d["simples"] is False


def test_presenca_cruza_estabelecimento_ativo_com_acessos_do_sici():
    _, docs = rodar()
    p = {x["ibge"]: x for x in docs["11111111"]["presenca"]}
    assert p["3550308"]["tem_matriz"] and p["3550308"]["acessos_fixo"] == 600 and p["3550308"]["acessos_movel"] == 1000      # fixo e móvel somam por município
    assert p["3304557"]["ativos"] == 1 and p["3304557"]["acessos_fixo"] == 40 and not p["3304557"]["tem_matriz"]
    assert p["3106200"]["estabelecimentos"] == 1 and p["3106200"]["ativos"] == 0 and p["3106200"]["acessos_fixo"] == 1     # filial baixada, mas com acesso declarado
    assert docs["11111111"]["resumo_presenca"] == {"municipios_com_estabelecimento_ativo": 2, "municipios_com_acessos": 3, "com_ambos": 2, "so_acessos": 1, "so_estabelecimento": 0}


def test_estabelecimento_sem_ibge_fica_fora_do_mapa_e_e_contado():
    geral, docs = rodar()
    assert geral["resumo"]["estabelecimentos_sem_ibge"] == 1                              # "LUGAR QUE NAO EXISTE"
    assert all(x["ibge"] != "9999" for x in docs["11111111"]["presenca"])


def test_so_operadoras_ganham_documento_mas_o_mercado_conta_todas_de_telecom():
    geral, docs = rodar()
    assert set(docs) == {"11111111", "22222222"} and geral["resumo"]["operadoras_com_cadastro"] == 2
    anos = {e["ano"]: e for e in geral["mercado"]["entradas_por_ano"]}
    assert anos[2010]["por_uf"] == {"SP": 1} and anos[2015]["total"] == 1 and anos[2018]["por_uf"] == {"MG": 1}     # inclui 33333333, que não é operadora
    assert [x["ano"] for x in geral["mercado"]["baixas_por_ano"]] == [2019] and geral["mercado"]["ativas_por_uf"] == {"MG": 1, "SP": 1}
    assert geral["mercado"]["ativas_por_porte"] == {"demais": 1, "pequeno": 1}


def test_empresario_individual_nao_expoe_nome():
    _, docs = rodar({"33333333"})
    d = docs["33333333"]
    assert d["razao_social"] is None and d["nome_fantasia"] is None and d["mei"] is True
    assert "FULANO" not in str(d)


def test_mercado_so_conta_matriz_com_cnae_61_principal():
    rfb = {**RFB, "estabelecimentos": {"11111111": [est("11111111000191", 1, "02", "2001-01-01", "SP", "7107", p="4711301", x=["6110803"])]}}
    geral, _ = b.calcular(rfb, None, None, {"11111111"}, POR_NOME, NOMES, "2026-11-07")
    assert geral["mercado"]["entradas_por_ano"] == [] and geral["mercado"]["ativas_por_uf"] == {}


def test_sem_sici_a_presenca_so_tem_estabelecimentos():
    _, docs = rodar({"11111111"}, None, None)
    assert all(x["acessos_fixo"] == 0 and x["acessos_movel"] == 0 for x in docs["11111111"]["presenca"])
    assert docs["11111111"]["resumo_presenca"]["municipios_com_acessos"] == 0


def test_limites_nao_prometem_o_que_o_cruzamento_nao_prova():
    assert "não prova" in b.LIMITES and "e-mail" in b.LIMITES and rc.NATUREZA_EI == "2135"
