# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Quadro de atribuição e destinação de faixas de frequência (PDFF) da Anatel.

O pacote traz `Destinacao.csv` (serviços destinados à faixa no Brasil) e `Atribuicao_BR.csv` (serviços atribuídos). O `ID_FREQ` **não é único** (a mesma faixa numérica aparece em kHz e em MHz),
então a chave é o par (início, fim) em MHz, lido das colunas `*_MHz`. É o **quadro normativo**: diz para que serviços a faixa pode ser usada, não quem a explora nem se está em uso.
"""
from __future__ import annotations

import csv
import io
from collections import defaultdict
from typing import IO

COL_DEST = ("DEST.Freq_inicial_MHz", "DEST.Freq_final_MHz", "Serviço Destinado BR Exibição", "Caráter DEST")
COL_ATRIB = ("ATB_BR.Freq_inicial_MHz", "ATB_BR.Freq_final_MHz", "Serviço Atribuído BR Exibição", "Caráter BR")

# Faixas de interesse para a Internet, com o nome de referência do Arandurapé (não é nome oficial da Anatel).
REFERENCIAS = (
    ("700 MHz", 698.0, 806.0), ("850 MHz", 824.0, 894.0), ("900 MHz", 880.0, 960.0), ("1800 MHz", 1710.0, 1880.0), ("2100 MHz", 1920.0, 2170.0), ("2,3 GHz", 2300.0, 2400.0),
    ("Wi-Fi 2,4 GHz", 2400.0, 2483.5), ("2,5 GHz", 2500.0, 2690.0), ("3,5 GHz", 3300.0, 3700.0), ("Wi-Fi 5 GHz", 5150.0, 5850.0), ("Wi-Fi 6 GHz", 5925.0, 7125.0), ("26 GHz", 24250.0, 27500.0),
)


def _mhz(v: str) -> float | None:
    try:
        return float((v or "").strip().replace(",", "."))
    except ValueError:
        return None


def _ler(csv_bytes: IO[bytes], cols: tuple[str, str, str, str]) -> dict[tuple[float, float], list[dict]]:
    leitor = csv.DictReader(io.TextIOWrapper(csv_bytes, encoding="utf-8-sig", newline=""), delimiter=";")
    faltam = [c for c in cols if c not in (leitor.fieldnames or [])]
    if faltam:
        raise RuntimeError(f"anatel_pdff: colunas ausentes {faltam}; o leiaute mudou")
    out: dict[tuple[float, float], list[dict]] = defaultdict(list)
    for r in leitor:
        ini, fim = _mhz(r[cols[0]]), _mhz(r[cols[1]])
        if ini is None or fim is None:
            continue
        servico = (r[cols[2]] or "").strip()
        if servico:
            out[(ini, fim)].append({"servico": servico, "carater": (r[cols[3]] or "").strip()})
    return out


def consolidar(destinacao: IO[bytes], atribuicao: IO[bytes]) -> tuple[list[dict], dict]:
    """Devolve `(faixas, resumo)`: uma linha por faixa (MHz) com serviços destinados e atribuídos."""
    dest, atrib = _ler(destinacao, COL_DEST), _ler(atribuicao, COL_ATRIB)
    faixas = []
    for chave in sorted(set(dest) | set(atrib)):
        faixas.append({"ini_mhz": chave[0], "fim_mhz": chave[1], "destinacao": dest.get(chave, []), "atribuicao": atrib.get(chave, [])})
    return faixas, {"faixas": len(faixas), "com_destinacao": sum(1 for f in faixas if f["destinacao"]), "com_atribuicao": sum(1 for f in faixas if f["atribuicao"])}
