# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Aba Relações do grupo: ligações entre empresas com a contagem de sócios, sem nome nem CPF de pessoa física."""
import json

from api.services.grupo_relacoes import relacoes_do_grupo

G = {"grupo_id": "grp_x", "classificacao": "parcial", "cnpjs": [{"cnpj": "A"}, {"cnpj": "B"}, {"cnpj": "C"}]}
SOCIOS = {"receita_dump_reference": "2026-09", "by_cnpj": {
    "A": {"mesmo_grupo": [{"cnpj": "B", "tipo_relacao": "quadro_identico"}],
          "relacionadas_parcial": [{"cnpj": "C", "tipo_relacao": "socios_em_comum", "socios_em_comum": 3, "nomes_em_comum": ["FULANO DE TAL", "BELTRANO"]},
                                   {"cnpj": "X", "tipo_relacao": "socios_em_comum", "socios_em_comum": 1, "nomes_em_comum": ["CICLANO"]}],
          "holdings_externas": [{"cnpj_basico": "11111111", "razao_social": "HOLDING SA", "situacao_cadastral": "ATIVA", "natureza_juridica": "S.A.", "logradouro": "RUA X", "capital_social": 10}]},
    "B": {"mesmo_grupo": [{"cnpj": "A", "tipo_relacao": "quadro_identico"}], "relacionadas_parcial": [{"cnpj": "C", "tipo_relacao": "controle_parcial_exercido", "total_socios_da_controlada": 2}]},
    "C": {"mesmo_grupo": [], "relacionadas_parcial": [{"cnpj": "A", "tipo_relacao": "socios_em_comum", "socios_em_comum": 3, "nomes_em_comum": ["FULANO DE TAL"]},
                                                        {"cnpj": "B", "tipo_relacao": "controle_parcial_recebido", "total_socios_da_controlada": 2}]}}}


def _r():
    return relacoes_do_grupo(G, SOCIOS, lambda c: {"A": "Alfa", "B": "Beta", "C": "Gama", "X": "Xis"}.get(c, c))


def test_uma_linha_por_ligacao_com_a_direcao_do_controle():
    lig = _r()["ligacoes"]
    assert [(x["tipo"], x["de"], x["para"], x["socios"]) for x in lig] == [("quadro_identico", "A", "B", None), ("controle_parcial", "B", "C", 2), ("socios_em_comum", "A", "C", 3)]


def test_ligacao_com_empresa_de_fora_vai_para_a_lista_de_fora_e_holding_so_com_dado_de_pj():
    r = _r()
    assert r["fora_do_grupo"]["total"] == 1 and r["fora_do_grupo"]["itens"][0]["empresa"] == "Xis" and r["fora_do_grupo"]["itens"][0]["liga_a"] == ["A"]
    assert r["controladoras_externas"] == [{"cnpj_basico": "11111111", "razao_social": "HOLDING SA", "situacao_cadastral": "ATIVA", "natureza_juridica": "S.A.", "controla": ["A"]}]


def test_nenhum_nome_de_socio_pessoa_fisica_na_resposta():
    corpo = json.dumps(_r(), ensure_ascii=False)
    for proibido in ("FULANO", "BELTRANO", "CICLANO", "nomes_em_comum", "logradouro", "capital_social"):
        assert proibido not in corpo, proibido


def test_sem_socios_publicados_nao_ha_bloco():
    assert relacoes_do_grupo(G, None, lambda c: c) is None


def test_forca_da_ligacao_e_classe_de_qualificacao_sem_nome():
    socios = {"by_cnpj": {
        "A": {"mesmo_grupo": [], "relacionadas_parcial": [
            {"cnpj": "B", "tipo_relacao": "socios_em_comum", "socios_em_comum": 1, "classes_qualificacao": ["socio"], "qualificacoes_em_comum": ["22"]},
            {"cnpj": "C", "tipo_relacao": "socios_em_comum", "socios_em_comum": 2, "classes_qualificacao": ["socio", "socio_administrador"], "qualificacoes_em_comum": ["22", "49"]}]},
        "B": {"mesmo_grupo": [], "relacionadas_parcial": [{"cnpj": "A", "tipo_relacao": "socios_em_comum", "socios_em_comum": 1, "classes_qualificacao": ["socio"]}]},
        "C": {"mesmo_grupo": [], "relacionadas_parcial": [{"cnpj": "A", "tipo_relacao": "socios_em_comum", "socios_em_comum": 2}]}}}
    r = relacoes_do_grupo(G, socios, lambda c: c)
    por_par = {(x["de"], x["para"]): x for x in r["ligacoes"]}
    assert por_par[("A", "B")]["forca"] == "fraca" and por_par[("A", "B")]["classes_qualificacao"] == ["socio"]
    assert por_par[("A", "C")]["forca"] == "forte" and por_par[("A", "C")]["classes_qualificacao"] == ["socio", "socio_administrador"]
    assert r["resumo"] == {"ligacoes": 2, "fortes": 1, "fracas": 1} and "Administrador" in r["regra_ligacao"]
    assert "qualificacoes_em_comum" not in json.dumps(r)


def test_quadro_identico_e_participacao_de_pj_sao_ligacoes_fortes():
    lig = _r()["ligacoes"]
    assert {x["tipo"]: x["forca"] for x in lig if x["tipo"] != "socios_em_comum"} == {"quadro_identico": "forte", "controle_parcial": "forte"}
