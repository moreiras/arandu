# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — área de influência dos PTTs: percentis ponderados, atribuição ao PTT mais próximo, PIX sem coordenada, CNPJ com vários ASNs e diretos ⊆ todos."""
import json

from products.area_influencia_ptt.build import calcular, montar, participacao_por_visao, percentil, posicionar_pix

# municípios na linha do equador (1° de longitude ≈ 111,2 km): A=0°, B=1°, C=2°, D=5°; PIX de p1 em A e de p2 em 3°
CEN = {"A": (0.0, 0.0), "B": (1.0, 0.0), "C": (2.0, 0.0), "D": (5.0, 0.0)}
PIX = {"p1": [(0.0, 0.0, "coordenada")], "p2": [(0.0, 3.0, "coordenada")]}


def _mun(**ops):
    return {"operadores": [{"cnpj": c, "acessos": a, "asns": asns} for c, (a, asns) in ops.items()]}


def test_percentil_pondera_por_acessos_e_pega_o_primeiro_que_alcanca_a_fracao():
    pares = [(30.0, 2.0), (10.0, 1.0), (20.0, 1.0)]
    assert percentil(pares, 0.25) == 10.0 and percentil(pares, 0.5) == 20.0 and percentil(pares, 0.75) == 30.0 and percentil(pares, 1.0) == 30.0
    assert percentil([], 0.5) is None
    assert percentil([(5.0, 1.0), (50.0, 99.0)], 0.5) == 50.0                 # um município grande puxa o P50 (por acessos), ao contrário da mediana por operadora


def test_acessos_vao_para_o_ptt_mais_proximo_entre_os_que_a_operadora_enxerga():
    muns = {"A": _mun(X=(100, [1])), "C": _mun(X=(300, [1])), "D": _mun(Y=(50, [2]))}
    part = {"diretos": {1: {"p1", "p2"}, 2: {"p1"}}, "todos": {1: {"p1", "p2"}, 2: {"p1"}}}
    r = calcular(muns, CEN, part, PIX)["diretos"]
    assert r["ptts"]["p1"]["acessos"] == 150 and r["ptts"]["p2"]["acessos"] == 300      # C está a 1° de p2 e a 2° de p1; D só enxerga p1
    assert r["ptts"]["p1"]["municipios"] == 2 and r["ptts"]["p2"]["municipios"] == 1
    assert r["total"]["acessos"] == 450 and r["total"]["acessos_atribuidos"] == 450 and r["total"]["acessos_sem_ptt"] == 0
    assert r["municipios"]["C"][:2] == ["p2", 1]


def test_operadora_que_so_enxerga_um_ptt_longe_nao_vai_para_o_mais_proximo_da_outra():
    muns = {"C": _mun(X=(100, [1]), Y=(100, [2]))}
    part = {"diretos": {1: {"p1", "p2"}, 2: {"p1"}}, "todos": {1: {"p1", "p2"}, 2: {"p1"}}}
    r = calcular(muns, CEN, part, PIX)["diretos"]
    assert r["ptts"]["p2"]["acessos"] == 100 and r["ptts"]["p1"]["acessos"] == 100
    assert r["municipios"]["C"][0] == "p1" and r["municipios"]["C"][3] == 200 and r["municipios"]["C"][4] == 2      # empate de acessos: o código menor; dois PTTs recebem do município


def test_cnpj_com_varios_asns_une_os_ptts_e_conta_os_acessos_uma_vez():
    muns = {"A": _mun(X=(100, [1, 2])), "D": _mun(X=(70, [1, 2]))}
    part = {"diretos": {1: {"p1"}, 2: {"p2"}}, "todos": {1: {"p1"}, 2: {"p2"}}}
    r = calcular(muns, CEN, part, PIX)["todos"]
    assert r["total"]["acessos_atribuidos"] == 170 and r["total"]["cnpjs_com_varios_asns"] == 1
    assert sum(p["acessos"] for p in r["ptts"].values()) == 170                    # sem contar em dobro
    assert r["ptts"]["p1"]["acessos"] == 100 and r["ptts"]["p2"]["acessos"] == 70       # A fica com p1; D (5°) está a 2° de p2 e a 5° de p1
    assert r["ptts"]["p1"]["operadoras"] == 1 and r["ptts"]["p2"]["operadoras"] == 1       # a operadora conta nos dois PTTs, cada um com os seus acessos


