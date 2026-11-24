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
# colunas do NGEO lidas quando existem (o CSV de 2026-11 tem; o leiaute anterior não): a tabela tem uma linha por sistema e por ano de agenda
# de exploração (`AGENDA_EE_ANO`, com `DT_AGENDA_EE` = 01/01 do ano), e `NU_ESTACAO` identifica o sistema
NGEO_OPCIONAIS = {"agenda_ano": "AGENDA_EE_ANO", "nu_estacao": "NU_ESTACAO"}
OPERANDO = {"satelite": "Satélite em operação", "posicao": "Posição orbital", "bandas": "Bandas do satélite", "tipo": "Tipo de Direito", "operadora": "Operadora comercial"}


def _data(v: str) -> str | None:
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", (v or "").strip())
    return f"{m[3]}-{m[2]}-{m[1]}" if m else None


def _int(v: str) -> int | None:
    v = (v or "").strip()
    return int(v) if v.isdigit() else None


def _ler(csv_bytes: IO[bytes], mapa: dict[str, str], nome: str, opcionais: dict[str, str] | None = None) -> list[dict]:
    leitor = csv.DictReader(io.TextIOWrapper(csv_bytes, encoding="utf-8-sig", newline=""), delimiter=";")
    faltam = [c for c in mapa.values() if c not in (leitor.fieldnames or [])]
    if faltam:
        raise RuntimeError(f"anatel_satelites: {nome}: colunas ausentes {faltam}; o leiaute mudou")
    mapa = {**mapa, **{k: c for k, c in (opcionais or {}).items() if c in (leitor.fieldnames or [])}}
    return [{k: re.sub(r"\s+", " ", (r[c] or "")).strip() for k, c in mapa.items()} for r in leitor]


def sem_copias(linhas: list[dict]) -> list[dict]:
    """Remove as linhas idênticas em todos os campos lidos (a origem repete linhas: Omnispace F2 sete vezes no mesmo ano), mantendo a ordem."""
    vistos, out = set(), []
    for r in linhas:
        chave = tuple(sorted(r.items()))
        if chave not in vistos:
            vistos.add(chave)
            out.append(r)
    return out


def sistemas_ngeo(linhas: list[dict]) -> list[dict]:
    """Uma linha por sistema NGEO a partir dos registros (um por ano de agenda e cópias). Sistema = `nu_estacao` quando existe, senão o nome
    comercial (`objeto`). Os campos descritivos vêm do registro corrente (maior `agenda_ano`; sem ele, o último na ordem da origem); a
    quantidade de satélites declarada vai como faixa (`constelacao_min` a `constelacao_max`) com `registros` e `anos_agenda` (REGULATORIO-E1)."""
    grupos: dict[str, list[dict]] = {}
    for r in sem_copias(linhas):
        grupos.setdefault(r.get("nu_estacao") or r.get("objeto") or "", []).append(r)
    out = []
    for regs in grupos.values():
        atual = max(enumerate(regs), key=lambda ir: (_int(str(ir[1].get("agenda_ano") or "")) or 0, ir[0]))[1]
        qts = [r["constelacao"] for r in regs if r.get("constelacao") is not None]
        anos = sorted({a for r in regs if (a := _int(str(r.get("agenda_ano") or ""))) is not None})
        out.append({**{k: atual.get(k) for k in ("cnpj", "prestadora", "lancamento", "estacao", "objeto", "status", "orbita", "planos", "constelacao")},
                    "registros": len(regs), "anos_agenda": anos, "constelacao_min": min(qts) if qts else None, "constelacao_max": max(qts) if qts else None})
    return sorted(out, key=lambda x: (x["objeto"] or "").lower())


def consolidar(direitos: IO[bytes], ngeo: IO[bytes], operando: IO[bytes]) -> tuple[dict, dict]:
    d = _ler(direitos, DIREITOS, "direitos")
    for r in d:
        r["lancamento"], r["validade"] = _data(r["lancamento"]), _data(r["validade"])
        r["prorrogado"] = r["prorrogado"].upper().startswith("S")
    n = _ler(ngeo, NGEO, "constelações NGEO", NGEO_OPCIONAIS)
    for r in n:
        r["lancamento"] = _data(r["lancamento"])
        r["planos"], r["constelacao"] = _int(r["planos"]), _int(r["constelacao"])
        r["cnpj"] = re.sub(r"\D", "", r["cnpj"]) or None
        if "agenda_ano" in r:
            r["agenda_ano"] = _int(r["agenda_ano"])
    n = sem_copias(n)                        # cópias exatas da origem (29 no CSV de 2026-11)
    o = _ler(operando, OPERANDO, "em operação")
    return {"direitos": d, "ngeo": n, "operando": o}, {"direitos": len(d), "ngeo": len(n), "operando": len(o)}
