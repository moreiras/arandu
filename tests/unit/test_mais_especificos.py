# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Mais-específicos das rotas brasileiras: a profundidade conta o encadeamento de sub-blocos (BGP-E4: saía sempre 0 ou 1)."""
from products.routing_analysis.mais_especificos import _analyze_more_specifics


def _r(prefix, asn=64500):
    return {"prefix": prefix, "origin_as": asn}


def test_profundidade_dois_para_sub_bloco_de_um_mais_especifico():
    rotas = [_r("198.18.0.0/24"), _r("198.18.0.0/16"), _r("198.18.0.0/22", 64501), _r("198.19.0.0/16"),
             _r("2001:db8::/32"), _r("2001:db8:1::/48"), _r("2001:db8:1::/64")]
    stats, ann = _analyze_more_specifics(rotas)
    d = {r["prefix"]: r["depth"] for r in ann}
    assert d == {"198.18.0.0/16": 0, "198.18.0.0/22": 1, "198.18.0.0/24": 2, "198.19.0.0/16": 0,
                 "2001:db8::/32": 0, "2001:db8:1::/48": 1, "2001:db8:1::/64": 2}
    assert [r["prefix"] for r in ann] == [r["prefix"] for r in rotas]                    # a ordem de entrada se mantém
    assert stats["max_depth"] == 2 and stats["avg_depth"] == round(6 / 7, 2)
    assert (stats["pbr_root"], stats["pbr_more_specific"]) == (3, 4)
    # o /24 tem como pai imediato o /22 (outra origem), não o /16
    assert next(r for r in ann if r["prefix"] == "198.18.0.0/24")["same_origin"] is False


def test_sem_rotas_e_prefixo_invalido_nao_quebram():
    assert _analyze_more_specifics([])[0]["max_depth"] == 0
    stats, ann = _analyze_more_specifics([_r("lixo"), _r("198.18.0.0/24")])
    assert [r["depth"] for r in ann] == [0, 0] and stats["max_depth"] == 0
