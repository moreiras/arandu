# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Regra única de comparabilidade (PT-28): quando a variação entre dois pontos não é calculada."""
from __future__ import annotations

from core import comparabilidade as c


def _p(data, valor, **meta):
    return {"date": data, "valor": valor, "meta": meta}


def test_pontos_da_mesma_base_e_metodo_sao_comparaveis():
    r = c.avaliar(_p("2026-11-15", 10, base="a", metodo="m1"), _p("2026-11-22", 12, base="a", metodo="m1"))
    assert r["comparavel"] and not r["motivos"] and not r["avisos"]
    v = c.variacao(_p("2026-11-15", 10, base="a"), _p("2026-11-22", 12, base="a"))
    assert (v["calculada"], v["absoluta"], v["pct"]) == (True, 2, 20.0)


def test_percentual_varia_em_pontos_percentuais_sem_pct():
    v = c.variacao(_p("2026-11-15", 60.21), _p("2026-11-22", 60.48), unidade="pp")
    assert v["calculada"] and v["unidade"] == "pp" and v["absoluta"] == 0.27 and v["pct"] is None


def test_ausente_nao_vira_zero():
    v = c.variacao(_p("2026-11-15", None), _p("2026-11-22", 5))
    assert not v["calculada"] and "absoluta" not in v and v["motivos"][0]["codigo"] == "ausente"


def test_base_diferente_bloqueia_a_variacao():
    # A base do `diff` (inválidas 444) não é a dos KPIs (659): "+37" colado a "659" seria errado
    v = c.variacao(_p("2026-11-15", 407, base="serie_semanal"), _p("2026-11-22", 659, base="kpi"))
    assert not v["calculada"] and [m["codigo"] for m in v["motivos"]] == ["base_diferente"]


def test_metodo_mudou_bloqueia():
    r = c.avaliar(_p("2026-11-15", 1, metodo="regras-aaa"), _p("2026-11-22", 2, metodo="regras-bbb"))
    assert not r["comparavel"] and r["motivos"][0]["codigo"] == "metodo_mudou"
    assert "regras-aaa" in r["motivos"][0]["detalhe"]


def test_cobertura_que_triplica_bloqueia_e_variacao_pequena_nao():
    # Filtragem: 1.407 para 4.144 ASNs medidos
    r = c.avaliar(_p("2026-11-15", 1, cobertura={"filtragem": 1407}), _p("2026-11-22", 2, cobertura={"filtragem": 4144}))
    assert not r["comparavel"] and r["motivos"][0]["codigo"] == "cobertura_mudou"
    assert "1407 para 4144" in r["motivos"][0]["detalhe"]
    ok = c.avaliar(_p("2026-11-15", 1, cobertura={"filtragem": 4000}), _p("2026-11-22", 2, cobertura={"filtragem": 4144}))
    assert ok["comparavel"]


def test_limiar_de_cobertura_e_exato():
    limite = c.avaliar(_p("2026-11-15", 1, cobertura={"x": 100}), _p("2026-11-22", 2, cobertura={"x": 75}))
    assert not limite["comparavel"]                      # 25% exatos
    abaixo = c.avaliar(_p("2026-11-15", 1, cobertura={"x": 100}), _p("2026-11-22", 2, cobertura={"x": 76}))
    assert abaixo["comparavel"]


def test_coleta_parcial_bloqueia():
    r = c.avaliar(_p("2026-11-15", 1, coleta_ok=True), _p("2026-11-22", 2, coleta_ok=False))
    assert not r["comparavel"] and r["motivos"][0]["codigo"] == "cobertura_mudou"


def test_data_atipica_d7_vale_para_metrica_de_roa_de_estrangeiro():
    a, b = _p("2026-06-28", 100), _p("2026-07-05", 0)
    assert not c.avaliar(a, b, "n_roa", estrangeiro=True)["comparavel"]
    assert c.avaliar(a, b, "n_roa", estrangeiro=True)["motivos"][0]["codigo"] == "data_atipica"
    # ASN brasileiro e outras métricas não são afetados
    assert c.avaliar(a, b, "n_roa", estrangeiro=False)["comparavel"]
    assert c.avaliar(a, b, "users", estrangeiro=True)["comparavel"]


def test_data_atipica_em_eventos_so_nos_tipos_afetados():
    assert c.atipica_evento("2026-07-05", "roa_perdido")
    assert c.atipica_evento("2026-07-05", "asn_novo") is None
    assert c.atipica_evento("2026-07-12", "roa_perdido") is None


def test_lacuna_so_avisa():
    r = c.avaliar(_p("2026-07-05", 1), _p("2026-07-26", 2))
    assert r["comparavel"] and r["avisos"][0]["codigo"] == "lacuna"
    assert not c.avaliar(_p("2026-11-15", 1), _p("2026-11-22", 2))["avisos"]


def test_serie_corta_no_ponto_incomparavel_e_so_desenha_linha_com_quatro_comparaveis():
    pontos = [_p("2026-10-25", 1, metodo="a"), _p("2026-11-01", 2, metodo="a"), _p("2026-11-08", 3, metodo="a"),
              _p("2026-11-15", 4, metodo="b"), _p("2026-11-22", 5, metodo="b")]
    s = c.anotar_serie(pontos)
    assert s["segmentos"] == [[0, 1, 2], [3, 4]]
    assert [p["comparavel_com_anterior"] for p in s["pontos"]] == [None, True, True, False, True]
    assert s["pontos"][3]["motivos"] == ["metodo_mudou"]
    assert not s["desenhar_linha"]                      # o último segmento tem 2 pontos
    # variação só dentro do último segmento comparável: nunca atravessa o corte
    assert s["variacao"]["de"] == "2026-11-15" and s["variacao"]["absoluta"] == 1
    assert "2026-11-15" in s["nota"] and "método" in s["nota"]


def test_serie_longa_comparavel_desenha_linha():
    pontos = [_p(f"2026-11-{d:02d}", i) for i, d in enumerate((1, 8, 15, 22))]
    s = c.anotar_serie(pontos)
    assert s["desenhar_linha"] and s["variacao"]["calculada"] and "nota" not in s


def test_serie_de_um_ponto_nao_tem_variacao():
    s = c.anotar_serie([_p("2026-11-22", 5)])
    assert "variacao" not in s and s["segmentos"] == [[0]]


def test_regra_publicavel_traz_versao_e_texto():
    r = c.regra()
    assert r["versao"] == c.VERSAO_REGRA and r["texto"] and "ausente" in r["motivos"]
    assert "2026-07-05" in r["datas_atipicas"]
