# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Contratos públicos (Compras.gov.br / PNCP) no dataset sintético.

Operadoras 1 a 4 (na ordem de `market.operators`): a 1ª tem três contratações (federal e municipal, detalhadas; um item cancelado que não conta no valor) e a leitura da faixa A; a 2ª tem uma contratação
SEM detalhe (esfera desconhecida) cujo município vem só da tabela de unidades (UASG); a 3ª foi lida e não teve resultado (ausência registrada, não zero); a 4ª é da faixa B, lida há 30 dias. As demais
operadoras do universo ainda não foram lidas pelo rodízio. Órgãos, unidades e valores são inventados."""
from __future__ import annotations

from tests.synth import market
from tests.synth.world import MUNICIPIOS, World


def _item(cnpj14: str, n: int, compra: str, un: str, uf: str, org: str, qtd: float, valor: float, sit: str, data: str) -> dict:
    return {"id": f"{un}{n:05d}", "seq": 1, "compra": compra, "un": un, "uf": uf, "org": org, "cnpj": cnpj14, "qtd": qtd, "valor": valor, "sit": sit, "data": data}


def siasg_contratos(world: World, d: str) -> dict:
    ops = market.operators(world)
    m1, m2, m3 = MUNICIPIOS[0], MUNICIPIOS[1], MUNICIPIOS[2]
    c1, c2, c3, c4 = ("11000000000191-1-000001/2026", "11000000000272-1-000002/2026", "11000000000353-1-000003/2025", "11000000000434-1-000004/2026")
    cn = [o["cnpj"][:8] + "0001" + o["cnpj"][-2:] for o in ops]
    fornecedores = {
        ops[0]["cnpj"][:8]: {"cnpj": cn[0], "lida_em": d, "desde": "2021-04-01", "total_ultima_consulta": 4, "itens": [
            _item(cn[0], 1, c1, "910001", m1[2], "11000000000191", 10, 1500.0, "Informado", "2026-02-10"),
            _item(cn[0], 2, c1, "910001", m1[2], "11000000000191", 1, 99.9, "Cancelado", "2026-02-10"),
            _item(cn[0], 1, c2, "910002", m2[2], "11000000000272", 2, 4000.25, "Informado", "2026-08-03"),
            _item(cn[0], 1, c3, "910001", m1[2], "11000000000191", 1, 250000.0, "Informado", "2025-11-20")]},
        ops[1]["cnpj"][:8]: {"cnpj": cn[1], "lida_em": d, "desde": "2021-04-01", "total_ultima_consulta": 1,
                             "itens": [_item(cn[1], 1, c4, "910003", m3[2], "11000000000434", 1, 777.0, "Informado", "2026-09-01")]},
        ops[2]["cnpj"][:8]: {"cnpj": cn[2], "lida_em": d, "desde": "2021-04-01", "total_ultima_consulta": 0, "itens": []},
        ops[3]["cnpj"][:8]: {"cnpj": cn[3], "lida_em": "2026-08-21", "desde": "2021-04-01", "total_ultima_consulta": 0, "itens": [], "herdado": True}}
    compras = {
        c1: {"orgao": "ORGAO FEDERAL SINTETICO", "org": "11000000000191", "esfera": "federal", "uf": m1[2], "ibge": m1[0], "municipio": m1[1], "modalidade": "Pregão - Eletrônico",
             "objeto": "Contratação de acesso à Internet (sintético)", "ano": 2026, "em": d},
        c2: {"orgao": "PREFEITURA SINTETICA", "org": "11000000000272", "esfera": "municipal", "uf": m2[2], "ibge": m2[0], "municipio": m2[1], "modalidade": "Dispensa",
             "objeto": "Link dedicado (sintético)", "ano": 2026, "em": d},
        c3: {"orgao": "ORGAO FEDERAL SINTETICO", "org": "11000000000191", "esfera": "federal", "uf": m1[2], "ibge": m1[0], "municipio": m1[1], "modalidade": "Pregão - Eletrônico",
             "objeto": "Rede de dados (sintético)", "ano": 2025, "em": d}}
    uasg = {"910001": {"nome": "UNIDADE SINTETICA 1", "uf": m1[2], "ibge": m1[0], "municipio": m1[1], "org": "11000000000191"},
            "910002": {"nome": "UNIDADE SINTETICA 2", "uf": m2[2], "ibge": m2[0], "municipio": m2[1], "org": "11000000000272"},
            "910003": {"nome": "UNIDADE SINTETICA 3", "uf": m3[2], "ibge": m3[0], "municipio": m3[1], "org": "11000000000434"}}
    faixas = {o["cnpj"][:8]: ("B" if i == 3 else "A") for i, o in enumerate(ops)}
    return {"snapshot_date": d, "fetched_at": f"{d}T00:00:00+00:00", "fonte": "https://dadosabertos.compras.gov.br", "api": "sintético", "licenca": "dados abertos (Lei 12.527/2011, LAI; PNCP, Lei 14.133/2021, art. 174); sem licença nominal publicada", "janela_inicio": "2021-04-01",
            "intervalos_dias": {"A": 7, "B": 56}, "faixas": faixas, "fornecedores": fornecedores, "compras": compras, "uasg": uasg, "uasg_em": d, "ultima_execucao": {}}
