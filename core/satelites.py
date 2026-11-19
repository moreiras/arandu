# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Satélites com direito de exploração no Brasil: direitos, constelações NGEO e satélites em operação comercial (dados abertos da Anatel).

São registros de **operadoras de satélite** (muitas estrangeiras, sem CNPJ brasileiro nos direitos); não cruzam com os grupos do SICI. Datas em `DD/MM/AAAA` viram `AAAA-MM-DD`.
"""
from __future__ import annotations

import csv
import io
import re
from typing import IO

DIREITOS = {"operadora": "Operadora (Operator)", "satelite": "Satélite (Satellite)", "codigo": "Código do Direito (Code)", "posicao": "Posição Orbital (Orbital slot)",
            "banda": "Banda do satélite exercendo o direito (Satellite Band)", "tipo": "Tipo de Direito (Type of landing right)", "status": "Status",
            "lancamento": "Data de lançamento (Launch date)", "validade": "Validade (Validity)", "prorrogado": "Direito prorrogado (Landing right postponed)"}
NGEO = {"cnpj": "NU_CNPJ", "prestadora": "NO_PRESTADORA", "lancamento": "DT_LANCAMENTO", "estacao": "SG_ESTACAO", "objeto": "NO_COMERCIAL_OBJETO", "status": "STATUS_OPERACAO",
        "orbita": "ORBITA_NGEO", "planos": "QT_PLANO_NGEO", "constelacao": "QT_CONSTELACAO_NGEO"}
OPERANDO = {"satelite": "Satélite em operação", "posicao": "Posição orbital", "bandas": "Bandas do satélite", "tipo": "Tipo de Direito", "operadora": "Operadora comercial"}


def _data(v: str) -> str | None:
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", (v or "").strip())
    return f"{m[3]}-{m[2]}-{m[1]}" if m else None


def _int(v: str) -> int | None:
    v = (v or "").strip()
    return int(v) if v.isdigit() else None


def _ler(csv_bytes: IO[bytes], mapa: dict[str, str], nome: str) -> list[dict]:
    leitor = csv.DictReader(io.TextIOWrapper(csv_bytes, encoding="utf-8-sig", newline=""), delimiter=";")
    faltam = [c for c in mapa.values() if c not in (leitor.fieldnames or [])]
    if faltam:
        raise RuntimeError(f"anatel_satelites: {nome}: colunas ausentes {faltam}; o leiaute mudou")
    return [{k: re.sub(r"\s+", " ", (r[c] or "")).strip() for k, c in mapa.items()} for r in leitor]


def consolidar(direitos: IO[bytes], ngeo: IO[bytes], operando: IO[bytes]) -> tuple[dict, dict]:
    d = _ler(direitos, DIREITOS, "direitos")
    for r in d:
        r["lancamento"], r["validade"] = _data(r["lancamento"]), _data(r["validade"])
        r["prorrogado"] = r["prorrogado"].upper().startswith("S")
    n = _ler(ngeo, NGEO, "constelações NGEO")
    for r in n:
        r["lancamento"] = _data(r["lancamento"])
        r["planos"], r["constelacao"] = _int(r["planos"]), _int(r["constelacao"])
        r["cnpj"] = re.sub(r"\D", "", r["cnpj"]) or None
    o = _ler(operando, OPERANDO, "em operação")
    return {"direitos": d, "ngeo": n, "operando": o}, {"direitos": len(d), "ngeo": len(n), "operando": len(o)}
