# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Área de influência observada dos PTTs, a partir de `territorio/area_influencia_ptt.json.gz`: recortes por PTT e nacional por município.

Só leitura do artefato publicado (nada é calculado na hora). Não traz nome de operadora, só contagens."""
from __future__ import annotations

from typing import Optional

VISOES = ("diretos", "todos")                       # as do índice nacional por município
VISOES_ALCANCE = ("alcance_diretos", "alcance_todos")      # só por PTT, sem disputa entre PTTs
VISOES_PTT = VISOES + VISOES_ALCANCE
ROTULOS_VISAO = {"diretos": "Só diretamente conectados", "todos": "Todos que anunciam no PTT"}
ROTULOS_VISAO_PTT = {**ROTULOS_VISAO, "alcance_diretos": "Alcance dos diretamente conectados", "alcance_todos": "Alcance de todos que anunciam"}
# campos de `visoes[v]` que o resumo nacional repete por PTT (sem a lista de municípios)
_RESUMO = ("operadoras", "municipios", "acessos", "p50_km", "p80_km", "p90_km", "mediana_operadora_km", "faixas")


def _meta(doc: dict) -> dict:
    return {"snapshot_date": doc["snapshot_date"], "natureza": doc["natureza"], "limites": doc["limites"], "metodo": doc["metodo"], "fontes": doc["fontes"], "faixas": doc["faixas"]}


def _ponto(pontos: list) -> Optional[list]:
    """[lat, lon] médio dos PIX do PTT (referência para o mapa nacional, que não repete todos os pontos)."""
    return [round(sum(p[0] for p in pontos) / len(pontos), 3), round(sum(p[1] for p in pontos) / len(pontos), 3)] if pontos else None


def por_ptt(doc: dict, code: str, visao: Optional[str] = None) -> Optional[dict]:
    """As quatro visões (ou a pedida) de um PTT, com o posicionamento dos PIX. `None` se o PTT não consta no artefato."""
    p = (doc.get("ptts") or {}).get(code)
    if p is None:
        return None
    visoes = {v: p["visoes"].get(v) for v in VISOES_PTT if visao in (None, v)}
    nomes_doc = doc.get("municipios_nomes") or {}
    nomes = {i: nomes_doc[i] for x in visoes.values() if x for i in x["municipios_faixa"] if i in nomes_doc}
    return {**_meta(doc), "ixp": code, "nome": p["nome"], "uf": p["uf"], "pix": p["pix"], "totais": {v: doc["totais"][v] for v in visoes if v in doc["totais"]}, "visoes": visoes, "municipios_nomes": nomes}


def nacional(doc: dict, visao: str) -> dict:
    """Uma visão no país: por município (PTT principal, faixa nele, acessos) e o resumo de cada PTT, sem as listas de municípios."""
    ptts = {c: {"nome": p["nome"], "uf": p["uf"], "pix_aproximado": p["pix"]["aproximado"], "ponto": _ponto(p["pix"]["pontos"]), **{k: p["visoes"][visao][k] for k in _RESUMO}}
            for c, p in sorted(doc["ptts"].items()) if p["visoes"].get(visao)}
    return {**_meta(doc), "visao": visao, "rotulo_visao": ROTULOS_VISAO[visao], "campos_municipio": ["ptt_principal", "faixa", "acessos_principal", "acessos_municipio", "ptts"],
            "total": doc["totais"][visao], "ptts_com_pix_aproximado": doc["ptts_com_pix_aproximado"], "ptts": ptts, "municipios": doc["municipios"][visao]}
