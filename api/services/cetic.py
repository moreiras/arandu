# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Consultas às tabelas oficiais das pesquisas TIC do Cetic.br.

Os valores são do Cetic.br, sem alteração: estimativas amostrais com margem de erro. A resposta sempre traz edição, citação e licença (CC BY 4.0).
"""
from __future__ import annotations

from typing import Optional

from api.repos.cetic import REGIOES_UF
from core.site import SITE


class CeticErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


AVISO = ("Estimativas amostrais publicadas pelo Cetic.br|NIC.br (não são contagens): a margem de erro acompanha cada valor. O recorte mais fino das tabelas públicas é a "
         f"grande região; resultados por UF vêm dos microdados e são do {SITE.nome}, rotulados à parte.")


def _meta(doc: dict) -> dict:
    return {"pesquisa": doc["pesquisa"], "edicao": doc["edicao"], "fonte": doc["fonte"], "licenca": doc["licenca"], "pagina": doc["pagina"], "coletado_em": doc.get("coletado_em"),
            "snapshot_date": doc["snapshot_date"], "aviso": AVISO}


def tabelas(doc: dict) -> dict:
    itens = [{"tabela": k, "codigo": v["codigo"], "titulo": v["titulo"], "universo": v["universo"], "notas": v["notas"]} for k, v in doc["tabelas"].items()]
    return {**_meta(doc), "total": len(itens), "items": itens}


def indicadores(doc: dict, tabela: Optional[str], dimensao: Optional[str], recorte: Optional[str], item: Optional[str], resposta: Optional[str],
                limit: int, offset: int) -> dict:
    if tabela and tabela not in doc["tabelas"]:
        raise CeticErro(404, f"Tabela '{tabela}' não existe na {doc['pesquisa']} {doc['edicao']}. Veja /cetic/tabelas.")

    def casa(valor: str, filtro: Optional[str]) -> bool:
        return filtro is None or filtro.strip().lower() in valor.lower()

    achadas = [l for l in doc["linhas"] if (not tabela or l["tabela"] == tabela) and casa(l["dimensao"], dimensao) and casa(l["recorte"], recorte)
               and casa(l["item"], item) and casa(l["resposta"], resposta)]
    meta = doc["tabelas"]
    itens = [{**l, "titulo_tabela": meta[l["tabela"]]["titulo"]} for l in achadas[offset:offset + limit]]
    return {**_meta(doc), "filtros": {"tabela": tabela, "dimensao": dimensao, "recorte": recorte, "item": item, "resposta": resposta}, "total": len(achadas), "items": itens}


def linhas(docs: list[dict]) -> list[dict]:
    """Uma linha por tabela × recorte × item × resposta (coleção `cetic_indicadores` do `/query`), das duas pesquisas."""
    out = []
    for doc in docs:
        chave = "domicilios" if "Domic" in doc["pesquisa"] else "provedores"
        for l in doc["linhas"]:
            out.append({"pesquisa": chave, "edicao": doc["edicao"], "tabela": l["tabela"], "titulo_tabela": doc["tabelas"][l["tabela"]]["titulo"],
                        "universo": doc["tabelas"][l["tabela"]]["universo"], **{k: l[k] for k in ("dimensao", "recorte", "item", "resposta", "proporcao", "margem_proporcao", "total", "margem_total")}})
    return out


AVISO_UF = (f"Estimativa do {SITE.nome} calculada dos microdados públicos da TIC Domicílios (Cetic.br|NIC.br), não é número publicado pelo Cetic.br. A margem de erro (95%) vem dos 200 pesos "
            "de réplica da base e é menor que a das tabelas oficiais (a oficial é de 1,08 a 1,14 vez a daqui, ver `validacao`); por UF a amostra é de 700 a 1.500 domicílios. "
            "Grupo com menos de 30 entrevistados é suprimido.")


def _meta_uf(doc: dict) -> dict:
    return {"natureza": doc["natureza"], "pesquisa": doc["pesquisa"], "edicao": doc["edicao"], "fonte": doc["fonte"], "licenca": doc["licenca"], "pagina": doc["pagina"],
            "coletado_em": doc.get("coletado_em"), "snapshot_date": doc["snapshot_date"], "metodo": doc["metodo"], "validacao": doc.get("validacao"), "indicadores": doc["indicadores"],
            "aviso": AVISO_UF}


def estimativas(doc: dict, tipo: Optional[str], indicador: Optional[str]) -> dict:
    if tipo and tipo not in ("brasil", "regiao", "uf"):
        raise CeticErro(400, "tipo inválido: use brasil, regiao ou uf.")
    if indicador and indicador not in doc["indicadores"]:
        raise CeticErro(400, f"indicador inválido: {indicador}. Use: {', '.join(doc['indicadores'])}.")
    itens = []
    for nome, g in doc["grupos"].items():
        if tipo and g["tipo"] != tipo:
            continue
        inds = {k: v for k, v in g["indicadores"].items() if not indicador or k == indicador}
        itens.append({"grupo": nome, "tipo": g["tipo"], "n": g["n"], "domicilios": g["domicilios"], "indicadores": inds})
    return {**_meta_uf(doc), "total": len(itens), "items": itens}


def estimativas_uf(doc: dict, uf: str) -> dict:
    uf = uf.upper()
    g = doc["grupos"].get(uf)
    if not g or g["tipo"] != "uf":
        raise CeticErro(404, f"UF '{uf}' não encontrada.")
    reg = doc["grupos"].get(REGIOES_UF.get(uf, ""))
    return {**_meta_uf(doc), "uf": uf, "regiao": REGIOES_UF.get(uf), "estimativas": g, "comparacao": {"regiao": reg, "brasil": doc["grupos"].get("BR")}}


def linhas_uf(doc: Optional[dict]) -> list[dict]:
    """Uma linha por grupo × indicador (coleção `cetic_estimativas_uf` do `/query`)."""
    if not doc:
        return []
    out = []
    for nome, g in doc["grupos"].items():
        for i, e in g["indicadores"].items():
            out.append({"grupo": nome, "tipo": g["tipo"], "uf": nome if g["tipo"] == "uf" else None, "indicador": i, "rotulo": doc["indicadores"][i]["rotulo"], "edicao": doc["edicao"],
                        "n": g["n"], "proporcao": e.get("proporcao"), "erro_padrao": e.get("erro_padrao"), "margem": e.get("margem"), "cv": e.get("cv"), "total": e.get("total"),
                        "precisao": e.get("precisao"), "suprimido": e.get("suprimido")})
    return out


def bloco_uf(doc: Optional[dict], uf: str) -> Optional[dict]:
    """O bloco `cetic` do perfil da UF (`?include=cetic`): `None` se o snapshot não tem as estimativas."""
    if not doc or uf not in doc["grupos"]:
        return None
    return estimativas_uf(doc, uf)
