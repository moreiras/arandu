# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Consumidor.gov.br: agregação do arquivo mensal `finalizadas_AAAA-MM.csv`.

Cada linha do arquivo é UMA reclamação finalizada, com sexo e faixa etária de quem reclamou. Aqui a linha é lida em fluxo e **descartada**: só sobram contagens e somas por empresa
(nome fantasia) × UF × cidade, por empresa × assunto e por empresa × grupo de problema, nunca um campo de pessoa. Só entram empresas do segmento de operadoras de telecomunicações.

Definições (as do próprio Consumidor.gov.br, em "Indicadores"):
  * respondida: a empresa respondeu (coluna `Respondida` = S); `tempo_resposta` é em dias e vem vazio quando não houve resposta;
  * avaliada: o consumidor avaliou a resposta (`Avaliação Reclamação` = Resolvida ou Não Resolvida); só as avaliadas têm nota (1 a 5);
  * índice de solução = resolvidas ÷ avaliadas (não ÷ finalizadas: quem não avaliou não entra).
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from collections import defaultdict
from typing import IO

# O cabeçalho é comparado sem acento, em minúsculas e com `_`: até 2026-09 era "Nome Fantasia", e o arquivo de 2026-10 passou a "nome_fantasia" (e a data a dd/mm/aaaa, e Respondida a Sim/Não).
COLUNAS = ("uf", "cidade", "tempo_resposta", "nome_fantasia", "segmento_de_mercado", "assunto", "grupo_problema", "respondida", "avaliacao_reclamacao", "nota_do_consumidor")
RESOLVIDA, NAO_RESOLVIDA = "resolvida", "nao_resolvida"
CAMPOS_CELULA = ("n", "respondidas", "avaliadas", "resolvidas", "tempo_n", "tempo_soma", "nota_n", "nota_soma")


def _chave(s: str) -> str:
    """"Avaliação Reclamação" e "avaliacao_reclamacao" viram `avaliacao_reclamacao`."""
    t = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def segmento_telecom(segmento: str) -> bool:
    """`Operadoras de Telecomunicações (Telefonia, Internet, TV por assinatura)`; casa por prefixo para tolerar mudança do parêntese. Aparelhos (`Produtos de Telefonia`) são outro segmento."""
    s = segmento.strip().lower()
    return s.startswith("operadoras de telecomunica")


def _inteiro(s: str) -> int | None:
    s = s.strip()
    try:
        return int(s) if s else None
    except ValueError:
        return None


def agregar_csv(arq: IO[bytes]) -> dict:
    """Lê o CSV (UTF-8 com BOM, `;`) em fluxo e devolve `{"cidades": [...], "assuntos": [...], "grupos": [...], "resumo": {...}}`.

    `cidades`: `{marca, uf, cidade, n, respondidas, avaliadas, resolvidas, tempo_n, tempo_soma, nota_n, nota_soma}`; `assuntos`/`grupos`: `{marca, assunto|grupo, n}`.
    """
    leitor = csv.reader(io.TextIOWrapper(arq, encoding="utf-8-sig", newline=""), delimiter=";")
    cab = [_chave(c) for c in next(leitor)]
    faltam = [c for c in COLUNAS if c not in cab]
    if faltam:
        raise RuntimeError(f"consumidor_gov: colunas ausentes {faltam}; o leiaute mudou")
    ix = {c: cab.index(c) for c in COLUNAS}
    n_cols = len(cab)
    cel: dict[tuple, list] = defaultdict(lambda: [0] * len(CAMPOS_CELULA))
    ass: dict[tuple, int] = defaultdict(int)
    grp: dict[tuple, int] = defaultdict(int)
    linhas = telecom = 0
    segmentos: set[str] = set()
    for r in leitor:
        if len(r) < n_cols:
            continue
        linhas += 1
        seg = r[ix["segmento_de_mercado"]].strip()
        if not segmento_telecom(seg):
            continue
        segmentos.add(seg)
        telecom += 1
        marca = r[ix["nome_fantasia"]].strip()
        c = cel[(marca, r[ix["uf"]].strip().upper(), r[ix["cidade"]].strip())]
        c[0] += 1
        if r[ix["respondida"]].strip().upper() in ("S", "SIM"):
            c[1] += 1
        av = _chave(r[ix["avaliacao_reclamacao"]])
        if av in (RESOLVIDA, NAO_RESOLVIDA):
            c[2] += 1
            c[3] += av == RESOLVIDA
        t = _inteiro(r[ix["tempo_resposta"]])
        if t is not None and t >= 0:
            c[4] += 1
            c[5] += t
        nota = _inteiro(r[ix["nota_do_consumidor"]])
        if nota is not None and 1 <= nota <= 5:
            c[6] += 1
            c[7] += nota
        ass[(marca, r[ix["assunto"]].strip())] += 1
        grp[(marca, r[ix["grupo_problema"]].strip())] += 1
    return {
        "cidades": [dict(zip(("marca", "uf", "cidade") + CAMPOS_CELULA, (*k, *v))) for k, v in sorted(cel.items())],
        "assuntos": [{"marca": k[0], "assunto": k[1], "n": v} for k, v in sorted(ass.items())],
        "grupos": [{"marca": k[0], "grupo": k[1], "n": v} for k, v in sorted(grp.items())],
        "resumo": {"linhas": linhas, "telecom": telecom, "segmentos": sorted(segmentos), "marcas": len({k[0] for k in cel}), "celulas": len(cel)},
    }