def test_operadora_sem_ptt_visivel_e_municipio_sem_centroide_ficam_fora_com_a_contagem():
    muns = {"A": _mun(X=(100, [1]), Z=(40, [])), "Q": _mun(X=(10, [1]))}
    part = {"diretos": {1: {"p1"}}, "todos": {1: {"p1"}}}
    t = calcular(muns, CEN, part, PIX)["diretos"]["total"]
    assert t == {"acessos": 150, "acessos_atribuidos": 100, "acessos_sem_ptt": 40, "acessos_sem_centroide": 10, "cnpjs_com_varios_asns": 0}


def test_ptt_sem_pix_posicionado_nao_recebe_acessos():
    muns = {"A": _mun(X=(100, [1]))}
    part = {"diretos": {1: {"pz"}}, "todos": {1: {"pz"}}}
    r = calcular(muns, CEN, part, PIX)["todos"]
    assert r["ptts"] == {} and r["total"]["acessos_sem_ptt"] == 100


def test_visoes_diretos_esta_contido_em_todos_e_mudam_a_atribuicao():
    def doc(direct, prefixos):
        return {"ixp_presence": {p: {"v4": {"direct": direct.get(p, False), "origin": True, "prefixes": prefixos.get(p, [])}, "v6": {"direct": direct.get(p, False), "origin": False, "prefixes": []}} for p in ("p1", "p2", "p3")}}

    docs = [(1, doc({"p1": True}, {"p1": ["198.18.0.0/24"], "p2": ["198.18.1.0/24"]})),           # direto só no p1; prefixo visto também no p2 (levado por outro)
            (2, doc({"p3": True}, {})),                                                          # sessão sem prefixo próprio: não entra em nenhuma visão
            (3, doc({"p2": True}, {"p2": ["198.18.2.0/24"]})),
            (9, doc({"p1": True}, {"p1": ["198.18.9.0/24"]}))]                                   # fora do conjunto pedido
    part = participacao_por_visao(iter(docs), {1, 2, 3})
    assert part["diretos"] == {1: {"p1"}, 3: {"p2"}} and part["todos"] == {1: {"p1", "p2"}, 3: {"p2"}}
    assert all(part["diretos"][a] <= part["todos"][a] for a in part["diretos"])
    muns = {"C": _mun(X=(100, [1]))}
    assert calcular(muns, CEN, part, PIX)["diretos"]["municipios"]["C"][0] == "p1"      # só enxerga o p1 como direto
    assert calcular(muns, CEN, part, PIX)["todos"]["municipios"]["C"][0] == "p2"         # com o p2 na visão, é o mais próximo


def test_prefixo_so_no_v6_conta_e_direct_so_no_v6_tambem():
    doc = {"ixp_presence": {"p1": {"v4": {"direct": False, "prefixes": []}, "v6": {"direct": True, "prefixes": ["2001:db8::/32"]}}}}
    assert participacao_por_visao(iter([(1, doc)]), {1}) == {"diretos": {1: {"p1"}}, "todos": {1: {"p1"}}}


