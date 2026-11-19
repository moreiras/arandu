# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""ARC — Arandurapé Relationship Classifier (v1): E0 sanitização → E1/E2 evidência e âncoras → E3 propagação → decisão por elo.

Funciona sem os caminhos dos coletores (só rampa dos route servers, ASPA e CAIDA): nesse caso não há clique nem votos de
propagação e os níveis altos dependem de ASPA e RS. Entradas por AFI; ASPA, CAIDA e irmãos valem para as duas."""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, Iterable, Iterator, Optional

from products.as_relationships.config import Config
from products.as_relationships.decisao import Veredito, decidir
from products.as_relationships.evidencias import Evidencias, Par, calcular_clique
from products.as_relationships.propagacao import CaminhoVP, propagar
from products.as_relationships.sanitiza import sanitizar


def inferir(
    rs: Iterable[tuple[Iterable[int], str]],
    colecao: Optional[Callable[[], Iterator[tuple[Iterable[int], int, bool]]]],
    aspa: Iterable[dict],
    caida: Optional[tuple[list, list]],
    grupos: dict[int, str],
    cfg: Config,
    so_elos: Optional[Callable[[int, int], bool]] = None,
    contexto: Optional[dict] = None,
) -> tuple[list[Veredito], dict]:
    """Devolve (vereditos, diagnóstico). `rs`: (AS_PATH, PTT); `colecao()`: iterador novo de (caminho, n_vps, vp0) por chamada;
    `so_elos(a, b)`: filtro opcional dos elos que vale a pena classificar (ex.: ao menos um ASN brasileiro).
    `contexto`: se for um dict, recebe as estruturas que o refinamento v2 reaproveita (evidências, adjacência, grau de trânsito,
    votos da propagação e o iterador dos caminhos limpos), para não repetir a passada 0."""
    ev = Evidencias()
    ev.grupo = dict(grupos)
    ev.definir_aspa(aspa)
    if caida:
        ev.definir_caida(*caida)
    diag = {"rs_caminhos": 0, "rs_descartados": 0, "col_caminhos": 0, "col_descartados": 0}

    for caminho, ptt in rs:
        c = sanitizar(caminho, cfg)
        if c is None:
            diag["rs_descartados"] += 1
            continue
        diag["rs_caminhos"] += 1
        ev.adicionar_rs(c, ptt)

    votos: dict[Par, list[int]] = {}
    adj: dict[int, set[int]] = defaultdict(set)
    transito: dict[int, set[int]] = defaultdict(set)
    limpos = None
    if colecao is not None:

        def limpos(contar: bool = False) -> Iterator[CaminhoVP]:
            for caminho, n_vps, vp0 in colecao():
                c = sanitizar(caminho, cfg)
                if c is None:
                    if contar:
                        diag["col_descartados"] += 1
                    continue
                yield c, n_vps, vp0

        for c, n_vps, _ in limpos(contar=True):                                    # passada 0: grafo, grau de trânsito, VPs por elo
            diag["col_caminhos"] += 1
            ev.adicionar_vistos(c, n_vps)
            for i in range(len(c) - 1):
                adj[c[i]].add(c[i + 1])
                adj[c[i + 1]].add(c[i])
            for i in range(1, len(c) - 1):
                transito[c[i]].update((c[i - 1], c[i + 1]))
        ev.clique = calcular_clique(adj, {a: len(v) for a, v in transito.items()}, cfg.clique_candidatos, cfg.clique_tamanho_minimo)
        diag["clique"] = sorted(ev.clique)

        votos = propagar(limpos, ev, cfg)

    candidatos: set[tuple[int, int]] = set(ev.vistos)
    candidatos |= {(min(p, c), max(p, c)) for p, c in ev.aspa_pos}
    candidatos |= {(min(p, c), max(p, c)) for p, c in ev.caida_p2c} | ev.caida_p2p   # só no CAIDA: nível 'possível' no máximo
    vereditos = [decidir(a, b, ev, cfg, votos) for a, b in sorted(candidatos) if so_elos is None or so_elos(a, b)]
    diag["elos"] = len(vereditos)
    if contexto is not None:
        contexto.update(ev=ev, adj=adj, grau_transito={a: len(v) for a, v in transito.items()}, votos=votos, limpos=limpos, cfg=cfg)
    return vereditos, diag
