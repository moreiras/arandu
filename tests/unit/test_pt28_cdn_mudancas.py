# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PT-28 / CDNS-5.4: mudanças na matriz de CDNs entre dois snapshots com regra de comparabilidade."""
from __future__ import annotations

from api.services import cdn_mudancas as cm


def _doc(data, cdns):
    return {"snapshot_date": data, "cdns": [{"name": n, "asns": asns, "ixbr": ixbr} for n, asns, ixbr in cdns]}


def _idx(**membros):
    return [{"code": c, "ixbr_members_count": n} for c, n in membros.items()]


def test_entrada_e_saida_de_ptt_com_mesmo_catalogo_e_cobertura():
    a = _doc("2026-11-15", [("Sage", [1], ["sp"]), ("Qwilt", [2], ["sp", "rj"])])
    b = _doc("2026-11-22", [("Sage", [1], ["sp", "rj"]), ("Qwilt", [2], ["sp"])])
    r = cm.mudancas(a, b, _idx(sp=10, rj=5), _idx(sp=11, rj=5))
    assert r["entradas"] == [{"cdn": "Sage", "ptt": "rj"}] and r["saidas"] == [{"cdn": "Qwilt", "ptt": "rj"}]
    assert r["nao_comparaveis"] == [] and r["totais"]["entradas"] == 1 and r["selo"] == "fato"
    assert r["comparabilidade"]["texto"] and r["catalogo"] == {"cdns_incluidas": [], "cdns_retiradas": [], "asns_alterados": []}


def test_mudanca_de_catalogo_fica_a_parte_e_a_variacao_de_ptt_nao_e_comparavel():
    a = _doc("2026-11-15", [("Sage", [1], ["sp"]), ("Antiga", [9], ["sp"])])
    b = _doc("2026-11-22", [("Sage", [1, 3], ["sp", "rj"]), ("Nova", [7], ["sp"])])
    r = cm.mudancas(a, b, _idx(sp=10, rj=5), _idx(sp=10, rj=5))
    assert r["entradas"] == [] and r["saidas"] == []                       # a entrada de Sage em rj veio com ASN novo no catálogo: não é mudança da rede
    assert [(x["cdn"], x["ptt"], x["motivos"]) for x in r["nao_comparaveis"]] == [("Sage", "rj", ["base_diferente"])]
    assert r["catalogo"]["cdns_incluidas"] == ["Nova"] and r["catalogo"]["cdns_retiradas"] == ["Antiga"]
    assert r["catalogo"]["asns_alterados"] == [{"cdn": "Sage", "asns_incluidos": [3], "asns_retirados": []}]


def test_ptt_sem_lista_de_membros_numa_das_datas_nao_vira_saida():
    a = _doc("2026-11-15", [("Sage", [1], ["sp", "ce"])])
    b = _doc("2026-11-22", [("Sage", [1], ["sp"])])
    r = cm.mudancas(a, b, _idx(sp=10, ce=4), _idx(sp=10, ce=0))             # `ce` sem membros na segunda data
    assert r["saidas"] == []
    assert r["nao_comparaveis"][0]["ptt"] == "ce" and r["nao_comparaveis"][0]["motivos"] == ["cobertura_mudou"]
    assert r["nao_comparaveis"][0]["estava"] is True and r["nao_comparaveis"][0]["esta"] is False


def test_ordem_neutra_por_cdn_e_ptt():
    a = _doc("2026-11-15", [("Zeta", [1], []), ("alfa", [2], [])])
    b = _doc("2026-11-22", [("Zeta", [1], ["sp", "ba"]), ("alfa", [2], ["rj"])])
    r = cm.mudancas(a, b, _idx(sp=1, ba=1, rj=1), _idx(sp=1, ba=1, rj=1))
    assert [(x["cdn"], x["ptt"]) for x in r["entradas"]] == [("alfa", "rj"), ("Zeta", "ba"), ("Zeta", "sp")]


def test_aviso_de_lacuna_entre_as_datas():
    r = cm.mudancas(_doc("2026-08-30", []), _doc("2026-11-22", []), [], [])
    assert [x["codigo"] for x in r["comparabilidade"]["avisos"]] == ["lacuna"]