def test_faixas_por_municipio_seguem_o_p50_e_o_p80_do_ptt():
    cen = {str(i): (float(i), 0.0) for i in range(1, 11)}
    muns = {str(i): _mun(X=(10, [1])) for i in range(1, 11)}          # 10 municípios a 1°..10° do PIX em 0°, 10 acessos cada
    part = {"diretos": {1: {"p"}}, "todos": {1: {"p"}}}
    r = calcular(muns, cen, part, {"p": [(0.0, 0.0, "coordenada")]})["todos"]["ptts"]["p"]
    assert r["acessos"] == 100 and r["municipios"] == 10
    assert abs(r["p50_km"] - 5 * 111.2) < 1 and abs(r["p80_km"] - 8 * 111.2) < 1 and abs(r["p90_km"] - 9 * 111.2) < 1
    assert r["faixas"] == {"ate_p50": {"municipios": 5, "acessos": 50}, "p50_a_p80": {"municipios": 3, "acessos": 30}, "alem_p80": {"municipios": 2, "acessos": 20}}
    assert [r["municipios_faixa"][str(i)][1] for i in range(1, 11)] == [1, 1, 1, 1, 1, 2, 2, 2, 3, 3]


def test_mediana_por_operadora_conta_cada_operadora_uma_vez():
    cen = {"1": (1.0, 0.0), "2": (2.0, 0.0), "9": (9.0, 0.0)}
    muns = {"1": _mun(P=(10, [1]), Q=(10, [2])), "2": _mun(R=(10, [3])), "9": _mun(G=(1000, [4]))}      # G é uma operadora grande e distante
    part = {"diretos": {a: {"p"} for a in (1, 2, 3, 4)}, "todos": {a: {"p"} for a in (1, 2, 3, 4)}}
    r = calcular(muns, cen, part, {"p": [(0.0, 0.0, "coordenada")]})["todos"]["ptts"]["p"]
    assert abs(r["p50_km"] - 9 * 111.2) < 1                                          # por acessos, G domina
    assert abs(r["mediana_operadora_km"] - 1 * 111.2) < 1 and r["operadoras"] == 4      # por operadora, a metade está a até 1°


def test_pix_sem_coordenada_vai_para_o_municipio_do_endereco_e_depois_para_a_sede():
    ptts = {"p1": {"name": "Cidade A", "uf": "AA"}, "p2": {"name": "Cidade B", "uf": "AA"}, "p3": {"name": "Cidade C", "uf": "AA"}, "p4": {"name": "Cidade Z", "uf": "AA"}}
    por_nome = {("CIDADE A", "AA"): "A", ("CIDADE B", "AA"): "B", ("CIDADE C", "AA"): "C"}
    cadastro = {"p1": [{"name": "a", "address": "", "lat": 1.5, "lon": 2.5}],
                "p2": [{"name": "b", "address": "Rua X, 10 - Centro, Cidade C - AA"}],                  # endereço reconhecível: centroide de C
                "p3": [{"name": "c", "address": "Rua Y, 5"}, {"name": "c2", "address": "Rua W - Cidade Desconhecida - AA"}]}   # sem endereço reconhecível: sede (C), duas vezes
    pix = posicionar_pix(cadastro, ptts, CEN, por_nome)
    assert pix["p1"] == [(1.5, 2.5, "coordenada")]
    assert pix["p2"] == [(0.0, 2.0, "endereco")]
    assert pix["p3"] == [(0.0, 2.0, "sede"), (0.0, 2.0, "sede")]
    assert "p4" not in pix                                                                           # sem PIX no cadastro e sem sede com centroide: fica fora


def test_ptt_sem_pix_no_cadastro_usa_a_sede():
    pix = posicionar_pix({}, {"p1": {"name": "Cidade B", "uf": "AA"}}, CEN, {("CIDADE B", "AA"): "B"})
    assert pix == {"p1": [(0.0, 1.0, "sede")]}


