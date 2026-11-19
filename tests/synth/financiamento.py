# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Financiamento do BNDES e sanções da CGU no dataset sintético.

Só as três primeiras operadoras sintéticas têm dado: a 1ª com duas operações (matriz e filial) e uma sanção vigente sem prazo; a 2ª com uma operação e uma sanção já encerrada
mais uma multa do CNEP; a 3ª com só uma sanção que começa depois da data do snapshot. As demais não têm nada (é o caso comum)."""
from __future__ import annotations

from tests.synth import market
from tests.synth.world import World


def _op(cnpj_ctr: str, data: str, vc: float, vd: float, uf: str, ibge: str) -> dict:
    return {"contrato": cnpj_ctr, "data": data, "contratado": vc, "desembolsado": vd, "produto": "BNDES FINAME", "instrumento": "CREDITO", "forma": "DIRETA", "uf": uf, "ibge": ibge,
            "cnae": "J6110801", "porte": "PEQUENA", "situacao": "ATIVO", "projeto": "AMPLIACAO DA REDE DE FIBRA OPTICA"}


def _san(cad: str, cod: str, cat: str, ini: str, fim: str | None, orgao: str, uf: str, esfera: str, multa: float | None = None) -> dict:
    s = {"cadastro": cad, "codigo": cod, "categoria": cat, "inicio": ini, "fim": fim, "publicacao": ini, "abrangencia": "Em todos os Poderes da Esfera do órgão sancionador", "orgao": orgao,
         "uf_orgao": uf, "esfera": esfera, "fundamento": "LEI 8666 - ART. 87, III", "processo": f"P-{cod}"}
    if multa is not None:
        s["multa"] = multa
    return s


def bndes(world: World, d: str) -> dict:
    ops = market.operators(world)
    out = {}
    for i, op in enumerate(ops[:2]):
        c = op["cnpj"]
        out[c] = [_op(f"90000{i}1", "2022-03-10", 1500000.5, 1200000.0, "ES", "3205309")]
    c0 = ops[0]["cnpj"]
    out[c0[:8] + "000200"] = [_op("9000002", "2023-07-01", 800000.0, 0.0, "ES", "3205200")]
    return {"snapshot_date": d, "generated_at": f"{d}T00:00:00Z", "fonte": "BNDES — dados abertos (operações de financiamento, não automáticas)", "licenca": "ODbL", "dump_reference": "2026-10-24",
            "universo_cnpjs_basicos": len(ops), "linhas_lidas": 1000, "operacoes_guardadas": sum(len(v) for v in out.values()), "cnpjs": len(out), "operacoes": out}


def cgu(world: World, d: str) -> dict:
    ops = market.operators(world)
    out = {ops[0]["cnpj"]: [_san("CEIS", "810001", "Impedimento/proibição de contratar com prazo determinado", "2024-01-10", "2099-12-31", "Prefeitura Fictícia", "ES", "MUNICIPAL")],
           ops[1]["cnpj"]: [_san("CEIS", "810002", "Suspensão", "2019-02-01", "2021-02-01", "Órgão Fictício", "DF", "FEDERAL"),
                            _san("CNEP", "820001", "Multa", "2023-05-05", None, "Órgão Federal Fictício", "", "FEDERAL", 36680.49)],
           ops[2]["cnpj"]: [_san("CEIS", "810003", "Impedimento/proibição de contratar com prazo determinado", "2999-01-01", "2999-12-31", "Órgão Fictício", "ES", "ESTADUAL")]}
    return {"snapshot_date": d, "generated_at": f"{d}T00:00:00Z", "fonte": "CGU — Portal da Transparência (CEIS e CNEP)", "arquivos": {"CEIS": d, "CNEP": d}, "universo_cnpjs_basicos": len(ops),
            "linhas_lidas": 1000, "linhas_pessoa_juridica": 900, "sancoes_guardadas": sum(len(v) for v in out.values()), "cnpjs": len(out), "sancoes": out}
