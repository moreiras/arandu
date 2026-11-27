# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PT-22 (municipios 5.2): `territorio.resumo`, os agregados por distância ao PTT que a síntese de `/municipios` cita."""
from __future__ import annotations

import pytest

from api.services import territorio as t

DOC = {"snapshot_date": "2026-11-22", "mes_referencia_sici": "2026-09", "censo_ano": "2022", "pnad_ano": "2025", "fonte": "x", "formulas": {}, "limites": "y"}


def _m(ibge, uf, dom, acessos, pop, km=None, **kw):
    ln = {"ibge": ibge, "uf": uf, "domicilios": dom, "domicilios_projetados": dom, "acessos": acessos, "populacao_estimada": pop,
          "penetracao": (acessos / dom) if dom else None, "nao_visto": kw.pop("nao_visto", 0)}
    if km is not None:
        ln.update({"km_ptt": km, "sem_ptt_proximo": km > 100})
    ln.update(kw)
    return ln


LINHAS = [
    _m("1", "AM", 1000, 500, 3000, km=250, nao_visto=100),       # longe
    _m("2", "AM", 2000, 1000, 6000, km=40),                      # perto
    _m("3", "SP", 10000, 12000, 30000, km=10),                   # perto, mais acessos que domicílios
    _m("4", "SP", 500, 100, 1500, km=300),                       # longe, abaixo do porte (500 domicílios)
    _m("5", "SP", 4000, 100, 9000),                              # sem centróide
    {"ibge": "6", "uf": "SP", "domicilios": None, "acessos": None},      # sem Censo
]


def test_grupos_nao_se_sobrepoem_e_somam_o_total():
    r = t.resumo(DOC, LINHAS, None)
    assert r["total"]["municipios"] == 6
    assert (r["a_mais_de_100km"]["municipios"], r["ate_100km"]["municipios"], r["sem_distancia"]["municipios"]) == (2, 2, 2)
    for campo in ("municipios", "populacao_estimada", "domicilios_projetados", "acessos"):
        assert r["a_mais_de_100km"][campo] + r["ate_100km"][campo] + r["sem_distancia"][campo] == r["total"][campo], campo
    assert r["escopo"] == {"pais": "BR"} and r["raio_sem_ptt_km"] == 100


def test_razao_de_acessos_por_domicilio_usa_so_municipios_com_domicilios():
    r = t.resumo(DOC, LINHAS, None)
    assert r["a_mais_de_100km"]["acessos_por_domicilio"] == pytest.approx((500 + 100) / (1000 + 500), abs=1e-3)
    assert r["ate_100km"]["acessos_por_domicilio"] == pytest.approx((1000 + 12000) / (2000 + 10000), abs=1e-3)
    assert r["sem_distancia"]["acessos_por_domicilio"] == pytest.approx(100 / 4000, abs=1e-3)       # o município sem Censo não entra na razão


def test_contagens_de_penetracao_porte_e_sem_domicilios():
    p = t.resumo(DOC, LINHAS, None)["penetracao"]
    assert p["porte_minimo_domicilios"] == 1000
    assert p["municipios_com_penetracao"] == 4          # 1, 2, 3 e 5 (o 4 tem 500 domicílios e o 6 não tem Censo)
    assert p["municipios_abaixo_do_porte"] == 1 and p["municipios_sem_domicilios"] == 1
    assert p["com_mais_acessos_que_domicilios"] == 1    # só o município 3


def test_uf_restringe_e_uf_desconhecida_e_404():
    r = t.resumo(DOC, LINHAS, "am")
    assert r["escopo"] == {"uf": "AM"} and r["total"]["municipios"] == 2 and r["a_mais_de_100km"]["municipios"] == 1
    with pytest.raises(t.TerritorioErro) as e:
        t.resumo(DOC, LINHAS, "ZZ")
    assert e.value.status == 404


def test_grupo_vazio_nao_vira_razao_zero():
    r = t.resumo(DOC, [_m("1", "AM", 1000, 500, 3000, km=10)], None)
    assert r["a_mais_de_100km"]["municipios"] == 0 and r["a_mais_de_100km"]["acessos_por_domicilio"] is None


def test_resposta_traz_as_datas_e_os_limites_do_territorio():
    r = t.resumo(DOC, LINHAS, None)
    assert r["mes_referencia_sici"] == "2026-09" and r["censo_ano"] == "2022" and r["limites"] == "y" and "linha reta" in r["criterio"]


def test_ranking_filtra_municipios_sem_rede_com_sessao_em_ptt():
    """PT-25 / municipios 5.3: separa distância de ausência de interligação registrada; sem o produto de redes por município o filtro não afirma nada."""
    rs = lambda asns, sessao: {"asns": asns, "sessao_ptt": sessao, "rotas_ptt": sessao}      # noqa: E731
    linhas = [_m("1", "AM", 1000, 500, 3000, km=250, redes_sede=rs(3, 0)),      # longe, redes sem sessão
              _m("2", "AM", 2000, 1000, 6000, km=250, redes_sede=rs(5, 2)),     # longe, com sessão
              _m("3", "AM", 3000, 1000, 6000, km=250, redes_sede=rs(0, 0)),     # longe, sem ASN com sede
              _m("4", "AM", 4000, 1000, 6000, km=250)]                          # longe, sem o produto de redes
    ids = lambda **kw: [i["ibge"] for i in t.ranking(DOC, linhas, "populacao_estimada", None, True, True, 0, 50, 0, **kw)["items"]]      # noqa: E731
    assert ids() == ["1", "2", "3", "4"]
    assert ids(sem_sessao_ptt=True) == ["1", "3"]
    assert ids(sem_sessao_ptt=False) == ["2"]
    r = t.ranking(DOC, linhas, "populacao_estimada", None, True, True, 0, 50, 0, sem_sessao_ptt=True)
    assert r["filtros"]["sem_sessao_ptt"] is True