def test_documento_publicado_so_tem_contagens_e_marca_o_pix_aproximado():
    sici = {"mes_referencia": "2026-08", "municipios": {"A": {"nome": "Cidade A", "uf": "AA", **_mun(**{"12345678000199": (100, [1])})},
                                                       "C": {"nome": "Cidade C", "uf": "AA", **_mun(**{"12345678000199": (50, [1])})}}}
    idx = [{"code": "p1", "name": "Cidade A", "uf": "AA"}, {"code": "p2", "name": "Cidade C", "uf": "AA"}]
    cadastro = {"p1": [{"name": "PIX Fulano Sicrano", "address": "", "lat": 0.0, "lon": 0.0}], "p2": [{"name": "[PIX X]", "address": "Rua A, 1"}]}
    part = {"diretos": {1: {"p1", "p2"}}, "todos": {1: {"p1", "p2"}}}
    doc = montar("2026-11-22", sici, idx, cadastro, CEN, {}, part)
    texto = json.dumps(doc, ensure_ascii=False)
    assert "12345678000199" not in texto and "Fulano" not in texto and "[PIX X]" not in texto and '"cnpj"' not in texto           # nem CNPJ nem nome de operadora ou de PIX
    assert doc["ptts_com_pix_aproximado"] == ["p2"] and doc["ptts"]["p1"]["pix"]["aproximado"] is False
    assert doc["ptts"]["p2"]["pix"]["sede"] == 1 and doc["natureza"] == "inferido" and doc["fontes"]["sici"] == "2026-08"
    assert doc["ptts"]["p1"]["visoes"]["todos"]["acessos"] == 100 and doc["ptts"]["p2"]["visoes"]["todos"]["acessos"] == 50
    assert doc["municipios_nomes"] == {"A": "Cidade A/AA", "C": "Cidade C/AA"}


def test_alcance_nao_disputa_e_contem_a_influencia_provavel_do_mesmo_ptt():
    muns = {"A": _mun(X=(100, [1])), "C": _mun(X=(300, [1])), "D": _mun(Y=(50, [2]))}
    part = {"diretos": {1: {"p1", "p2"}, 2: {"p1"}}, "todos": {1: {"p1", "p2"}, 2: {"p1"}}}
    r = calcular(muns, CEN, part, PIX)
    for base, alc in (("diretos", "alcance_diretos"), ("todos", "alcance_todos")):
        for ptt, prov in r[base]["ptts"].items():
            a = r[alc]["ptts"][ptt]
            assert set(prov["municipios_faixa"]) <= set(a["municipios_faixa"]) and a["acessos"] >= prov["acessos"] and a["operadoras"] >= prov["operadoras"]
            assert all(a["municipios_faixa"][i][0] >= x[0] for i, x in prov["municipios_faixa"].items())
    p1, p2 = r["alcance_diretos"]["ptts"]["p1"], r["alcance_diretos"]["ptts"]["p2"]
    assert (p1["municipios"], p1["acessos"], p1["operadoras"]) == (3, 450, 2)          # X em A, C e D; Y em D
    assert (p2["municipios"], p2["acessos"], p2["operadoras"]) == (2, 400, 1)          # só X, em A e C: Y não enxerga o p2
    assert "municipios" not in r["alcance_diretos"] and "total" not in r["alcance_diretos"]       # sem índice nacional nem totais


def test_municipio_aparece_no_alcance_de_dois_ptts_e_cada_acesso_conta_em_cada_um():
    muns = {"C": _mun(X=(100, [1]))}
    part = {"diretos": {1: {"p1", "p2"}}, "todos": {1: {"p1", "p2"}}}
    r = calcular(muns, CEN, part, PIX)
    assert r["diretos"]["ptts"]["p2"]["acessos"] == 100 and "p1" not in r["diretos"]["ptts"]       # influência provável: só o mais próximo (p2)
    assert r["alcance_diretos"]["ptts"]["p1"]["municipios_faixa"]["C"][0] == 100                  # alcance: C nos dois PTTs
    assert r["alcance_diretos"]["ptts"]["p2"]["municipios_faixa"]["C"][0] == 100
    assert r["alcance_diretos"]["ptts"]["p1"]["p50_km"] > r["alcance_diretos"]["ptts"]["p2"]["p50_km"] > 0       # a distância é a de cada PTT


