# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Interligação de cada PTT na lista `/ixps` (PT-24 / IXPS-E5.4): sessões nos route servers por família e CDNs da lista curada."""
from api.services import ptt_interligacao as li


def _rs(r, afi, total, up, consultado=True, incerto=False):
    return {"rs": r, "afi": afi, "sessoes": total, "sessoes_up": up, "consultado": consultado, "vizinhos_incerto": incerto}


DOC = {"fonte": "Alice-LG", "coletado_em": "2026-11-22T06:00:00+00:00", "versao_alice": "6.1.0", "ixps": {
    "sp": {"rs": [_rs("a", "v6", 100, 90), _rs("b", "v6", 50, 40), _rs("a4", "v4", 80, 70)]},
    "to": {"rs": [_rs("t6", "v6", 92, 36), _rs("t4-velho", "v4", 10, 0, incerto=True)]},
    "ap": {"rs": [_rs("ap6", "v6", 0, 0, consultado=False)]},
}}
CDNS = {"cdns": [{"name": "X"}, {"name": "Y"}], "ixbr_columns": [{"code": "sp", "cdn_count": 50}, {"code": "to", "cdn_count": 0}]}


def test_soma_sessoes_por_familia_e_down_e_total_menos_up():
    r = li.sessoes_por_ptt(DOC)["sp"]
    assert r["v6"] == {"up": 130, "down": 20, "sessoes": 150, "rs": 2}
    assert r["v4"] == {"up": 70, "down": 10, "sessoes": 80, "rs": 1}


def test_route_server_sem_vizinhos_atuais_fica_fora_da_conta_e_e_contado_a_parte():
    r = li.sessoes_por_ptt(DOC)["to"]
    assert r["v4"] is None and r["rs_sem_vizinhos_atuais"] == 1               # a sessão down do RS velho não vira "down" do PTT
    assert r["v6"]["up"] == 36 and r["v6"]["down"] == 56


def test_ptt_sem_route_server_consultado_nao_tem_entrada_nem_zero():
    assert "ap" not in li.sessoes_por_ptt(DOC)
    ixps = li.enriquecer([{"code": "ap"}], DOC, CDNS)
    assert ixps[0]["route_servers"] is None and ixps[0]["cdns_curados"] == 0    # CDN: o produto existe e o PTT não tem nenhum


def test_cdns_ausentes_do_produto_viram_none_e_o_indice_nao_e_alterado():
    indice = [{"code": "sp", "name": "SP"}]
    novo = li.enriquecer(indice, None, None)
    assert novo[0]["cdns_curados"] is None and novo[0]["route_servers"] is None
    assert "cdns_curados" not in indice[0]                                     # o índice em cache fica como estava
    assert li.enriquecer(indice, DOC, CDNS)[0]["cdns_curados"] == 50


def test_fontes_trazem_data_e_tamanho_da_lista():
    f = li.fontes(DOC, CDNS, "2026-11-22")
    assert f["route_servers"]["coletado_em"] == "2026-11-22T06:00:00+00:00" and f["cdns"]["cdns_na_lista"] == 2
    assert li.fontes(None, None, "2026-11-22") == {"route_servers": None, "cdns": None}
