# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`grupo_mercado`: série, posição, UFs, sobreposição interna e concorrentes do grupo."""
from api.services.grupo_mercado import indice, mercado_do_grupo

MESES = [f"2025-{m:02d}" for m in range(10, 13)] + [f"2026-{m:02d}" for m in range(1, 11)]       # 13 meses: 2025-10 .. 2026-10
SERIE = lambda base: [[m, base + i, 0, 0] for i, m in enumerate(MESES)]                          # noqa: E731
DADOS = {
    "serie_por_cnpj": {"A": SERIE(100), "B": SERIE(50), "C": SERIE(120), "D": SERIE(10)},
    "serie_total": [{"mes": m, "acessos": 1000} for m in MESES],
    "cnpjs": {
        "A": {"por_municipio": {"1": {"uf": "SP", "acessos": 60}, "2": {"uf": "SP", "acessos": 40}}, "por_tecnologia": {"FTTH": 100}},
        "B": {"por_municipio": {"2": {"uf": "SP", "acessos": 30}, "3": {"uf": "RJ", "acessos": 20}}, "por_tecnologia": {"FTTH": 50}},
        "C": {"por_municipio": {"1": {"uf": "SP", "acessos": 120}, "9": {"uf": "SP", "acessos": 150}}}, "D": {"por_municipio": {}},
    },
}
GRUPOS = [{"grupo_id": "grp_ab", "tamanho": 2, "cnpjs": [{"cnpj": "A"}, {"cnpj": "B"}]}]
MG = {"ufs": {"SP": {"hhi_cnpj": 3000, "hhi_grupo": 3500, "faixa_grupo": "concentrado"}},
      "sobreposicao": {"A": [{"cnpj": "C", "empresa": "Cê", "municipios_em_comum": 2, "acessos_dele_nos_comuns": 120, "mesmo_grupo": False}, {"cnpj": "B", "empresa": "Bê", "municipios_em_comum": 1, "mesmo_grupo": True}],
                       "B": [{"cnpj": "C", "empresa": "Cê", "municipios_em_comum": 1, "acessos_dele_nos_comuns": 120, "mesmo_grupo": False}]}}


def test_serie_soma_o_grupo_e_a_posicao_junta_os_cnpjs():
    idx = indice(DADOS, GRUPOS, meses=13)
    r = mercado_do_grupo({"grupo_id": "grp_ab", "tamanho": 2, "cnpjs": [{"cnpj": "A"}, {"cnpj": "B"}]}, idx, DADOS, MG)
    assert r["serie"][0]["acessos"] == 150 and r["serie"][-1]["acessos"] == 174 and r["serie"][0]["parcela"] == 15.0
    # grupo A+B (150) passa C (120) e D (10): 1ª posição; sem agrupar, C seria a 1ª
    assert r["posicao"]["atual"] == 1 and r["posicao"]["ha_12_meses"] == 1 and r["posicao"]["unidades"] == 3 and r["posicao"]["mes_ha_12_meses"] == "2025-10"


def test_ufs_sobreposicao_interna_e_concorrentes():
    idx = indice(DADOS, GRUPOS, meses=13)
    r = mercado_do_grupo({"grupo_id": "grp_ab", "tamanho": 2, "cnpjs": [{"cnpj": "A"}, {"cnpj": "B"}]}, idx, DADOS, MG)
    sp = next(u for u in r["por_uf"] if u["uf"] == "SP")
    assert sp["acessos"] == 130 and sp["parcela_na_uf"] == 32.5 and sp["hhi_grupo"] == 3500 and sp["faixa_grupo"] == "concentrado"
    assert r["sobreposicao_interna"] == {"municipios": 3, "com_mais_de_um_cnpj": 1}          # só o município 2 tem os dois CNPJs
    assert [c["cnpj"] for c in r["concorrentes"]] == ["C"] and r["concorrentes"][0]["municipios_em_comum"] == 2   # mesmo grupo fora; vale a maior sobreposição
    assert r["por_tecnologia"] == {"FTTH": 150} and "inferido" in r["natureza"]


def test_cnpj_avulso_e_um_grupo_de_uma_empresa():
    idx = indice(DADOS, GRUPOS, meses=13)
    r = mercado_do_grupo({"grupo_id": "grp_c", "tamanho": 1, "cnpjs": [{"cnpj": "C"}]}, idx, DADOS, MG)
    assert r["serie"][0]["acessos"] == 120 and r["posicao"]["atual"] == 2 and r["cnpjs_com_acessos"] == 1
