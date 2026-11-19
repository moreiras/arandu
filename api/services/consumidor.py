# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Reclamações no Consumidor.gov.br a partir de `consumidor/*.json.gz`.

Agregados com base mínima (o produto já suprime o que tem poucos casos) e **sem ranking**: as listas saem em ordem alfabética e nenhuma rota ordena por "melhor" ou "pior".
Reaproveita a ligação marca → CNPJ de `core/marcas.py` (a empresa chega ao produto já com `raizes` e `casamento`).
"""
from __future__ import annotations

from typing import Optional

_META = ("natureza", "fonte", "url_fonte", "limites", "minimos", "snapshot_date")


def _meta(doc: dict) -> dict:
    return {k: doc.get(k) for k in _META}


def uf_do_municipio(doc: Optional[dict], ibge: str) -> Optional[str]:
    return (doc or {}).get("municipios_uf", {}).get(ibge)


def resumo(doc: dict) -> dict:
    return {**_meta(doc), "janela": doc["janela"], "setor_por_mes": doc["setor_por_mes"], "casamento": doc["casamento"], "cidades": doc["cidades"], "leitura": doc["leitura"]}


def marcas(doc: dict, uf: Optional[str], q: Optional[str], com_cnpj: Optional[bool], limit: int, offset: int) -> dict:
    """Uma linha por empresa com os indicadores da janela (ou da UF, com `uf`). Ordem alfabética: não há ranking."""
    por_uf = {x["marca"]: x for x in doc["uf"] if uf and x["uf"] == uf.upper()}
    itens = []
    for x in doc["marcas"]:
        if uf and x["marca"] not in por_uf:
            continue
        base = por_uf[x["marca"]] if uf else x["janela"]
        if not base:
            continue
        itens.append({"marca": x["marca"], "raizes": x["raizes"], "cnpjs_matriz": x["cnpjs_matriz"], "casamento": x["casamento"], **{k: v for k, v in base.items() if k not in ("marca", "uf")}})
    if q:
        n = q.strip().lower()
        itens = [x for x in itens if n in x["marca"].lower()]
    if com_cnpj is not None:
        itens = [x for x in itens if bool(x["raizes"]) == com_cnpj]
    itens.sort(key=lambda x: x["marca"].lower())
    return {**_meta(doc), "janela": doc["janela"], "uf": uf.upper() if uf else None, "ordem": "empresa (alfabética; sem ranking)", "total": len(itens), "limit": limit, "offset": offset, "items": itens[offset:offset + limit]}


def linhas_marcas(doc: Optional[dict]) -> list[dict]:
    """Uma linha por empresa × mês (coleção `consumidor_marca` do `/query`)."""
    if not doc:
        return []
    return [{"marca": x["marca"], "raizes": x["raizes"], "casamento": x["casamento"], **m} for x in doc["marcas"] for m in x["por_mes"]]


def municipio(doc_uf: Optional[dict], ibge: str, meta_doc: Optional[dict]) -> Optional[dict]:
    if not doc_uf or ibge not in doc_uf["municipios"]:
        return None
    mun = doc_uf["municipios"][ibge]
    return {**_meta(meta_doc or doc_uf), "ibge": ibge, "nome": mun["nome"], "uf": mun["uf"], "populacao": mun.get("populacao"), "janela": doc_uf["janela"], "total": mun["total"], "itens": mun["itens"]}


def bloco_municipio(doc: Optional[dict], doc_uf: Optional[dict], ibge: str) -> Optional[dict]:
    return municipio(doc_uf, ibge, doc) if doc else None


def bloco_uf(doc: Optional[dict], uf: str) -> Optional[dict]:
    """Empresas com reclamações na UF (só células com a base mínima do produto), em ordem alfabética."""
    if not doc:
        return None
    linhas = sorted((x for x in doc["uf"] if x["uf"] == uf), key=lambda x: x["marca"].lower())
    if not linhas:
        return None
    casa = {x["marca"]: x for x in doc["marcas"]}
    return {**_meta(doc), "uf": uf, "janela": doc["janela"], "itens": [{**{k: v for k, v in x.items() if k != "uf"}, "raizes": casa[x["marca"]]["raizes"]} for x in linhas]}


def bloco_operadora(doc: Optional[dict], cnpj: str) -> Optional[dict]:
    """As empresas do Consumidor.gov.br ligadas à raiz do CNPJ (tabela curada ou nome fantasia único), com a série mensal e os assuntos; `None` se nenhuma casa."""
    if not doc:
        return None
    raiz = cnpj[:8]
    minhas = [x for x in doc["marcas"] if raiz in x["raizes"]]
    if not minhas:
        return None
    nomes = {x["marca"] for x in minhas}
    return {**_meta(doc), "raiz": raiz, "janela": doc["janela"], "marcas": [{k: x[k] for k in ("marca", "casamento", "base_casamento", "janela", "por_mes")} for x in sorted(minhas, key=lambda x: x["marca"].lower())],
            "assuntos": [x for x in doc["assuntos"] if x["marca"] in nomes], "grupos": [x for x in doc["grupos"] if x["marca"] in nomes],
            "setor_por_mes": doc["setor_por_mes"], "casamento_regra": doc["casamento"]["tabela_curada"]}
