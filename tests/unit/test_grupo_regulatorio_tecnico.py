# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Abas Regulatório e Técnico do grupo: soma sem dupla contagem, ordem alfabética (sem ranking por multa) e limites."""
from api.services.grupo_regulatorio import regulatorio_do_grupo
from api.services.grupo_tecnico import LIMITE_ASES, tecnico_do_grupo

G = {"grupo_id": "grp_x", "cnpjs": [
    {"cnpj": "11111111000101", "has_scm": True, "has_smp": False, "has_stfc": False, "has_seac": True},
    {"cnpj": "11111111000202", "has_scm": True},                      # filial: mesma raiz da primeira
    {"cnpj": "22222222000103", "has_scm": False, "has_smp": True}]}
MULTAS = {"fonte": "Anatel", "limites": "x", "brasil": {"empresas": 2, "multas": 9, "saldo": 1.0}, "empresas": [
    {"raiz": "11111111", "entidade": "ZETA", "cnpj_matriz": "11111111000101", "anos": [2020], "grupo": "SCM", "uf": "SP", "multas": 5, "original": 100.0, "pago": 10.0, "saldo": 90.0, "situacoes": {}},
    {"raiz": "22222222", "entidade": "ALFA", "cnpj_matriz": "22222222000103", "anos": [2021], "grupo": "SMP", "uf": "RJ", "multas": 50, "original": 1000.0, "pago": 0.0, "saldo": 1000.0, "situacoes": {}}]}


def _reg(**kw):
    return regulatorio_do_grupo(G, kw.get("multas", MULTAS), kw.get("rqual"), kw.get("recl"), kw.get("cons"))


def test_multas_somam_por_raiz_e_saem_em_ordem_alfabetica_e_nao_por_valor():
    r = _reg()
    assert r["empresas"] == 2 and r["multas"]["empresas_com_registro"] == 2 and r["multas"]["multas"] == 55 and r["multas"]["saldo"] == 1090.0
    assert [x["empresa"] for x in r["multas"]["por_empresa"]] == ["ALFA", "ZETA"]            
    assert r["outorgas"] == {"SCM": 2, "SMP": 1, "STFC": 0, "SeAC": 1}


def test_reclamacoes_nao_contam_a_mesma_marca_duas_vezes():
    recl = {"anos": [2025], "limites": "l", "marcas": [
        {"marca": "M", "ano": 2025, "servico": "SCM", "reclamacoes": 10, "raizes": ["11111111", "22222222"]},       # ligada às duas raízes do grupo: conta uma vez
        {"marca": "Outra", "ano": 2025, "servico": "SMP_Pós", "reclamacoes": 4, "raizes": ["99999999"]}]}
    r = _reg(recl=recl)["reclamacoes_anatel"]
    assert r["marcas"] == ["M"] and r["anos"] == [{"ano": 2025, "reclamacoes": 10, "por_servico": {"SCM": 10}}]


def test_consumidor_soma_marcas_unicas_e_nao_recalcula_indice():
    cons = {"janela": {"de": "a", "ate": "b"}, "limites": "l", "marcas": [
        {"marca": "B", "casamento": "curada", "raizes": ["11111111"], "janela": {"n": 100, "pct_respondidas": 99.0, "indice_solucao": 70.0, "nota_media": 3.0}},
        {"marca": "A", "casamento": "curada", "raizes": ["22222222"], "janela": {"n": 20, "pct_respondidas": 90.0, "indice_solucao": None, "nota_media": None}}]}
    c = _reg(cons=cons)["consumidor"]
    assert [m["marca"] for m in c["marcas"]] == ["A", "B"] and c["reclamacoes_finalizadas"] == 120


def test_tecnico_une_ptts_soma_prefixos_e_conta_provedor_uma_vez_por_as():
    docs = {1: {"name": "A", "apnic_users": 100, "apnic_v6_users": 50, "apnic_v6_pct_as": 50.0, "global_prefixes_v4_count": 3, "global_prefixes_v6_count": 1, "has_ipv6": True,
                "rpki_validation": {"p1": "valid", "p2": "not_found", "p3": "invalid_asn"}, "ixps_direct": ["sp", "rj"], "upstreams_global_v4": [10], "upstreams_global_v6": [10, 11], "is_multihomed_v6": True},
            2: {"name": "B", "apnic_users": 300, "apnic_v6_users": 0, "global_prefixes_v4_count": 2, "global_prefixes_v6_count": 0, "rpki_validation": {"p4": "valid"}, "ixps_direct": ["sp"], "upstreams_global_v4": [10]}}
    t = tecnico_do_grupo({"grupo_id": "g", "asns": [1, 2, 3]}, docs)
    assert t["asns_total"] == 3 and t["asns_com_dado"] == 2 and t["prefixos"] == {"v4": 5, "v6": 1}
    assert t["ipv6"]["pct_v6"] == 12.5 and t["rpki"] == {"validados": 4, "valido": 2, "invalido": 1, "sem_roa": 1, "valido_pct": 50.0}
    assert {x["asn"]: x["asns_do_grupo"] for x in t["transito"]["provedores"]} == {10: 2, 11: 1}      # AS1 usa o 10 em v4 e v6: conta uma vez
    assert [(p["ixp"], p["asns"]) for p in t["ptts"]] == [("rj", [1]), ("sp", [1, 2])] and t["transito"]["asns_multihomed"] == 1


def test_grupo_grande_mostra_so_os_maiores_e_diz_quantos_omitiu():
    docs = {a: {"name": f"AS{a}", "apnic_users": a} for a in range(1, LIMITE_ASES + 6)}
    t = tecnico_do_grupo({"grupo_id": "g", "asns": list(docs)}, docs)
    assert t["asns_detalhados"] == LIMITE_ASES and t["asns_omitidos"] == 5 and max(r["usuarios"] for r in t["por_asn"]) == LIMITE_ASES + 5
