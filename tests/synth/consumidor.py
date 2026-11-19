# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Consumidor.gov.br no dataset sintético.

O CSV sintético (leiaute real do `finalizadas_AAAA-MM.csv`, com sexo e faixa etária que o parser descarta) é lido por `core.consumidor`, então o normalizado sai igual ao de produção. As empresas
usam os apelidos da tabela curada sintética (`Alfa Fibra - Marca A`, `Beta Net`) e o nome fantasia das outorgas sintéticas (SEMASN1: casamento automático aceito, as reclamações caem na UF da
outorga; SEMASN2: nome único, mas as reclamações caem em outra UF e o casamento é descartado); `SEM DONO` e `OUTRA OPERADORA` ficam sem CNPJ. Três meses, para a série (a janela de 12 meses
cobre os três).
"""
from __future__ import annotations

import io

from core import consumidor as cg
from tests.synth.market import MUN
from tests.synth.world import World

MESES = ("2026-07", "2026-08", "2026-09")
_CAB = ("Região;UF;Cidade;Sexo;Faixa Etária;Data Finalização;Tempo Resposta;Nome Fantasia;Segmento de Mercado;Área;Assunto;Grupo Problema;Problema;Como Comprou Contratou;Procurou Empresa;"
        "Respondida;Situação;Avaliação Reclamação;Nota do Consumidor")
_TEL = "Operadoras de Telecomunicações (Telefonia, Internet, TV por assinatura)"
_SAUDE = "Operadoras de Planos de Saúde e Administradoras de Benefícios"
# (nome fantasia, município, reclamações por mês, assunto, grupo de problema)
_CELULAS = (
    ("Alfa Fibra - Marca A", "9900007", 40, "Internet Fixa", "Cobrança / Contestação"),
    ("Alfa Fibra - Marca A", "9900004", 12, "Internet Fixa", "Atendimento / SAC"),
    ("Alfa Fibra - Marca A", "9900005", 3, "Combo", "Vício de Qualidade"),         # 9 no trimestre: acima do mínimo de célula (5)
    ("Beta Net", "9900005", 14, "Internet Fixa", "Cobrança / Contestação"),
    ("Beta Net", "9900007", 1, "Internet Fixa", "Vício de Qualidade"),            # 3 no trimestre: abaixo do mínimo de célula
    ("SEMASN1", "9900004", 6, "Internet Fixa", "Vício de Qualidade"),
    ("SEMASN2", "9900007", 6, "Internet Fixa", "Cobrança / Contestação"),
    ("SEM DONO", "9900005", 4, "TV por Assinatura", "Atendimento / SAC"),
    ("OUTRA OPERADORA", "9900003", 2, "Internet Fixa", "Cobrança / Contestação"),
)


def _linhas(mes: str, deslocamento: int) -> list[str]:
    out: list[str] = []
    i = deslocamento
    for marca, ibge, q, assunto, grupo in _CELULAS:
        _, nome, uf, *_ = MUN[ibge]
        for _k in range(q):
            i += 1
            responde = i % 10 != 0
            av = ("Resolvida", "Não Resolvida", "Não Avaliada")[i % 3] if responde else "Não Avaliada"
            nota = (i % 5) + 1 if av != "Não Avaliada" else ""
            out.append(";".join(["SE", uf, nome, "F" if i % 2 else "M", "entre 31 a 40 anos", f"{mes}-02", str(3 + i % 8) if responde else "", marca, _TEL, "Telecomunicações", assunto, grupo, "x",
                                 "Internet", "S", "S" if responde else "N", "Finalizada avaliada" if av != "Não Avaliada" else "Finalizada não avaliada", av, str(nota)]))
    # um plano de saúde, que o parser descarta
    out.append(";".join(["SE", "SP", "Arandurápolis", "F", "entre 31 a 40 anos", f"{mes}-02", "5", "Saúde Alfa", _SAUDE, "Saúde", "Plano", "x", "x", "x", "S", "S", "x", "Resolvida", "5"]))
    return out


def consumidor_gov(world: World, d: str) -> dict:
    meses = {}
    for k, mes in enumerate(MESES):
        agg = cg.agregar_csv(io.BytesIO(("﻿" + _CAB + "\r\n" + "\r\n".join(_linhas(mes, 7 * k)) + "\r\n").encode("utf-8")))
        meses[mes] = {"codigo": f"2026{k:02d}0000000{k}", "tamanho": 1000 + k, **agg}
    resumo = {"meses": len(meses), "mes_inicial": MESES[0], "mes_final": MESES[-1], "baixados": len(meses), "reclamacoes_telecom": sum(m["resumo"]["telecom"] for m in meses.values())}
    return {"snapshot_date": d, "generated_at": "2026-01-01T00:00:00+00:00", "fonte": "sintético", "url": "https://consumidor.gov.br/pages/publicacao/externo/publicacoes.json", "meses": meses, "resumo": resumo}
