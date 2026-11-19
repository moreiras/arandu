# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Taxa de reclamações por 100 mil habitantes por município: último ano completo e base mínima de 30 casos."""
from api.services.perfis import MIN_RECLAMACOES_TAXA, PerfisService


class _Serv(PerfisService):
    def __init__(self):                                   # sem store: só a lógica da taxa
        pass

    def reclamacoes_doc(self, d):
        return {"anos": [2024, 2025, 2026], "municipios_uf": {"1": "SP", "2": "SP", "3": "RJ", "4": "RJ"}}

    def reclamacoes_municipios_uf(self, d, uf):
        itens = lambda ano, n: [{"ano": ano, "reclamacoes": n, "servico": "SCM", "marca": "X", "raizes": []}]       # noqa: E731
        if uf == "SP":
            return {"municipios": {"1": {"populacao": 100_000, "itens": itens(2025, 50) + itens(2026, 999)},      # 2026 é o ano em curso: fica de fora
                                   "2": {"populacao": 1_000, "itens": itens(2025, MIN_RECLAMACOES_TAXA - 1)}}}   # abaixo da base mínima: sem taxa
        return {"municipios": {"3": {"populacao": 0, "itens": itens(2025, 80)},                                  # sem população: sem taxa
                               "4": {"populacao": 200_000, "itens": itens(2025, MIN_RECLAMACOES_TAXA)}}}


def test_ultimo_ano_completo_e_base_minima():
    r = _Serv()._reclamacoes_100mil("2026-11-05")
    assert r["ano"] == 2025
    assert r["por_ibge"] == {"1": 50.0, "4": 15.0}


def test_sem_reclamacoes_publicadas_a_taxa_fica_vazia():
    class _Sem(_Serv):
        def reclamacoes_doc(self, d):
            return None
    assert _Sem()._reclamacoes_100mil("2026-11-05") == {"ano": None, "por_ibge": {}}
