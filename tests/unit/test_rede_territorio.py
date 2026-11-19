# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — rede no território: IPv6 estimado, usuários atrás de ROV e dependência de trânsito, com a suposição e a cobertura à vista."""
from products.rede_territorio.build import adocao_v6, calcular_ipv6, calcular_rov, calcular_transito


def _mun(uf, **ops):
    return {"uf": uf, "operadores": [{"cnpj": c, "acessos": a, "asns": asns} for c, (a, asns) in ops.items()]}


IDX = {1: {"is_br": True, "apnic_users": 1000, "pct_v6": 40.0}, 2: {"is_br": True, "apnic_users": 3000, "pct_v6": 20.0}, 3: {"is_br": True, "apnic_users": 500}}


def test_adocao_pondera_por_usuarios_e_ignora_asn_sem_medida():
    assert adocao_v6(IDX, [1, 2]) == (40 * 1000 + 20 * 3000) / 4000
    assert adocao_v6(IDX, [3]) is None and adocao_v6(IDX, []) is None and adocao_v6(IDX, [99]) is None


def test_ipv6_por_municipio_usa_so_quem_tem_medida_e_diz_a_cobertura():
    r = calcular_ipv6({"1": _mun("SP", A=(800, [1]), B=(200, []))}, IDX)
    m = r["municipios"]["1"]
    assert m["acessos"] == 1000 and m["acessos_com_estimativa"] == 800 and m["v6_estimado"] == 320 and m["pct_v6"] == 40.0 and m["cobertura"] == 80.0
    assert r["ufs"]["SP"]["pct_v6"] == 40.0 and r["brasil"]["cobertura"] == 80.0


def test_rov_so_conta_asn_br_com_usuarios_e_amostras_suficientes():
    seg = {"1": {"uf": "SP", "rov": {"validates_pct": 100.0, "amostras": 500}}, "2": {"uf": "SP", "rov": {"validates_pct": 50.0, "amostras": 50}},
           "3": {"uf": "RJ", "rov": {"validates_pct": 10.0, "amostras": 200}}}
    r = calcular_rov(IDX, seg)
    sp = r["ufs"]["SP"]
    assert sp["usuarios"] == 4000 and sp["usuarios_com_medida"] == 1000 and sp["usuarios_atras_rov"] == 1000 and sp["pct_atras_rov"] == 100.0 and sp["cobertura"] == 25.0   # o ASN 2 tem poucas amostras
    assert r["ufs"]["RJ"]["usuarios_atras_rov"] == 50 and r["brasil"]["usuarios"] == 4500


def test_transito_distingue_um_provedor_de_nenhum_inferido():
    muns = {"1": _mun("SP", A=(600, [1]), B=(300, [2]), C=(100, [9]))}
    prov = {1: {100}, 2: {100, 200}}                                    # o ASN 9 não tem relação inferida: desconhecido, não "um só provedor"
    r = calcular_transito(muns, prov, {100: "Trânsito X", 200: "Trânsito Y"})
    m = r["municipios"]["1"]
    assert m["acessos_com_relacao"] == 900 and m["acessos_provedor_unico"] == 600 and m["pct_provedor_unico"] == 66.7 and m["cobertura"] == 90.0
    assert m["provedor_principal"] == {"asn": 100, "nome": "Trânsito X", "pct_dos_acessos": 100.0}
    assert r["ufs"]["SP"]["pct_provedor_unico"] == 66.7


def test_provedores_firmes_usam_o_nivel_numerico_da_regiao():
    from products.rede_territorio.build import _provedores_firmes
    regiao = {"asns": {"1": {"n": "A", "p": [[100, 99, 0], [200, 80, 1], [300, 60, 2]]}, "2": {"n": "B", "p": [[300, 60, 2]]}, "3": {"n": "C", "p": []}}}
    prov, nomes = _provedores_firmes(regiao)
    assert prov == {1: {100, 200}} and nomes == {1: "A", 2: "B", 3: "C"}            # nível 2 (possível) e ASN sem provedor ficam de fora
