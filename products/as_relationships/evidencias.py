# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""E1/E2 — vetor de evidência por elo e âncoras de alta precisão.

Direção sempre como par ordenado `(provedor, cliente)`. Fontes de evidência (as 4 primeiras são independentes entre si; o CAIDA
usa os mesmos coletores que nós e por isso só serve de prior):
  aspa    objetos ASPA: o cliente declara seus provedores (positivo) e quem ele não lista (negativo, mais fraco)
  rs      rampa dos route servers do IX.br: no caminho [membro, …, origem] cada AS é provedor do seguinte
  colecao votos da propagação valley-free nos caminhos dos coletores (ver propagacao.py)
  clique  pares entre os ASNs do topo (Luckie §4.4)
  caida   as-rel2 do CAIDA
  irmaos  mesmo CNPJ/grupo econômico (só nível 'possível')"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Iterable, Optional

Par = tuple[int, int]


class Evidencias:
    def __init__(self) -> None:
        self.rs_membros: dict[Par, set[int]] = defaultdict(set)
        self.rs_ptts: dict[Par, set[str]] = defaultdict(set)
        self.colecao: dict[Par, list[int]] = {}                   # (prov, cli) → [votos, máx. de VPs]
        self.aspa_pos: set[Par] = set()
        self.aspa_provedores: dict[int, frozenset[int]] = {}      # cliente → provedores declarados (0 = "nenhum", AS0)
        self.caida_p2c: set[Par] = set()
        self.caida_p2p: set[tuple[int, int]] = set()
        self.clique: frozenset[int] = frozenset()
        self.grupo: dict[int, str] = {}                           # ASN → chave de grupo (CNPJ raiz)
        self.vistos: set[tuple[int, int]] = set()                 # elos não orientados vistos em algum caminho (a<b)
        self.n_vps_elo: dict[tuple[int, int], int] = defaultdict(int)
        self.ptts_do_asn: dict[int, set[str]] = defaultdict(set)  # PTTs em que o ASN aparece como membro da rampa (co-localização, v2)

    # ── entradas ────────────────────────────────────────────────────────────
    def adicionar_rs(self, caminho: tuple[int, ...], ptt: str) -> None:
        """Rota do route server: `caminho[0]` é o membro; cada AS é provedor do seguinte (rampa de subida lida da origem)."""
        membro = caminho[0]
        self.ptts_do_asn[membro].add(ptt)
        for i in range(len(caminho) - 1):
            par = (caminho[i], caminho[i + 1])
            self.rs_membros[par].add(membro)
            self.rs_ptts[par].add(ptt)
            self.vistos.add((min(par), max(par)))

    def adicionar_vistos(self, caminho: tuple[int, ...], n_vps: int) -> None:
        for i in range(len(caminho) - 1):
            k = (min(caminho[i], caminho[i + 1]), max(caminho[i], caminho[i + 1]))
            self.vistos.add(k)
            if n_vps > self.n_vps_elo[k]:
                self.n_vps_elo[k] = n_vps

    def definir_aspa(self, objetos: Iterable[dict]) -> None:
        for o in objetos:
            cli = int(o["customer"])
            provs = frozenset(int(p) for p in o.get("providers", []))
            self.aspa_provedores[cli] = self.aspa_provedores.get(cli, frozenset()) | provs
            for p in provs:
                if p != 0:
                    self.aspa_pos.add((p, cli))

    def definir_caida(self, p2c: Iterable[Iterable[int]], p2p: Iterable[Iterable[int]]) -> None:
        self.caida_p2c = {(int(a), int(b)) for a, b in p2c}
        self.caida_p2p = {(min(int(a), int(b)), max(int(a), int(b))) for a, b in p2p}

    # ── consultas ───────────────────────────────────────────────────────────
    def rs_forte(self, par: Par) -> bool:
        """Âncora A2: ≥ 2 membros distintos ou ≥ 2 PTTs sustentam a direção."""
        return len(self.rs_membros.get(par, ())) >= 2 or len(self.rs_ptts.get(par, ())) >= 2

    def aspa_nega(self, par: Par) -> bool:
        """O cliente tem ASPA e não lista este provedor."""
        provs = self.aspa_provedores.get(par[1])
        return provs is not None and par[0] not in provs

    def no_clique(self, a: int, b: int) -> bool:
        return a in self.clique and b in self.clique

    def rotulo_ancora(self, x: int, y: int, extra: Optional[dict[Par, str]] = None) -> Optional[str]:
        """Direção conhecida do elo (x, y) lido da esquerda para a direita do caminho: 'U' (y é provedor de x), 'D' (x é provedor de
        y), 'P' (par) ou None. Âncoras: ASPA positivo > clique > rampa RS forte (mais os rótulos fortes de rodadas anteriores)."""
        if (y, x) in self.aspa_pos and (x, y) not in self.aspa_pos:
            return "U"
        if (x, y) in self.aspa_pos and (y, x) not in self.aspa_pos:
            return "D"
        if self.no_clique(x, y):
            return "P"
        if x in self.clique and y not in self.clique:
            return "D"                  # CoreToLeaf: quem vem depois de um membro do clique é cliente (ele não tem provedor)
        if y in self.clique and x not in self.clique:
            return "U"
        a, b = self.rs_forte((y, x)), self.rs_forte((x, y))
        if a and not b:
            return "U"
        if b and not a:
            return "D"
        if extra:
            r = extra.get((x, y))
            if r:
                return r
        return None


def calcular_clique(adj: dict[int, set[int]], grau_transito: dict[int, int], candidatos: int, minimo: int) -> frozenset[int]:
    """Clique no topo (Luckie §4.4): entre os `candidatos` de maior grau de trânsito, a clique máxima (Bron–Kerbosch, desempate
    pela soma do grau) e depois estendida, em ordem de grau, por quem é adjacente a todos. Vazio se menor que `minimo`."""
    top = sorted(grau_transito, key=lambda a: (-grau_transito[a], a))[:candidatos]
    viz = {a: adj.get(a, set()) & set(top) for a in top}
    melhor: list[int] = []

    def peso(c) -> tuple[int, int]:
        return (len(c), sum(grau_transito[x] for x in c))

    def bk(r: list[int], p: set[int], x: set[int]) -> None:
        nonlocal melhor
        if not p and not x:
            if peso(r) > peso(melhor):
                melhor = list(r)
            return
        if len(r) + len(p) < len(melhor):
            return
        pivo = max(p | x, key=lambda u: len(p & viz[u]))
        for v in sorted(p - viz[pivo], key=lambda a: -grau_transito[a]):
            bk(r + [v], p & viz[v], x & viz[v])
            p = p - {v}
            x = x | {v}

    bk([], set(top), set())
    clique = set(melhor)
    for a in top:
        if a not in clique and all(a in adj.get(c, ()) for c in clique):
            clique.add(a)
    return frozenset(clique) if len(clique) >= minimo else frozenset()


def pares_do_clique(clique: Iterable[int]) -> list[tuple[int, int]]:
    return [(min(a, b), max(a, b)) for a, b in combinations(sorted(clique), 2)]
