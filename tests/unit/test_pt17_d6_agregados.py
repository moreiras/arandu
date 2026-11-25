# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PT-17 (D6, SEG-E11): agregados por UF e município sem supressão: n, peso do maior integrante e avisos (prontidão, ROV, HHI)."""
from core.avisos_agregado import MIN_CASOS, PESO_AVISO, avisos, peso_top1
from core.prontidao_agregado import agregar
from products.rede_territorio.build import calcular_rov
from products.seguranca import build as seg
from products.sici_indicadores.build import _hhi_e_lider, calcular_mercado_grupos


def test_regra_dos_avisos_menos_de_5_casos_ou_integrante_com_30_por_cento_ou_mais():
    assert (MIN_CASOS, PESO_AVISO) == (5, 0.30)
    assert avisos(4, 0.1) == ["poucos_casos"] and avisos(5, 0.1) == []
    assert avisos(10, 0.30) == ["maior_integrante"] and avisos(10, 0.299) == []
    assert avisos(2, 0.9) == ["poucos_casos", "maior_integrante"]
    assert avisos(3, 0.9, com_peso=False) == ["poucos_casos"]
    assert peso_top1([50, 30, 20]) == 0.5 and peso_top1([0, 0]) is None and peso_top1([]) is None


def _asn(usuarios, total=50.0, rov=None):
    pilares = {"filtragem": {"componentes": {"rov": {"valor": rov}}}} if rov is not None else {}
    return {"usuarios": usuarios, "total": total, "classe": "em_progresso", "pilares": pilares}


def test_prontidao_agregada_traz_n_peso_e_aviso_e_nenhum_recorte_some():
    asns = {"1": _asn(1_841_945, rov=96.6), "2": _asn(10), "3": _asn(10), "4": _asn(10), "5": _asn(10), "6": _asn(10),      # SC: um ASN domina
            "11": _asn(100, rov=1.0), "12": _asn(100), "13": _asn(100),                                                  # AP: 3 ASNs
            "21": _asn(100), "22": _asn(100), "23": _asn(100), "24": _asn(100), "25": _asn(100), "26": _asn(100)}         # SP: 6 iguais
    grupo = {**{a: "SC" for a in ("1", "2", "3", "4", "5", "6")}, **{a: "AP" for a in ("11", "12", "13")}, **{a: "SP" for a in ("21", "22", "23", "24", "25", "26")}}
    r = agregar(asns, grupo)
    assert set(r) == {"SC", "AP", "SP"}                                                  # nada suprimido
    assert r["SC"]["n_asns_com_dado"] == 6 and r["SC"]["peso_top1"] > 0.99 and r["SC"]["avisos"] == ["maior_integrante"]
    assert r["AP"]["n_asns_com_dado"] == 3 and r["AP"]["avisos"] == ["poucos_casos", "maior_integrante"]       # 3 casos e cada um com 1/3 do peso
    assert r["SP"]["avisos"] == [] and r["SP"]["peso_top1"] == round(1 / 6, 3)
    rov = r["SC"]["medicoes"]["rov"]
    assert rov["n_asns_com_dado"] == 1 and rov["peso_top1"] == 1.0 and rov["avisos"] == ["poucos_casos", "maior_integrante"]      # ROV de SC: um ASN só


def test_rov_por_uf_traz_n_peso_e_avisos():
    idx = {i: {"is_br": True, "apnic_users": u} for i, u in {1: 1000, 2: 10, 3: 10, 4: 10, 5: 10, 6: 10, 7: 50}.items()}
    segs = {str(i): {"uf": "SC" if i <= 6 else "AP", "rov": {"validates_pct": 50.0, "amostras": 500}} for i in idx}
    r = calcular_rov(idx, segs)
    sc, ap = r["ufs"]["SC"], r["ufs"]["AP"]
    assert sc["n_asns_com_dado"] == 6 and sc["peso_top1"] == round(1000 / 1050, 3) and sc["avisos"] == ["maior_integrante"]
    assert ap["n_asns_com_dado"] == 1 and ap["peso_top1"] == 1.0 and "poucos_casos" in ap["avisos"]
    assert r["brasil"]["n_asns_com_dado"] == 7 and r["brasil"]["peso_top1"] == round(1000 / 1100, 3)


def test_rov_de_seguranca_traz_n_e_peso_das_amostras():
    a = seg._agregar([(10.0, 100), (20.0, 100), (30.0, 800)])
    assert a["asns"] == a["n_asns_com_dado"] == 3 and a["peso_top1"] == 0.8 and a["avisos"] == ["poucos_casos", "maior_integrante"]
    assert seg._agregar([])["avisos"] == ["poucos_casos"] and seg._agregar([])["n_asns_com_dado"] == 0


def test_hhi_mostra_acessos_e_n_e_avisa_so_com_menos_de_5_operadoras():
    h = _hhi_e_lider({"a": 900, "b": 100}, {"a": "A", "b": "B"})
    assert h["acessos"] == 1000 and h["n_operadoras"] == 2 and h["lider"]["share"] == 90.0 and h["avisos"] == ["poucos_casos"]
    seis = _hhi_e_lider({str(i): 100 for i in range(6)} | {"x": 5000}, {})
    assert seis["avisos"] == [] and seis["lider"]["share"] > 30          # líder com mais de 30% não gera aviso no HHI: a parcela dele é parte da medida e fica à vista


def test_mercado_grupos_traz_acessos_n_e_avisos_por_municipio_e_uf():
    muns = {"1": {"uf": "SC", "nome": "A", "operadores": [{"cnpj": "11111111000101", "empresa": "A", "acessos": 100}, {"cnpj": "22222222000102", "empresa": "B", "acessos": 50}]}}
    r = calcular_mercado_grupos(muns, [])
    m = r["municipios"]["1"]
    assert m["acessos"] == 150 and m["n_cnpjs"] == 2 and m["avisos_cnpj"] == ["poucos_casos"] and m["avisos_grupo"] == ["poucos_casos"]
    u = r["ufs"]["SC"]
    assert u["acessos"] == 150 and u["n_cnpjs"] == 2 and u["lider_grupo_share"] == round(100 * 100 / 150, 2) and u["avisos_cnpj"] == ["poucos_casos"]


def _classe(classe, com_rov):
    pilares = {"filtragem": {"componentes": {"rov": {"valor": 50.0}} if com_rov else {"sem_bogon": {"valor": 100.0}}}}
    return {"usuarios": 100, "total": 80.0, "classe": classe, "pilares": pilares}


def test_classes_separadas_por_rov_medido_somam_a_distribuicao_por_classe():
    """SEG-E5: "pronto" sem ROV medido não é o mesmo que "pronto" com ROV medido; as duas linhas somam as classes do recorte."""
    asns = {"1": _classe("pronto", True), "2": _classe("pronto", False), "3": _classe("pronto", False), "4": _classe("atrasado", False), "5": _classe("em_progresso", True)}
    r = agregar(asns, {a: "BR" for a in asns})["BR"]
    assert r["classes_com_rov"] == {"pronto": 1, "em_progresso": 1, "atrasado": 0, "sem_dados": 0}
    assert r["classes_sem_rov"] == {"pronto": 2, "em_progresso": 0, "atrasado": 1, "sem_dados": 0}
    soma = {c: r["classes_com_rov"][c] + r["classes_sem_rov"][c] for c in r["classes"]}
    assert soma == r["classes"]
