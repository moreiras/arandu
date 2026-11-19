# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Route servers do IX.br: blocos do PTT e do ASN, ranking e tabela do `/query`. Funções puras sobre `route_servers/*.json.gz`.

São fatos medidos no route server na data da coleta (`coletado_em`), sem causa nem veredito (política editorial): o motivo de uma queda é o que o Alice reporta,
"cadastrado sem sessão" pode ser peering bilateral e a sessão de um route server sem frescor confirmado vem marcada `rs_incerto` (cache de vizinhos com mais de 24 h, sem `cached_at` ou consulta que falhou). O READY/BUSY/ERROR do Alice é o do cache de rotas e não entra nesse critério.
"""
from __future__ import annotations

from typing import Optional

CRITERIOS = {
    "sessoes_down": "sessões down em route servers com vizinhos atuais (número absoluto), com o total de sessões do membro ao lado",
    "dias_down": "maior tempo de queda, em dias, de uma sessão em route server com vizinhos atuais",
    "uso_limite": "maior uso do limite de importação entre as sessões up (rotas recebidas ÷ import_limit)",
    "sessoes": "sessões do membro no PTT",
}


class RouteServersErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


def _meta(doc: dict) -> dict:
    return {"snapshot_date": doc["snapshot_date"], "coletado_em": doc.get("coletado_em"), "fonte": doc.get("fonte"), "versao_alice": doc.get("versao_alice"),
            "parametros": {"dias_down": doc.get("dias_down"), "uso_limite": doc.get("uso_limite"), "idade_max_vizinhos_h": doc.get("idade_max_vizinhos_h")},
            "limites": ("Estado do route server no instante da coleta. Sessão down não diz de quem é a causa; cadastrado sem sessão pode ser peering bilateral; "
                        "sessão em route server sem frescor confirmado (cache de vizinhos com mais de 24 h ou sem consulta) vem marcada rs_incerto e não conta como membro down. O READY, BUSY ou ERROR do "
                        "Alice é o do cache de rotas e não diz nada das sessões.")}


def _destaque(m: dict) -> bool:
    return bool(m.get("membro_down") or m.get("perto_do_limite") or m.get("cadastrado_sem_sessao") or (m.get("sessoes") and not m.get("cadastrado")))


def bloco_ixp(doc: Optional[dict], code: str, todos: bool = False) -> Optional[dict]:
    """Bloco `route_servers` do perfil do PTT (`include=route_servers`); None se o produto não foi publicado ou o PTT não tem route server.
    Por padrão `membros` traz só os que têm algo a dizer (membro down, perto do limite, cadastrado sem sessão, sessão sem cadastro): o PTT de
    São Paulo tem milhares de membros e a lista inteira pesa ~0,5 MB. `todos=True` devolve todos; o `resumo` é sempre do PTT inteiro."""
    if not doc or code not in doc["ixps"]:
        return None
    p = doc["ixps"][code]
    membros = p["membros"] if todos else [m for m in p["membros"] if _destaque(m)]
    return {**_meta(doc), **{k: v for k, v in p.items() if k != "membros"}, "membros_listados": "todos" if todos else "destaque", "membros_total": len(p["membros"]), "membros": membros}


def bloco_asn(doc: Optional[dict], asn: int) -> Optional[dict]:
    if not doc or str(asn) not in doc["asns"]:
        return None
    return {**_meta(doc), **doc["asns"][str(asn)]}


def ranking(doc_ixps: dict, criterio: str, ixp: Optional[str], apenas_down: bool, limit: int, offset: int) -> dict:
    """Membros (ASN × PTT) ordenados por `criterio`, em ordem decrescente; empate pelo ASN. Só números medidos, sem adjetivo."""
    if criterio not in CRITERIOS:
        raise RouteServersErro(400, f"criterio inválido: {criterio}. Use: {', '.join(CRITERIOS)}")
    ixp = ixp.lower() if ixp else None
    if ixp and ixp not in doc_ixps["ixps"]:
        raise RouteServersErro(404, f"PTT '{ixp}' sem route server publicado.")
    chave = {"sessoes_down": "down_certo", "dias_down": "max_dias_down", "uso_limite": "max_uso_limite", "sessoes": "sessoes"}[criterio]
    linhas = []
    for code, p in doc_ixps["ixps"].items():
        if ixp and code != ixp:
            continue
        for m in p["membros"]:
            if not m.get("sessoes") or m.get(chave) in (None, 0) or (apenas_down and not m.get("membro_down")):
                continue
            linhas.append({"ixp": code, "asn": m["asn"], "nome": m.get("nome"), "sessoes": m["sessoes"], "up": m["up"], "down": m["down"], "down_certo": m["down_certo"],
                           "max_dias_down": m.get("max_dias_down"), "max_uso_limite": m.get("max_uso_limite"), "membro_down": m["membro_down"],
                           "rs_incerto": m.get("rs_incerto", 0)})
    linhas.sort(key=lambda r: (-(r[chave] or 0), r["ixp"], r["asn"]))
    itens = [{"posicao": offset + i + 1, **r} for i, r in enumerate(linhas[offset:offset + limit])]
    return {**_meta(doc_ixps), "criterio": CRITERIOS[criterio] + " (decrescente)", "escopo": {"ixp": ixp} if ixp else {"pais": "BR"},
            "filtros": {"apenas_down": apenas_down}, "total": len(linhas), "items": itens}


def linhas(doc_asns: Optional[dict], doc_ixps: Optional[dict]) -> list[dict]:
    """Uma linha por sessão (coleção `rs_sessoes` do `/query`), com o nome do membro no PTT quando há cadastro."""
    if not doc_asns:
        return []
    nomes = {(c, m["asn"]): m.get("nome") for c, p in ((doc_ixps or {}).get("ixps") or {}).items() for m in p["membros"]}
    out = []
    for a, d in doc_asns["asns"].items():
        for code, x in d["ixps"].items():
            for s in x["lista"]:
                out.append({"ixp": code, "asn": int(a), "nome": nomes.get((code, int(a))), "cadastrado": x["cadastrado"], "rs": s["rs"], "afi": s["afi"], "neighbor_ip": s["ip"],
                            "estado": s["estado"], "dias_no_estado": s["dias"], "last_error": s.get("erro"), "rotas_recebidas": s["recebidas"], "rotas_aceitas": s["aceitas"],
                            "rotas_filtradas": s["filtradas"], "import_limit": s["limite"], "uso_limite": s["uso_limite"], "rs_incerto": bool(s.get("rs_incerto"))})
    out.sort(key=lambda r: (r["ixp"], r["asn"], r["rs"], r["neighbor_ip"]))
    return out
