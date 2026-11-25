# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Rejeições, communities e política de roteamento nos route servers do IX.br: blocos do PTT e do ASN, explorador de communities e linhas do `/query`.
Funções puras sobre `rs_policy/*.json.gz`.

É a **declaração** do membro por communities e a **decisão** do route server sobre as rotas dele, vistas pelo Alice-LG; não é tráfego nem relação comercial. O perfil
(aberto, seletivo, restritivo) é INFERIDO por heurística documentada (`parametros`) e só existe para quem teve as rotas recebidas coletadas (nível 3, rodízio dentro de um
orçamento de requisições): sem coleta não há perfil. Contagens são exatas sobre as rotas do vizinho; as amostras de prefixos são parciais. Nenhum contato aqui: só ASN, nome
do membro como rotulado no route server, prefixos públicos de roteamento e communities.
"""
from __future__ import annotations

from typing import Optional

LIMITES = ("Declaração por communities e decisão do route server no instante da coleta de cada vizinho (`coletado_de`, `coletado_ate`); não é tráfego nem relação comercial. "
           "O perfil é inferido por heurística (veja `parametros`) e só existe para quem teve as rotas recebidas coletadas: o nível 3 cobre alguns PTTs e uma parte dos membros por rodada "
           "(`cobertura`); sem coleta não há perfil, e ausência de rejeição ou de community não é prova de que o ASN não a tem. As amostras de prefixos são parciais; as contagens são exatas sobre as rotas do vizinho "
           "(`contagem: amostra` quando o Alice não trouxe a contagem). `forma: equivalente_padrao` = community padrão ou estendida lida como a grande equivalente do dicionário (assumido pela forma).")


def _meta(doc: dict) -> dict:
    return {"snapshot_date": doc["snapshot_date"], "coletado_nivel2": doc.get("coletado_nivel2"), "coletado_nivel3": doc.get("coletado_nivel3"),
            "cobertura_total_nivel2": doc.get("cobertura_total_nivel2"), "cobertura_total_nivel3": doc.get("cobertura_total_nivel3"), "rs_pulados": doc.get("rs_pulados"), "fonte": doc.get("fonte"),
            "versao_alice": doc.get("versao_alice"), "parametros": doc.get("parametros"), "limites": LIMITES}


def bloco_asn(doc: Optional[dict], asn: int, ixp: Optional[str] = None) -> Optional[dict]:
    """Rejeições e política do ASN em cada PTT coletado (`?ixp=` restringe a um PTT). None se não há nada do ASN (o ASN não foi coletado ou não tem rejeição)."""
    if not doc or str(asn) not in doc["asns"]:
        return None
    d = doc["asns"][str(asn)]
    ixps = {c: x for c, x in d["ixps"].items() if not ixp or c == ixp}
    if not ixps:
        return None
    out = {**_meta(doc), "asn": asn, **{k: v for k, v in d.items() if k != "ixps"}, "ixps": ixps}
    if ixp:
        out["evidencia_rs"] = out.get("evidencia_rs") if "rejeicoes" in ixps[ixp] else None
    return out


def bloco_ixp(doc: Optional[dict], code: str, limit: int = 50, offset: int = 0, motivo: Optional[str] = None) -> Optional[dict]:
    """Rejeições e política de um PTT. `rejeicoes.asns` vem paginado (SP tem centenas de ASNs com rota rejeitada); `motivo` mantém só os ASNs com aquele motivo."""
    if not doc or code not in doc["ixps"]:
        return None
    p = doc["ixps"][code]
    rej = p.get("rejeicoes")
    if rej:
        asns = [a for a in rej["asns"] if not motivo or motivo in a["motivos"]]
        rej = {**{k: v for k, v in rej.items() if k != "asns"}, "asns_total": len(asns), "asns": asns[offset:offset + limit], "asns_filtro": {"motivo": motivo} if motivo else None}
    return {**_meta(doc), "ixp": code, "nome": p["nome"], "rejeicoes": rej, "politica": p.get("politica")}


def _uso(e: dict, ixp: Optional[str]) -> dict:
    if not ixp:
        return e
    u = e["ixps"][ixp]
    return {**{k: v for k, v in e.items() if k not in ("ixps", "asns_total", "asns_soma_ptts", "ptts", "rotas_total")}, "asns_total": u["asns"], "asns_soma_ptts": u["asns"], "ptts": 1,
            "rotas_total": u["rotas"], "ixps": {ixp: u}}


def communities(doc: Optional[dict], q: Optional[str], ixp: Optional[str], classe: Optional[str], limit: int, offset: int) -> Optional[dict]:
    """Explorador de communities: as que aparecem nas rotas recebidas coletadas, com classe, rótulo e quem usa (por PTT). `q` casa a community (trecho), o rótulo ou, se for número, o ASN-alvo."""
    if not doc:
        return None
    nq = q.strip().lower() if q else None
    itens = []
    for e in doc["communities"]:
        if ixp and ixp not in e["ixps"]:
            continue
        if classe and e["classe"] != classe:
            continue
        if nq and not (nq in e["community"].lower() or nq in (e.get("rotulo") or "").lower() or (nq.isdigit() and e.get("alvo") == int(nq))):
            continue
        itens.append(_uso(e, ixp))
    if ixp:
        itens.sort(key=lambda e: (-e["asns_total"], -e["rotas_total"], e["community"]))
    por_classe: dict[str, int] = {}
    for e in itens:
        por_classe[e["classe"]] = por_classe.get(e["classe"], 0) + 1
    return {**_meta(doc), "filtros": {"q": q, "ixp": ixp, "classe": classe}, "total": len(itens), "por_classe": dict(sorted(por_classe.items())), "items": itens[offset:offset + limit]}


def uso_da_community(doc: Optional[dict], community: str, ixp: Optional[str] = None) -> Optional[dict]:
    """Uma community exata (MCP `ixp_communities`): classe, rótulo e quem a usa."""
    if not doc:
        return None
    for e in doc["communities"]:
        if e["community"] == community and (not ixp or ixp in e["ixps"]):
            return {**_meta(doc), **_uso(e, ixp)}
    return None


def linhas(doc: Optional[dict], colecao: str) -> list[dict]:
    """Linhas do `/query`: `rs_communities` (PTT × ASN × community) e `rs_filtradas` (PTT × ASN × motivo)."""
    return list((doc or {}).get(colecao) or [])