def test_alcance_diretos_esta_contido_em_alcance_todos_e_usa_a_participacao_da_visao():
    muns = {"A": _mun(X=(100, [1]), Y=(60, [2])), "C": _mun(Y=(40, [2]))}
    part = {"diretos": {1: {"p1"}}, "todos": {1: {"p1"}, 2: {"p1", "p2"}}}
    r = calcular(muns, CEN, part, PIX)
    d, t = r["alcance_diretos"]["ptts"], r["alcance_todos"]["ptts"]
    assert set(d) == {"p1"} and set(t) == {"p1", "p2"}
    for ptt, x in d.items():
        assert set(x["municipios_faixa"]) <= set(t[ptt]["municipios_faixa"]) and x["acessos"] <= t[ptt]["acessos"] and x["operadoras"] <= t[ptt]["operadoras"]
    assert d["p1"]["acessos"] == 100 and d["p1"]["municipios"] == 1
    assert t["p1"]["acessos"] == 200 and t["p2"]["acessos"] == 100                 # Y entra no p1 (A e C) e no p2 (A e C)


def test_alcance_pondera_percentis_pelos_acessos_do_alcance_total_e_conta_cnpj_com_varios_asns_uma_vez():
    cen = {str(i): (float(i), 0.0) for i in range(1, 11)}
    muns = {str(i): _mun(X=(10, [1, 2])) for i in range(1, 11)}                 # 10 municípios, um CNPJ com dois ASNs, os dois no PTT p
    part = {"diretos": {1: {"p"}, 2: {"p"}}, "todos": {1: {"p"}, 2: {"p"}}}
    r = calcular(muns, cen, part, {"p": [(0.0, 0.0, "coordenada")]})["alcance_todos"]["ptts"]["p"]
    assert r["acessos"] == 100 and r["operadoras"] == 1 and r["municipios"] == 10                                 # acessos uma vez só
    assert abs(r["p50_km"] - 5 * 111.2) < 1 and abs(r["p80_km"] - 8 * 111.2) < 1 and abs(r["p90_km"] - 9 * 111.2) < 1
    assert [r["municipios_faixa"][str(i)][1] for i in range(1, 11)] == [1, 1, 1, 1, 1, 2, 2, 2, 3, 3]
    assert r["faixas"]["ate_p50"] == {"municipios": 5, "acessos": 50}


def test_documento_publicado_traz_as_quatro_visoes_por_ptt_e_o_indice_nacional_so_as_duas():
    sici = {"mes_referencia": "2026-08", "municipios": {"A": {"nome": "Cidade A", "uf": "AA", **_mun(**{"12345678000199": (100, [1])})},
                                                       "C": {"nome": "Cidade C", "uf": "AA", **_mun(**{"12345678000199": (50, [1])})}}}
    idx = [{"code": "p1", "name": "Cidade A", "uf": "AA"}, {"code": "p2", "name": "Cidade C", "uf": "AA"}]
    cadastro = {"p1": [{"name": "x", "address": "", "lat": 0.0, "lon": 0.0}], "p2": [{"name": "y", "address": "", "lat": 0.0, "lon": 2.0}]}
    part = {"diretos": {1: {"p1", "p2"}}, "todos": {1: {"p1", "p2"}}}
    doc = montar("2026-11-22", sici, idx, cadastro, CEN, {}, part)
    assert set(doc["ptts"]["p1"]["visoes"]) == {"diretos", "todos", "alcance_diretos", "alcance_todos"}
    assert set(doc["municipios"]) == {"diretos", "todos"} and set(doc["totais"]) == {"diretos", "todos"}
    assert doc["ptts"]["p1"]["visoes"]["diretos"]["acessos"] == 100 and doc["ptts"]["p1"]["visoes"]["alcance_diretos"]["acessos"] == 150     # p1 perde C para o p2 na disputa
    assert doc["ptts"]["p2"]["visoes"]["alcance_diretos"]["municipios"] == 2
    assert "12345678000199" not in json.dumps(doc)
