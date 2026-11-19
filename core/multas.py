# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Multas constituídas da Anatel, a partir de `multas_constituidas.csv` do pacote de arrecadação.

Só **pessoa jurídica** dos serviços de interesse (SCM, SMP, STFC e SeAC) é consolidada: o CPF já vem mascarado na fonte (`***.999.999-**`) e essas linhas são descartadas e contadas; serviços de
radiodifusão, radioamador, privados e linhas sem serviço (multas a quem não tem outorga) ficam fora e também são contados. A agregação é por raiz do CNPJ (8 dígitos: matriz e filiais) e
grupo de serviço. Multa constituída não é condenação definitiva: pode estar quitada, parcelada, suspensa judicialmente ou em recurso (a situação vem do arquivo).
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from collections import Counter, defaultdict
from typing import IO

COLUNAS = ("NU_CNPJ", "NO_ENTIDADE", "SG_UF", "AA_REFERENCIA", "DT_APLICACAO_SANCAO", "NO_SERVICO", "NO_SITUACAO_PAGAMENTO", "VR_ORIGINAL", "VR_PAGO", "VR_SALDO_DEVEDOR_ATUALIZADO")
SITUACOES = ("Quitado", "Devedor", "Parcial")
GRUPOS = ("SCM", "SMP", "STFC", "SeAC")


def _sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()


def grupo_servico(nome: str) -> str | None:
    """SCM, SMP, STFC ou SeAC; qualquer outro serviço (radiodifusão, privados, radioamador...) devolve None."""
    n = _sem_acento(nome)
    if "COMUNICACAO MULTIMIDIA" in n:
        return "SCM"
    if "MOVEL PESSOAL" in n:
        return "SMP"
    if "TELEFONICO FIXO COMUTADO" in n or n.startswith("STFC"):
        return "STFC"
    if "ACESSO CONDICIONADO" in n or "TV A CABO" in n or "MULTIPONTO" in n or "DTH" in n or "MMDS" in n:
        return "SeAC"
    return None


def _reais(v: str) -> float:
    v = re.sub(r"[^\d,.-]", "", v or "")
    if not v:
        return 0.0
    try:
        return float(v.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


def _ano(r: dict) -> int | None:
    for c in ("DT_APLICACAO_SANCAO", "AA_REFERENCIA"):
        m = re.match(r"(\d{4})", (r.get(c) or "").strip())
        if m:
            return int(m[1])
    return None


def consolidar(csv_bytes: IO[bytes]) -> tuple[list[dict], dict]:
    """Devolve `(empresas, resumo)`: uma linha por (raiz do CNPJ, grupo de serviço). Falha alto se faltar coluna."""
    leitor = csv.DictReader(io.TextIOWrapper(csv_bytes, encoding="utf-8-sig", newline=""), delimiter=";")
    faltam = [c for c in COLUNAS if c not in (leitor.fieldnames or [])]
    if faltam:
        raise RuntimeError(f"anatel_multas: colunas ausentes {faltam}; o leiaute mudou")
    acc: dict[tuple[str, str], dict] = {}
    linhas = pf = fora = sem_servico = situacao_nova = 0
    for r in leitor:
        linhas += 1
        digitos = re.sub(r"\D", "", r["NU_CNPJ"] or "")
        if "*" in (r["NU_CNPJ"] or "") or len(digitos) != 14:
            pf += 1
            continue
        servico = (r["NO_SERVICO"] or "").strip()
        grupo = grupo_servico(servico)
        if grupo is None:
            fora += 1
            sem_servico += not servico
            continue
        a = acc.setdefault((digitos[:8], grupo), {"raiz": digitos[:8], "grupo": grupo, "entidades": Counter(), "cnpjs": set(), "ufs": Counter(), "multas": 0, "original": 0.0, "pago": 0.0,
                                                   "saldo": 0.0, "situacoes": Counter(), "anos": Counter()})
        situacao = (r["NO_SITUACAO_PAGAMENTO"] or "").strip()
        situacao_nova += situacao not in SITUACOES
        a["entidades"][(r["NO_ENTIDADE"] or "").strip()] += 1
        a["cnpjs"].add(digitos)
        if r["SG_UF"]:
            a["ufs"][r["SG_UF"].strip().upper()] += 1
        a["multas"] += 1
        a["original"] += _reais(r["VR_ORIGINAL"])
        a["pago"] += _reais(r["VR_PAGO"])
        a["saldo"] += _reais(r["VR_SALDO_DEVEDOR_ATUALIZADO"])
        a["situacoes"][situacao] += 1
        ano = _ano(r)
        if ano:
            a["anos"][str(ano)] += 1
    empresas = [{"raiz": a["raiz"], "grupo": a["grupo"], "entidade": a["entidades"].most_common(1)[0][0], "cnpjs": sorted(a["cnpjs"]), "uf": a["ufs"].most_common(1)[0][0] if a["ufs"] else None,
                 "multas": a["multas"], "original": round(a["original"], 2), "pago": round(a["pago"], 2), "saldo": round(a["saldo"], 2), "situacoes": dict(a["situacoes"]),
                 "anos": dict(sorted(a["anos"].items()))} for a in acc.values()]
    empresas.sort(key=lambda e: (e["raiz"], e["grupo"]))
    return empresas, {"linhas": linhas, "pessoa_fisica": pf, "fora_do_escopo": fora, "sem_servico": sem_servico, "situacao_desconhecida": situacao_nova,
                      "empresas": len(empresas), "multas": sum(e["multas"] for e in empresas)}
