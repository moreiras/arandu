# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Restrições e rótulos da v2 aplicados às linhas já unidas (v4+v6):

  1. irmãos: ASNs do mesmo CNPJ raiz (Registro.br) ou da mesma organização do CAIDA (`as2org`) viram `s2s`; as duas origens
     concordando sobem o nível para `provavel` (fontes independentes), uma só fica em `possivel`. ASPA positivo não é desfeito.
  2. acíclico: o grafo p2c, com os irmãos colapsados num só nó, não pode ter ciclo (ninguém é cliente de si mesmo); em cada ciclo
     o elo mais fraco (menor nível e p) é rebaixado a `sem_classificacao`, nunca um `declarado`.
  3. `complexa`: v4 e v6 divergindo com força (ambas com p ≥ `complexa_p_min` e nível ≥ provável) viram uma linha só, híbrida
     (p2c numa família e p2p na outra) ou inversa (p2c nos dois sentidos)."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from products.as_relationships.config import Config

ORDEM_NIVEL = {"declarado": 4, "confirmado": 3, "provavel": 2, "possivel": 1, "sem_classificacao": 0}


class _UF:
    def __init__(self) -> None:
        self.pai: dict = {}

    def achar(self, x):
        self.pai.setdefault(x, x)
        while self.pai[x] != x:
            self.pai[x] = self.pai[self.pai[x]]
            x = self.pai[x]
        return x

    def unir(self, a, b) -> None:
        ra, rb = self.achar(a), self.achar(b)
        if ra != rb:
            self.pai[max(ra, rb)] = min(ra, rb)


def grupos_de_irmaos(cnpj_raiz: dict[int, str], organizacao: dict[int, str]) -> dict[int, int]:
    """{asn: representante} só para ASNs em grupo com mais de um membro (CNPJ raiz ou organização do CAIDA, a união das duas)."""
    uf = _UF()
    por_chave: dict[tuple[str, str], int] = {}
    for tipo, mapa in (("c", cnpj_raiz), ("o", organizacao)):
        for asn, chave in mapa.items():
            k = (tipo, chave)
            if k in por_chave:
                uf.unir(asn, por_chave[k])
            else:
                por_chave[k] = asn
                uf.achar(asn)
    membros: dict[int, int] = defaultdict(int)
    for asn in list(uf.pai):
        membros[uf.achar(asn)] += 1
    return {asn: uf.achar(asn) for asn in list(uf.pai) if membros[uf.achar(asn)] > 1}


def _evid(l: dict) -> dict:
    return l["evid"] if isinstance(l["evid"], dict) else {}


def aplicar_irmaos(linhas: list[dict], cnpj_raiz: dict[int, str], organizacao: dict[int, str]) -> int:
    n = 0
    for l in linhas:
        a, b = l["a"], l["b"]
        c = a in cnpj_raiz and cnpj_raiz.get(a) == cnpj_raiz.get(b)
        o = a in organizacao and organizacao.get(a) == organizacao.get(b)
        if not (c or o) or l["nivel"] == "declarado":
            continue
        l["evid"] = {**_evid(l), "irmaos": {"cnpj": c, "organizacao": o}, "antes_dos_irmaos": _resumo(l)}
        l["a"], l["b"] = min(a, b), max(a, b)
        l["tipo"] = "s2s"
        l["nivel"] = "provavel" if (c and o) else "possivel"
        l["p"] = 0.85 if (c and o) else 0.6
        n += 1
    return n


def _scc(nos: Iterable[int], arcos: dict[int, list[int]]) -> list[list[int]]:
    """Componentes fortemente conexos não triviais (Tarjan iterativo)."""
    indice: dict[int, int] = {}
    baixo: dict[int, int] = {}
    pilha: list[int] = []
    na_pilha: set[int] = set()
    out: list[list[int]] = []
    cont = 0
    for raiz in nos:
        if raiz in indice:
            continue
        trabalho = [(raiz, iter(arcos.get(raiz, ())))]
        indice[raiz] = baixo[raiz] = cont
        cont += 1
        pilha.append(raiz)
        na_pilha.add(raiz)
        while trabalho:
            v, it = trabalho[-1]
            avancou = False
            for w in it:
                if w not in indice:
                    indice[w] = baixo[w] = cont
                    cont += 1
                    pilha.append(w)
                    na_pilha.add(w)
                    trabalho.append((w, iter(arcos.get(w, ()))))
                    avancou = True
                    break
                if w in na_pilha:
                    baixo[v] = min(baixo[v], indice[w])
            if avancou:
                continue
            trabalho.pop()
            if trabalho:
                u = trabalho[-1][0]
                baixo[u] = min(baixo[u], baixo[v])
            if baixo[v] == indice[v]:
                comp = []
                while True:
                    w = pilha.pop()
                    na_pilha.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                if len(comp) > 1:
                    out.append(comp)
    return out


