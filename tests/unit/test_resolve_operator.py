# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""operadora_resolver: marca curada antes do trecho do nome, AS estrangeiro só sem nenhum brasileiro."""
from api.services.consultas import ConsultasService

ASNS = [
    {"asn": 26599, "name": "TELEFÔNICA BRASIL S.A", "cnpj_root": "02558157", "is_br": True},
    {"asn": 18881, "name": "TELEFÔNICA BRASIL S.A", "cnpj_root": "02558157", "is_br": True},
    {"asn": 34942, "name": "VIVOR-AS Vivor B.V., NL", "cnpj_root": None, "is_br": False},
    {"asn": 265476, "name": "PONTOVIVO INTERNET", "cnpj_root": "07229330", "is_br": True},
    {"asn": 999, "name": "ZETA NETWORKS, US", "cnpj_root": None, "is_br": False},
]
OPS = [{"empresa": "PROVEDOR X", "grupo_economico": "GRUPO X", "asns": [77]}]


class _Loja:
    def cdn_presence(self, d):
        return {"cdns": [{"name": "Google", "asns": [15169]}]}


class _Servico(ConsultasService):
    def query_table(self, d, col):
        return ASNS if col == "asns" else OPS


def _r(nome):
    return _Servico(_Loja()).resolve_operator("2026-11-13", nome)


def test_marca_curada_traz_os_asns_da_raiz():
    r = _r("Vivo")
    assert r["metodo"] == "curada" and r["asns"] == [18881, 26599]


def test_operadora_do_sici_pelo_grupo():
    r = _r("Grupo X")
    assert r["metodo"] == "sici" and r["asns"] == [77]


def test_cdn_e_trecho_do_nome():
    assert _r("google")["metodo"] == "cdn"
    r = _r("pontovivo")
    assert r["metodo"] == "nome_do_as" and r["asns"] == [265476]
    r = _r("zeta")                                                   # sem brasileiro: o estrangeiro vem, com aviso no `base`
    assert r["asns"] == [999] and "estrangeiros" in r["base"]
    assert _r("inexistente")["asns"] == []
