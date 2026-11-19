# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estações do SMP licenciadas a partir de `erbs/resumo.json.gz`: cadastro de licenciamento, não cobertura."""
from __future__ import annotations

from typing import Optional

GERACOES = ("2G", "3G", "4G", "5G")
_META = ("natureza", "fonte", "data_arquivo", "limites", "snapshot_date")


class ErbsErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


def _meta(doc: dict) -> dict:
    return {k: doc.get(k) for k in _META}


def _marcas(doc: dict) -> dict[str, str]:
    return {(o["cnpj"] or o["marca"]): o["marca"] for o in doc["operadoras"]}


def resumo(doc: dict, uf: Optional[str]) -> dict:
    if uf is None:
        return {**_meta(doc), "brasil": doc["brasil"], "ufs": doc["ufs"], "operadoras": doc["operadoras"], "casamento": doc["casamento"]}
    uf = uf.upper()
    if uf not in doc["ufs"]:
        raise ErbsErro(404, f"UF '{uf}' não encontrada.")
    return {**_meta(doc), "uf": uf, "resumo": doc["ufs"][uf], "brasil": doc["brasil"]}


def municipios(doc: dict, uf: Optional[str], geracao: Optional[str], ordem: str, limit: int, offset: int) -> dict:
    if geracao and geracao not in GERACOES:
        raise ErbsErro(400, f"geracao inválida: use {', '.join(GERACOES)}.")
    if ordem not in ("estacoes", "por_10mil_hab"):
        raise ErbsErro(400, "ordem inválida: use estacoes ou por_10mil_hab.")
    if uf and uf.upper() not in doc["ufs"]:
        raise ErbsErro(404, f"UF '{uf}' não encontrada.")
    linhas = _linhas(doc)
    if uf:
        linhas = [x for x in linhas if x["uf"] == uf.upper()]
    if geracao:
        linhas = [x for x in linhas if x[f"estacoes_{geracao.lower()}"] > 0]
    campo = f"estacoes_{geracao.lower()}" if geracao and ordem == "estacoes" else ordem
    linhas.sort(key=lambda x: (-(x.get(campo) or 0), x["ibge"]))
    return {**_meta(doc), "geracao": geracao, "uf": uf.upper() if uf else None, "ordem": campo, "total": len(linhas), "limit": limit, "offset": offset, "items": linhas[offset:offset + limit]}


def _linhas(doc: dict) -> list[dict]:
    marcas = _marcas(doc)
    out = []
    for ibge, m in doc["municipios"].items():
        top = next(iter(m["operadoras"]), None)
        out.append({"ibge": ibge, "nome": m.get("nome"), "uf": m.get("uf"), "estacoes": m["estacoes"], **{f"estacoes_{g.lower()}": m["geracoes"][g] for g in GERACOES},
                    "por_10mil_hab": m.get("por_10mil_hab"), "operadoras": len(m["operadoras"]), "operadora_principal": marcas.get(top, top) if top else None})
    return out


def linhas(doc: Optional[dict]) -> list[dict]:
    """Uma linha por município com estação (coleção `erbs_municipio` do `/query`)."""
    return _linhas(doc) if doc else []


def grade_geojson(doc: dict, geracao: Optional[str]) -> dict:
    """Células da grade como GeoJSON de pontos (centro da célula). Com `geracao`, só as células com estação naquela geração, contando só ela em `n`."""
    if geracao and geracao not in GERACOES:
        raise ErbsErro(400, f"geracao inválida: use {', '.join(GERACOES)}.")
    col = {"2G": 3, "3G": 4, "4G": 5, "5G": 6}.get(geracao or "", 2)
    feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [c[0], c[1]]},
              "properties": {"n": c[col], "estacoes": c[2], "g2": c[3], "g3": c[4], "g4": c[5], "g5": c[6]}} for c in doc["celulas"] if c[col] > 0]
    return {"type": "FeatureCollection", "features": feats, "snapshot_date": doc["snapshot_date"], "geracao": geracao, "passo_graus": doc["passo_graus"], "natureza": doc["natureza"],
            "limites": doc["limites"]}


def bloco_municipio(doc: Optional[dict], ibge: str, uf: Optional[str]) -> Optional[dict]:
    """O bloco `erbs` do perfil do município (`?include=erbs`): `None` se o snapshot não o tem. Município sem estação devolve zeros (é informação, não ausência)."""
    if not doc:
        return None
    m = doc["municipios"].get(ibge)
    marcas = _marcas(doc)
    ufr = doc["ufs"].get(uf or "")
    ops = [{"cnpj": k if k.isdigit() else None, "marca": marcas.get(k, k), "estacoes": n} for k, n in (m["operadoras"] if m else {}).items()]
    return {**_meta(doc), "estacoes": m["estacoes"] if m else 0, "geracoes": m["geracoes"] if m else dict.fromkeys(GERACOES, 0), "por_10mil_hab": m.get("por_10mil_hab") if m else None,
            "operadoras": ops, "uf": uf, "comparacao_uf": ufr, "brasil": doc["brasil"]}


def bloco_uf(doc: Optional[dict], uf: str) -> Optional[dict]:
    if not doc or uf not in doc["ufs"]:
        return None
    return resumo(doc, uf)


def bloco_operadora(doc: Optional[dict], cnpj: str) -> Optional[dict]:
    """Estações da operadora por CNPJ (`?include=erbs`): `None` se não há estação licenciada para o CNPJ."""
    if not doc:
        return None
    o = next((x for x in doc["operadoras"] if x["cnpj"] == cnpj), None)
    return {**_meta(doc), **o, "brasil": {"estacoes": doc["brasil"]["estacoes"], "municipios_com_estacao": doc["brasil"]["municipios_com_estacao"]}} if o else None