def quebrar_ciclos(linhas: list[dict], grupo: dict[int, int], afis: Iterable[str] = ("v4", "v6")) -> int:
    """Rebaixa o elo p2c mais fraco de cada ciclo (por família, com irmãos colapsados). Devolve quantos elos rebaixou."""
    rebaixados = 0
    rep = lambda x: grupo.get(x, x)                                                # noqa: E731
    for afi in afis:
        cand = [l for l in linhas if l["tipo"] == "p2c" and afi in l["afi"]]
        for _ in range(10_000):
            arcos: dict[int, list[int]] = defaultdict(list)
            for l in cand:
                if l["tipo"] == "p2c":
                    arcos[rep(l["a"])].append(rep(l["b"]))
            comps = _scc(list(arcos), arcos)
            if not comps:
                break
            feito = False
            for comp in comps:
                c = set(comp)
                dentro = [l for l in cand if l["tipo"] == "p2c" and rep(l["a"]) in c and rep(l["b"]) in c and l["nivel"] != "declarado"]
                if not dentro:
                    continue
                pior = min(dentro, key=lambda l: (ORDEM_NIVEL[l["nivel"]], l["p"], l["a"], l["b"]))
                pior["evid"] = {**_evid(pior), "restricao": "ciclo_p2c", "antes_do_ciclo": _resumo(pior)}
                a, b = min(pior["a"], pior["b"]), max(pior["a"], pior["b"])
                pior["a"], pior["b"], pior["tipo"], pior["nivel"] = a, b, "sem_classificacao", "sem_classificacao"
                rebaixados += 1
                feito = True
            if not feito:
                break
    return rebaixados


def _resumo(l: dict) -> dict:
    return {"tipo": l["tipo"], "a": l["a"], "b": l["b"], "p": l["p"], "nivel": l["nivel"]}


def unir_complexas(linhas: list[dict], cfg: Config) -> tuple[list[dict], int]:
    """Funde os pares de linhas `afi_divergente` em que as duas famílias têm p alto e nível ≥ provável numa linha `complexa`."""
    por_elo: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for l in linhas:
        if l.get("afi_divergente"):
            por_elo[(min(l["a"], l["b"]), max(l["a"], l["b"]))].append(l)
    fundir: dict[int, dict | None] = {}
    for k, ls in por_elo.items():
        v4 = next((l for l in ls if l["afi"] == ["v4"]), None)
        v6 = next((l for l in ls if l["afi"] == ["v6"]), None)
        if not (v4 and v6):
            continue
        fortes = all(l["p"] >= cfg.refino.complexa_p_min and ORDEM_NIVEL[l["nivel"]] >= ORDEM_NIVEL["provavel"] and l["tipo"] in ("p2c", "p2p")
                     for l in (v4, v6))
        if not fortes:
            continue
        sub = "hibrida" if "p2p" in (v4["tipo"], v6["tipo"]) else "inversa"
        nivel = min((v4["nivel"], v6["nivel"]), key=lambda n: ORDEM_NIVEL[n])
        nova = {"a": k[0], "b": k[1], "tipo": "complexa", "p": min(v4["p"], v6["p"]), "nivel": nivel, "afi": ["v4", "v6"],
                "evid": {"complexa": {"subtipo": sub, "v4": {**_resumo(v4), "evid": v4["evid"]}, "v6": {**_resumo(v6), "evid": v6["evid"]}}},
                "n_vps": max(v4["n_vps"], v6["n_vps"]), "n_ptt": max(v4["n_ptt"], v6["n_ptt"])}
        fundir[id(v4)] = nova
        fundir[id(v6)] = None
    out = []
    for l in linhas:
        if id(l) in fundir:
            if fundir[id(l)] is not None:
                out.append(fundir[id(l)])
            continue
        out.append(l)
    return out, sum(1 for v in fundir.values() if v is not None)
