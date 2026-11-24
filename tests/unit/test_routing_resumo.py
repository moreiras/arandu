# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Resumo nacional da análise de roteamento (Panorama técnico): estado RPKI das rotas BR e espaço por estado."""
from __future__ import annotations

import json

from products.routing_analysis import resumo
from products.routing_analysis.rpki import _build_rpki_index

VRPS = [
    {"asn": 64500, "prefix": "2001:db8::/32", "maxLength": 48},
    {"asn": 64500, "prefix": "192.0.2.0/24", "maxLength": 24},
]


def _rota(prefixo: str, origem: int) -> dict:
    return {"prefix": prefixo, "origin_as": origem, "is_origin_br": True, "is_prefix_br": True}


def test_estado_rpki_conta_rotas_e_espaco_por_estado():
    idx = _build_rpki_index(VRPS)
    v6 = [_rota("2001:db8::/32", 64500), _rota("2001:db8:1::/48", 64501), _rota("2001:db9::/48", 64502)]
    r = resumo.estado_rpki(v6, idx, "v6")
    assert (r["rotas"], r["valid"], r["invalid"], r["not_found"]) == (3, 1, 1, 1)
    assert r["asns_origem_com_invalida"] == 1
    # O /48 inválido está dentro do /32 válido: o total é a união (65536 + 1), e os estados se sobrepõem.
    assert r["espaco"] == {"unidade": "/48", "total": 65537, "valid": 65536, "invalid": 1, "not_found": 1}
    assert r["pct"]["valid"] == 33.33


def test_estado_rpki_ipv4_mais_especifico_alem_do_maxlength_e_invalido():
    idx = _build_rpki_index(VRPS)
    r = resumo.estado_rpki([_rota("192.0.2.0/25", 64500), _rota("198.51.100.0/24", 64500)], idx, "v4")
    assert (r["valid"], r["invalid"], r["not_found"]) == (0, 1, 1)
    assert r["espaco"]["unidade"] == "/24" and r["espaco"]["total"] == 2   # 0,5 + 1, arredondado


def test_montar_e_gravar(tmp_path):
    idx = _build_rpki_index(VRPS)
    doc = resumo.montar("2026-11-13", [_rota("192.0.2.0/24", 64500)], [], idx,
                        more_specifics={"v4": {"pbr_root": 3, "pbr_more_specific": 1}},
                        too_specific={"v4": [{}], "v6": []}, moas=[{}] * 500, vrps=2)
    assert doc["rpki"]["v4"]["valid"] == 1 and doc["rpki"]["v6"]["rotas"] == 0
    assert doc["rpki"]["v6"]["pct"]["valid"] is None
    assert doc["saude"]["v4"] == {"mais_especificos": 1, "mais_especificos_pct": 25.0, "filtraveis": 1}
    assert doc["saude"]["moas"] is None and "limite da coleta" in doc["saude"]["moas_indisponivel"]      # BGP-E2: a coleta não detecta MOAS
    destino = resumo.gravar(tmp_path, doc)
    assert destino.name == resumo.ARQUIVO and json.loads(destino.read_text())["vrps"] == 2
    assert not list(tmp_path.glob("*.tmp"))
