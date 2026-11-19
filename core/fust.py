# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""FUST: compromissos de aplicação dos recursos do Fundo de Universalização, a partir de `Base_FUST.csv` da Anatel.

Uma linha do arquivo é um compromisso (escola, unidade básica de saúde, favela, localidade ou município a atender), com programa, edital, investimento previsto, prazo e situação.
O arquivo **não traz a empresa executora**: a ligação com operadoras seria inferência e não é feita aqui. O município vem dos 7 primeiros dígitos de `COD_LOCALIDADE`
(código IBGE na malha indicada em `BASE`: IBGE_2010 ou IBGE_2022). Pessoas não aparecem; escola e unidade de saúde são estabelecimentos públicos.
"""
from __future__ import annotations

import csv
import io
import re
from collections import Counter
from typing import IO

COLUNAS = ("ID_LINHA", "ORIGEM", "TP_COMPROMISSO", "CO_PROGRAMA", "INVESTIMENTO_TOTAL", "NIVEL_OBRIGACAO", "BASE", "COD_LOCALIDADE", "UF", "MUNICIPIO", "STATUS", "PRAZO_MAXIMO")
STATUS = ("Atendido", "A vencer", "Em apuração")


def _num(v: str) -> float | None:
    v = (v or "").strip()
    if not v or v.upper() == "N/A":
        return None
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return None


def _prazo(v: str) -> str | None:
    """`DD/MM/AAAA` → `AAAA-MM-DD`; qualquer outra coisa vira None."""
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", (v or "").strip())
    return f"{m[3]}-{m[2]}-{m[1]}" if m else None


def _txt(v: str) -> str:
    return re.sub(r"\s+", " ", v or "").strip()


def consolidar(csv_bytes: IO[bytes]) -> tuple[list[dict], dict]:
    """Lê o CSV e devolve `(compromissos, resumo)`. Falha alto se faltar coluna: o leiaute mudou."""
    leitor = csv.DictReader(io.TextIOWrapper(csv_bytes, encoding="utf-8-sig", newline=""), delimiter=";")
    faltam = [c for c in COLUNAS if c not in (leitor.fieldnames or [])]
    if faltam:
        raise RuntimeError(f"anatel_fust: colunas ausentes {faltam}; o leiaute mudou")
    saida: list[dict] = []
    sem_ibge = sem_valor = status_novo = 0
    status_vistos: Counter = Counter()
    for r in leitor:
        cod = _txt(r["COD_LOCALIDADE"])
        ibge = cod[:7] if len(cod) >= 7 and cod[:7].isdigit() else None
        sem_ibge += ibge is None
        valor = _num(r["INVESTIMENTO_TOTAL"])
        sem_valor += valor is None
        status = _txt(r["STATUS"])
        status_vistos[status] += 1
        status_novo += status not in STATUS
        saida.append({"id": _txt(r["ID_LINHA"]), "origem": _txt(r["ORIGEM"]), "tipo": _txt(r["TP_COMPROMISSO"]), "programa": _txt(r["CO_PROGRAMA"]),
                      "nivel": _txt(r["NIVEL_OBRIGACAO"]), "base_ibge": _txt(r["BASE"]), "ibge": ibge, "uf": _txt(r["UF"]).upper() or None, "municipio": _txt(r["MUNICIPIO"]),
                      "status": status, "prazo": _prazo(r["PRAZO_MAXIMO"]), "investimento": valor})
    return saida, {"compromissos": len(saida), "sem_ibge": sem_ibge, "sem_investimento": sem_valor, "status": dict(status_vistos), "status_desconhecido": status_novo}
