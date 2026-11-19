# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""FUST a partir de `regulatorio/fust.json.gz`: compromissos registrados pela Anatel, por município, UF e programa. Sem operadora: o arquivo não a identifica."""
from __future__ import annotations

from typing import Optional

_META = ("natureza", "fonte", "data_arquivo", "limites", "snapshot_date")
ORDENS = ("compromissos", "investimento", "por_10mil_hab", "atendidos", "a_vencer", "em_apuracao")


class FustErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


def _meta(doc: dict) -> dict:
    return {k: doc.get(k) for k in _META}


def resumo(doc: dict, uf: Optional[str]) -> dict:
    if uf is None:
        return {**_meta(doc), "brasil": doc["brasil"], "ufs": doc["ufs"], "programas": doc["programas"], "editais": doc["editais"], "casamento": doc["casamento"]}
    uf = uf.upper()
    if uf not in doc["ufs"]:
        raise FustErro(404, f"UF '{uf}' não encontrada.")
    return {**_meta(doc), "uf": uf, "resumo": doc["ufs"][uf], "brasil": doc["brasil"]}


def _linhas(doc: dict) -> list[dict]:
    return [{"ibge": ibge, "nome": m.get("nome"), "uf": m.get("uf"), "compromissos": m["compromissos"], "atendidos": m["atendidos"], "a_vencer": m["a_vencer"], "em_apuracao": m["em_apuracao"],
             "investimento": m["investimento"], "por_10mil_hab": m.get("por_10mil_hab"), "programas": list(m["programas"])} for ibge, m in doc["municipios"].items()]


def linhas(doc: Optional[dict]) -> list[dict]:
    """Uma linha por município com compromisso (coleção `fust_municipio` do `/query`)."""
    return _linhas(doc) if doc else []


def municipios(doc: dict, uf: Optional[str], programa: Optional[str], ordem: str, limit: int, offset: int) -> dict:
    if ordem not in ORDENS:
        raise FustErro(400, f"ordem inválida: use {', '.join(ORDENS)}.")
    if uf and uf.upper() not in doc["ufs"]:
        raise FustErro(404, f"UF '{uf}' não encontrada.")
    if programa and programa not in {p["codigo"] for p in doc["programas"]}:
        raise FustErro(400, f"programa inválido: use um de {', '.join(p['codigo'] for p in doc['programas'])}.")
    linhas_ = _linhas(doc)
    if uf:
        linhas_ = [x for x in linhas_ if x["uf"] == uf.upper()]
    if programa:
        linhas_ = [x for x in linhas_ if programa in x["programas"]]
    linhas_.sort(key=lambda x: (-(x.get(ordem) or 0), x["ibge"]))
    return {**_meta(doc), "uf": uf.upper() if uf else None, "programa": programa, "ordem": ordem, "total": len(linhas_), "limit": limit, "offset": offset, "items": linhas_[offset:offset + limit]}


def bloco_municipio(doc: Optional[dict], ibge: str, uf: Optional[str]) -> Optional[dict]:
    """O bloco `fust` do perfil do município (`?include=fust`): `None` se o snapshot não o tem. Município sem compromisso devolve zeros (é informação, não ausência)."""
    if not doc:
        return None
    m = doc["municipios"].get(ibge)
    zero = {"compromissos": 0, "atendidos": 0, "a_vencer": 0, "em_apuracao": 0, "investimento": 0.0, "programas": {}, "tipos": {}}
    return {**_meta(doc), **(m or zero), "uf": uf, "comparacao_uf": doc["ufs"].get(uf or ""), "programas_nomes": {p["codigo"]: p["nome"] for p in doc["programas"]}}


def bloco_uf(doc: Optional[dict], uf: str) -> Optional[dict]:
    if not doc or uf not in doc["ufs"]:
        return None
    return {**resumo(doc, uf), "programas_nomes": {p["codigo"]: p["nome"] for p in doc["programas"]}}
