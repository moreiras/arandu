# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — diagnóstico de estabilidade: a estabilidade entre coletas separa o efeito da coleta do efeito do algoritmo."""
from products.as_relationships import diagnostico


def test_comparar_da_jaccard_e_o_que_saiu_e_entrou():
    r = diagnostico.comparar({(1, 2), (1, 3), (1, 4), (1, 5)}, {(1, 2), (1, 3), (1, 6)})
    assert r["iguais"] == 2 and r["so_em_a"] == 2 and r["so_em_b"] == 1
    assert r["saiu_pct"] == 50.0 and r["entrou_pct"] == 25.0 and r["jaccard"] == round(2 / 5, 4)
    assert diagnostico.comparar(set(), set())["jaccard"] is None and diagnostico.comparar(set(), {(1, 2)})["saiu_pct"] is None


def test_estabilidade_entre_coletas_isola_coleta_e_algoritmo(monkeypatch, tmp_path):
    # v1 muda 1 elo entre as datas (efeito da coleta); em cada data o v2 rebaixa 1 elo do v1 (efeito do algoritmo)
    dados = {(1, "d1"): {(1, 2), (1, 3), (1, 4), (1, 5)}, (1, "d2"): {(1, 2), (1, 3), (1, 4), (1, 6)},
             (2, "d1"): {(1, 2), (1, 3), (1, 4)}, (2, "d2"): {(1, 2), (1, 3), (1, 4)}}
    monkeypatch.setattr(diagnostico, "analisar", lambda base, d, cfg, afi, so=None: (dados[(cfg.versao, d)], {}))
    r = diagnostico.estabilidade_entre_coletas(tmp_path, "d1", "d2", cfg=diagnostico.carregar(), afis=("v4",))
    assert r["v4"]["coleta"]["v1"]["iguais"] == 3 and r["v4"]["coleta"]["v1"]["jaccard"] == round(3 / 5, 4)
    assert r["v4"]["coleta"]["v2"]["jaccard"] == 1.0                                   # o refino absorveu a diferença da coleta nesse exemplo
    assert r["v4"]["algoritmo"]["d1"]["so_em_a"] == 1 and r["v4"]["algoritmo"]["d2"]["so_em_a"] == 1


def test_comparar_classes_separa_mudanca_de_classe_de_entrada_e_saida():
    a = {(1, 2): "p2c:1", (1, 3): "p2p", (1, 4): "p2c:1", (1, 5): "p2c:1"}
    b = {(1, 2): "p2c:2", (1, 3): "p2c:1", (1, 4): "p2c:1", (1, 6): "p2p"}
    r = diagnostico.comparar_classes(a, b)
    assert r["em_comum"] == 3 and r["mudaram_de_classe"] == 2 and r["mudou_pct"] == round(100 * 2 / 3, 2)
    assert r["p2c_que_inverteu"] == 1 and r["so_em_a"] == 1 and r["so_em_b"] == 1
    assert diagnostico.comparar_classes({}, {})["mudou_pct"] is None


def test_classes_dos_vereditos_so_nivel_provavel_ou_mais():
    from types import SimpleNamespace as V

    vs = [V(a=1, b=2, tipo="p2c", nivel="provavel"), V(a=3, b=4, tipo="p2p", nivel="confirmado"), V(a=5, b=6, tipo="p2c", nivel="possivel"),
          V(a=7, b=8, tipo="sibling", nivel="provavel")]
    assert diagnostico.classes_dos_vereditos(vs) == {(1, 2): "p2c:1", (3, 4): "p2p"}


def test_so_comuns_passa_a_intersecao_dos_coletores_aos_dois_lados(monkeypatch, tmp_path):
    vistos = []
    monkeypatch.setattr(diagnostico.build, "_colecao", lambda base, d, afi: (None, ["a", "b", "c"] if d == "d1" else ["b", "c", "d"], d))
    monkeypatch.setattr(diagnostico, "analisar", lambda base, d, cfg, afi, so=None: (vistos.append((d, so)) or set(), {}))
    r = diagnostico.estabilidade_entre_coletas(tmp_path, "d1", "d2", cfg=diagnostico.carregar(), afis=("v4",), versoes=(1,), so_comuns=True)
    assert r["coletores_em_comum"]["v4"] == ["b", "c"] and {x[1] == {"b", "c"} for x in vistos} == {True}
