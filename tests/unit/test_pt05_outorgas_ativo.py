# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Filtro `ativo` das outorgas com um só serviço (contradições item 3, OPERADORAS-E8)."""
from types import SimpleNamespace

# ── contradições, item 3 / OPERADORAS-E8: na aba SCM, "ativo" é acesso fixo ──

def test_ativo_com_um_servico_olha_o_acesso_daquele_servico():
    from api.routes.outorgas import montar_lista

    linhas = [
        {"cnpj": "a", "servicos": ["SCM"], "uf": "SP", "municipio": "", "razao_social": "A", "nome_fantasia": "", "asns": [], "porte": "",
         "acessos_fixo": 10, "acessos_movel": 0, "acessos": 10, "ativo": True},
        {"cnpj": "b", "servicos": ["SCM", "SMP"], "uf": "SP", "municipio": "", "razao_social": "B", "nome_fantasia": "", "asns": [], "porte": "",
         "acessos_fixo": 0, "acessos_movel": 50, "acessos": 50, "ativo": True},                       # só declara móvel (Telecall, Datora)
    ]
    store = SimpleNamespace(outorgas_unificadas=lambda d: linhas)
    cnpjs = lambda **kw: [r["cnpj"] for r in montar_lista(store, "d", **kw)["items"]]   # noqa: E731
    assert cnpjs(servico="SCM", ativo=True) == ["a"]
    assert cnpjs(servico="SCM", ativo=False) == ["b"]
    assert cnpjs(servico="SMP", ativo=True) == ["b"]
    assert sorted(cnpjs(ativo=True)) == ["a", "b"]                                   # sem serviço: fixo ou móvel, como antes
    assert sorted(cnpjs(servico="SCM,SMP", ativo=True)) == ["a", "b"]
