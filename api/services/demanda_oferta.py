# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Demanda × oferta de banda larga fixa a partir de `mercado/demanda_oferta.json.gz`."""
from __future__ import annotations

from typing import Optional

from core.cetic_microdados import REGIOES_UF


class DemandaOfertaErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


_META = ("natureza", "fonte", "tic_edicao", "mes_referencia_sici", "pnad_ano", "intervalo", "formulas", "limites", "snapshot_date")


def _meta(doc: dict) -> dict:
    return {k: doc.get(k) for k in _META}


def resposta(doc: dict, uf: Optional[str]) -> dict:
    if uf is None:
        return {**_meta(doc), "brasil": doc["brasil"], "regioes": doc["regioes"], "ufs": doc["ufs"]}
    uf = uf.upper()
    if uf not in doc["ufs"]:
        raise DemandaOfertaErro(404, f"UF '{uf}' não encontrada.")
    reg = REGIOES_UF.get(uf)
    return {**_meta(doc), "uf": uf, "regiao": reg, "demanda_oferta": doc["ufs"][uf], "comparacao": {"regiao": doc["regioes"].get(reg), "brasil": doc["brasil"]}}


def linhas(doc: Optional[dict]) -> list[dict]:
    """Uma linha por UF, região e Brasil (coleção `demanda_oferta` do `/query`)."""
    if not doc:
        return []
    comuns = {"tic_edicao": doc.get("tic_edicao"), "mes_referencia_sici": doc.get("mes_referencia_sici")}
    out = [{"grupo": "BR", "tipo": "brasil", "uf": None, **doc["brasil"], **comuns}]
    out += [{"grupo": r, "tipo": "regiao", "uf": None, **v, **comuns} for r, v in doc["regioes"].items()]
    out += [{"grupo": u, "tipo": "uf", "uf": u, **v, **comuns} for u, v in doc["ufs"].items()]
    return out


def bloco_uf(doc: Optional[dict], uf: str) -> Optional[dict]:
    """O bloco `demanda_oferta` do perfil da UF (`?include=cetic`): `None` se o snapshot não o tem."""
    if not doc or uf not in doc["ufs"]:
        return None
    return resposta(doc, uf)
