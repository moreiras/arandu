# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Multas, faixas de frequência e satélites a partir de `regulatorio/{multas,faixas,satelites}.json.gz`. Cadastros e normas da Anatel; nada de pessoa física."""
from __future__ import annotations

from typing import Optional

from core.satelites import sistemas_ngeo

_META = ("natureza", "fonte", "data_arquivo", "limites", "snapshot_date")
ORDENS_MULTAS = ("saldo", "multas", "original", "pago")
CARATERES = ("Primário", "Secundário")


class RegulatorioErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


def _meta(doc: dict) -> dict:
    return {k: doc.get(k) for k in _META}


# ── multas ──────────────────────────────────────────────────────────────────

def multas_resumo(doc: dict) -> dict:
    return {**_meta(doc), "leitura": doc["leitura"], "brasil": doc["brasil"], "por_grupo": doc["por_grupo"], "por_ano": doc["por_ano"]}


def _linha_empresa(e: dict) -> dict:
    return {"raiz": e["raiz"], "cnpj_matriz": e["cnpj_matriz"], "entidade": e["entidade"], "grupo": e["grupo"], "uf": e["uf"], "multas": e["multas"], "original": e["original"], "pago": e["pago"],
            "saldo": e["saldo"], "situacoes": e["situacoes"], "primeiro_ano": min(e["anos"], default=None), "ultimo_ano": max(e["anos"], default=None)}


def linhas_multas(doc: Optional[dict]) -> list[dict]:
    """Uma linha por empresa e grupo (coleção `multas_empresa` do `/query`)."""
    return [_linha_empresa(e) for e in doc["empresas"]] if doc else []


def multas_empresas(doc: dict, grupo: Optional[str], q: Optional[str], ordem: str, limit: int, offset: int) -> dict:
    if ordem not in ORDENS_MULTAS:
        raise RegulatorioErro(400, f"ordem inválida: use {', '.join(ORDENS_MULTAS)}.")
    if grupo and grupo not in doc["por_grupo"]:
        raise RegulatorioErro(400, f"grupo inválido: use {', '.join(doc['por_grupo'])}.")
    linhas = linhas_multas(doc)
    if grupo:
        linhas = [x for x in linhas if x["grupo"] == grupo]
    if q:
        n = q.strip().lower()
        linhas = [x for x in linhas if n in x["entidade"].lower() or n in x["raiz"]]
    linhas.sort(key=lambda x: (-x[ordem], x["raiz"], x["grupo"]))
    return {**_meta(doc), "grupo": grupo, "ordem": ordem, "total": len(linhas), "limit": limit, "offset": offset, "items": linhas[offset:offset + limit]}


def bloco_operadora(doc: Optional[dict], cnpj: str) -> Optional[dict]:
    """Multas da operadora por raiz do CNPJ (`?include=multas`): `None` se o snapshot não as tem ou a empresa não aparece em SCM, SMP, STFC nem SeAC."""
    if not doc:
        return None
    mine = [_linha_empresa(e) for e in doc["empresas"] if e["raiz"] == cnpj[:8]]
    if not mine:
        return None
    soma = lambda c: round(sum(x[c] for x in mine), 2)      # noqa: E731
    return {**_meta(doc), "raiz": cnpj[:8], "multas": sum(x["multas"] for x in mine), "original": soma("original"), "pago": soma("pago"), "saldo": soma("saldo"), "por_grupo": mine,
            "brasil": {"empresas": doc["brasil"]["empresas"], "multas": doc["brasil"]["multas"], "saldo": doc["brasil"]["saldo"]}}


# ── faixas ──────────────────────────────────────────────────────────────────

def linhas_faixas(doc: Optional[dict]) -> list[dict]:
    """Uma linha por faixa (coleção `faixas_espectro` do `/query`)."""
    if not doc:
        return []
    return [{"ini_mhz": f["ini_mhz"], "fim_mhz": f["fim_mhz"], "largura_mhz": round(f["fim_mhz"] - f["ini_mhz"], 6),
             "destinacao": [d["servico"] for d in f["destinacao"] if d["carater"] == "Primário"], "destinacao_secundaria": [d["servico"] for d in f["destinacao"] if d["carater"] != "Primário"],
             "atribuicao": [a["servico"] for a in f["atribuicao"] if a["carater"] == "Primário"]} for f in doc["faixas"]]


def faixas(doc: dict, de: Optional[float], ate: Optional[float], servico: Optional[str], carater: Optional[str], limit: int, offset: int) -> dict:
    if carater and carater not in CARATERES:
        raise RegulatorioErro(400, f"carater inválido: use {', '.join(CARATERES)}.")
    if de is not None and ate is not None and ate < de:
        raise RegulatorioErro(400, "`ate` deve ser maior ou igual a `de`.")
    itens = doc["faixas"]
    if de is not None:
        itens = [f for f in itens if f["fim_mhz"] > de]
    if ate is not None:
        itens = [f for f in itens if f["ini_mhz"] < ate]
    if servico:
        n = servico.strip().lower()
        itens = [f for f in itens if any(n in d["servico"].lower() and (not carater or d["carater"] == carater) for d in f["destinacao"])]
    return {**_meta(doc), "de": de, "ate": ate, "servico": servico, "carater": carater, "total": len(itens), "limit": limit, "offset": offset, "items": itens[offset:offset + limit],
            "referencias": doc["referencias"] if not (de is not None or ate is not None or servico) else None}


def faixas_resumo(doc: dict) -> dict:
    return {**_meta(doc), "resumo": doc["resumo"], "referencias": doc["referencias"]}


# ── satélites ───────────────────────────────────────────────────────────────

def satelites_resumo(doc: dict) -> dict:
    """`ngeo` são os registros como a Anatel publica (um por sistema e ano de agenda); `ngeo_sistemas`, um por sistema. Snapshot gravado
    antes de `ngeo_sistemas` existir: agrupado aqui, dos mesmos registros (REGULATORIO-E1)."""
    sistemas = doc.get("ngeo_sistemas")
    if sistemas is None:
        sistemas = sistemas_ngeo(doc["ngeo"])
    resumo = {**doc["resumo"], "ngeo_sistemas": len(sistemas)}
    return {**_meta(doc), "resumo": resumo, "ngeo": doc["ngeo"], "ngeo_sistemas": sistemas, "operando": doc["operando"]}


def linhas_satelites(doc: Optional[dict]) -> list[dict]:
    """Um direito de exploração por linha (coleção `satelites_direitos` do `/query`)."""
    if not doc:
        return []
    return [{**x, "vencido": bool(x["validade"] and x["validade"] < (doc.get("snapshot_date") or ""))} for x in doc["direitos"]]


def satelites_direitos(doc: dict, operadora: Optional[str], tipo: Optional[str], status: Optional[str], limit: int, offset: int) -> dict:
    linhas = linhas_satelites(doc)
    tipos = sorted({x["tipo"] for x in linhas})
    if tipo and tipo not in tipos:
        raise RegulatorioErro(400, f"tipo inválido: use {', '.join(tipos)}.")
    if operadora:
        n = operadora.strip().lower()
        linhas = [x for x in linhas if n in x["operadora"].lower() or n in x["satelite"].lower()]
    if tipo:
        linhas = [x for x in linhas if x["tipo"] == tipo]
    if status:
        linhas = [x for x in linhas if x["status"].lower() == status.strip().lower()]
    return {**_meta(doc), "operadora": operadora, "tipo": tipo, "status": status, "total": len(linhas), "limit": limit, "offset": offset, "items": linhas[offset:offset + limit]}
