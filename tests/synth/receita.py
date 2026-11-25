# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cadastro de telecom da Receita no dataset sintético.

Cada operadora sintética ganha uma matriz e uma filial. Os municípios do dataset são fictícios (códigos 99000xx) e não casam com o IBGE por nome, então as matrizes ficam em
Vitória (ES) e as filiais em Vila Velha (ES), que existem em `config/municipios-referencia.json`: é isso que exercita o casamento por nome e UF. Entram também dois
empresários individuais (um deles baixado), três empresas de telecom de outros anos para a série de mercado e uma loja de outro CNAE fora do recorte.
"""
from __future__ import annotations

from tests.synth import market
from tests.synth.world import World, make_cnpj

MUNICIPIOS_RFB = {"5701": "VITÓRIA", "5702": "VILA VELHA"}
CNAES = {"6110803": "Serviços de comunicação multimídia - SCM", "6190699": "Outras atividades de telecomunicações não especificadas anteriormente", "4321500": "Instalação e manutenção elétrica"}


def _est(cnpj: str, matriz: bool, sit: str, inicio: str, mun: str, cnae: str = "6110803", ds: str | None = None, fantasia: str | None = None) -> dict:
    e = {"c": cnpj, "m": 1 if matriz else 2, "s": sit, "d": inicio, "ds": ds, "u": "ES", "mu": mun, "p": cnae, "x": []}
    if fantasia:
        e["n"] = fantasia
    return e


def receita_cnpj(world: World, d: str) -> dict:
    estab: dict[str, list[dict]] = {}
    empresa: dict[str, dict] = {}
    simples: dict[str, dict] = {}
    for i, op in enumerate(market.operators(world)):
        raiz = op["cnpj"][:8]
        estab[raiz] = [_est(raiz + "0001" + op["cnpj"][-2:], True, "02", f"{2008 + i % 14}-0{1 + i % 9}-15", "5701", fantasia=op["nome_fantasia"]),
                       _est(raiz + "0002" + "00", False, "02" if i % 3 else "08", f"{2015 + i % 8}-03-01", "5702", cnae="4321500", ds=None if i % 3 else "2024-05-02")]
        empresa[raiz] = {"nat": "2054" if op.get("sociedade_anonima") else "2062", "capital": 10000.0 * (i + 1), "porte": ("01", "03", "05")[i % 3], "razao": op["razao_social"]}
        simples[raiz] = {"simples": bool(i % 2), "simples_in": "2018-01-01" if i % 2 else None, "simples_out": None, "mei": False, "mei_in": None, "mei_out": None}
    for k, (ano, sit, nat) in enumerate((("2019", "02", "2062"), ("2021", "02", "2062"), ("2021", "08", "2062"), ("2022", "02", "2135"), ("2023", "08", "2135"))):
        raiz = make_cnpj(900 + k)[:8]
        estab[raiz] = [_est(raiz + "000" + str(k) + "00", True, sit, f"{ano}-06-01", "5701", cnae="6190699", ds="2024-01-10" if sit == "08" else None, fantasia=None if nat == "2135" else f"Nova {k}")]
        empresa[raiz] = {"nat": nat, "capital": 1000.0, "porte": "01"} if nat == "2135" else {"nat": nat, "capital": 1000.0, "porte": "01", "razao": f"Nova Empresa {k} Ltda"}
        simples[raiz] = {"simples": True, "simples_in": f"{ano}-07-01", "simples_out": None, "mei": nat == "2135", "mei_in": f"{ano}-07-01" if nat == "2135" else None, "mei_out": None}
    return {"snapshot_date": d, "generated_at": f"{d}T00:00:00Z", "fonte": "Receita Federal — dados abertos do CNPJ", "dump_reference": "2026-09",
            "universo_cnpjs_basicos": len(market.operators(world)), "linhas_lidas": 1000, "estabelecimentos_guardados": sum(len(v) for v in estab.values()), "empresas": len(estab),
            "municipios_rfb": MUNICIPIOS_RFB, "naturezas": {"2054": "Sociedade Anônima Fechada", "2062": "Sociedade Empresária Limitada", "2135": "Empresário (Individual)"},
            "cnaes": CNAES, "empresa": empresa, "simples": simples, "estabelecimentos": estab}
