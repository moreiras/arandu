# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Sem declaração ao SICI: `grupo_declara` exato e UF de quem parou de declarar (RANKINGS-E2, RANKINGS-E4)."""

import pytest

from api.services import sici_indicadores as s
from products.sici_indicadores.build import calcular_indicadores

# ── RANKINGS-E2 e RANKINGS-E4 ──

OM = {"snapshot_date": "d", "mes_referencia": "2026-09", "fonte": "f", "parametros": {}, "por_uf": {},
      "itens": {"t": {"uf": "AC", "classe": "com_usuarios_apnic", "usuarios_apnic": 500, "grupo_declara": True},
                "f": {"uf": "AC", "classe": "com_usuarios_apnic", "usuarios_apnic": 400, "grupo_declara": False},
                "n1": {"uf": "AM", "classe": "com_usuarios_apnic", "usuarios_apnic": 300},
                "n2": {"uf": "AM", "classe": "sem_usuarios", "usuarios_apnic": 10}}}


@pytest.mark.parametrize("valor,esperado", [(None, {"t", "f", "n1", "n2"}), ("true", {"t"}), ("false", {"f"}), (False, {"f"}),
                                            ("desconhecido", {"n1", "n2"})])
def test_grupo_declara_tem_semantica_exata(valor, esperado):
    r = s.sem_declaracao(OM, {}, "outorga_sem_declaracao", None, None, valor, 50, 0)
    assert {i["cnpj"] for i in r["items"]} == esperado


def test_grupo_declara_tres_estados_somam_o_total_da_classe():
    tot = lambda v: s.sem_declaracao(OM, {}, "outorga_sem_declaracao", None, "com_usuarios_apnic", v, 50, 0)["total"]   # noqa: E731
    assert tot("true") + tot("false") + tot("desconhecido") == tot(None) == 3
    with pytest.raises(s.IndicadoresErro):
        s.sem_declaracao(OM, {}, "outorga_sem_declaracao", None, None, "talvez", 50, 0)


def test_parou_de_declarar_filtra_uf_ou_recusa():
    ind = {"parou_de_declarar": {"x": {"empresa": "X", "acessos_no_ultimo_mes": 10, "uf": "AC"}, "y": {"empresa": "Y", "acessos_no_ultimo_mes": 5, "uf": "SP"}}}
    r = s.sem_declaracao(OM, ind, "parou_de_declarar", "ac", None, None, 50, 0)
    assert r["total"] == 1 and r["items"][0]["cnpj"] == "x" and r["escopo"] == {"uf": "AC"}
    assert s.sem_declaracao(OM, ind, "parou_de_declarar", None, None, None, 50, 0)["total"] == 2
    antigo = {"parou_de_declarar": {"x": {"empresa": "X", "acessos_no_ultimo_mes": 10}}}      # snapshot sem a UF: não devolve o nacional
    with pytest.raises(s.IndicadoresErro) as e:
        s.sem_declaracao(OM, antigo, "parou_de_declarar", "AC", None, None, 50, 0)
    assert e.value.status == 400


def test_produto_grava_uf_de_quem_parou_de_declarar():
    serie = {"z": [["2025-12", 100, 90, 10]]}
    meses = {"2026-09": {"a": {"empresa": "A", "acessos": 5, "por_municipio": {}}}}
    ind = calcular_indicadores("2026-09", meses, serie, {"z": "Z LTDA"}, {"z": "AC"})
    assert ind["parou_de_declarar"]["z"]["uf"] == "AC"


def test_parou_de_declarar_aceita_o_filtro_de_grupo_com_a_mesma_semantica():
    ind = {"parou_de_declarar": {"a": {"empresa": "A", "acessos_no_ultimo_mes": 30, "grupo_declara": True},
                                 "b": {"empresa": "B", "acessos_no_ultimo_mes": 20, "grupo_declara": False},
                                 "c": {"empresa": "C", "acessos_no_ultimo_mes": 10}}}
    cnpjs = lambda v: [i["cnpj"] for i in s.sem_declaracao(OM, ind, "parou_de_declarar", None, None, v, 50, 0)["items"]]   # noqa: E731
    assert cnpjs("true") == ["a"] and cnpjs("false") == ["b"] and cnpjs("desconhecido") == ["c"] and cnpjs(None) == ["a", "b", "c"]
