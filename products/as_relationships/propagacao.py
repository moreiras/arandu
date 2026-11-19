# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""E3 — propagação *valley-free* dos rótulos nos caminhos dos coletores (generalização do CoreToLeaf do ProbLink).

Um caminho lido do VP (esquerda) para a origem (direita) sobe por elos cliente→provedor ('U'), tem no máximo um par no ápice ('P')
e desce por provedor→cliente ('D'). Dado um elo conhecido: depois de um 'D' tudo é 'D'; antes de um 'U' tudo é 'U'; um 'P' separa
subida e descida. Caminho com 'D' antes de 'U' viola *valley-free* (vazamento ou *poisoning*): não vota. O elo VP→1º AS também
não vota quando o 1º AS é o próprio VP (é o elo mais sujeito a viés: reflete a política de exportação do VP, não a hierarquia).
Cada caminho único vota uma vez por elo; só elos sem rótulo prévio recebem voto (confirmar o que já se sabia não reforça o próprio voto)."""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, Iterable, Iterator

from products.as_relationships.config import Config
from products.as_relationships.evidencias import Evidencias, Par

#: (caminho sanitizado, nº de VPs, 1º AS é VP)
CaminhoVP = tuple[tuple[int, ...], int, bool]


def votar_caminho(caminho: tuple[int, ...], vp0: bool, rotulo: Callable[[int, int], str | None]) -> list[tuple[int, Par]] | None:
    """Votos `(índice do elo, (provedor, cliente))` do caminho, ou None se viola *valley-free*."""
    n = len(caminho) - 1
    conhecidos = [rotulo(caminho[i], caminho[i + 1]) for i in range(n)]
    ult_up = -1                      # maior índice com 'U' ou 'P': tudo antes é 'U'
    prim_dp = n                      # menor índice com 'D' ou 'P': tudo depois é 'D'
    descendo = False                 # padrão válido: U* P? D*
    for i, r in enumerate(conhecidos):
        if r == "U":
            if descendo:
                return None
            ult_up = i
        elif r == "P":
            if descendo:
                return None
            descendo, ult_up, prim_dp = True, i, min(prim_dp, i)
        elif r == "D":
            descendo = True
            prim_dp = min(prim_dp, i)
    votos: list[tuple[int, Par]] = []
    for i in range(n):
        if conhecidos[i] is not None:
            continue
        if i == 0 and vp0:
            continue
        if i < ult_up:
            votos.append((i, (caminho[i + 1], caminho[i])))        # sobe: o da direita é provedor
        elif i > prim_dp:
            votos.append((i, (caminho[i], caminho[i + 1])))        # desce: o da esquerda é provedor
    return votos


def rodada(caminhos: Iterable[CaminhoVP], ev: Evidencias, extra: dict[Par, str]) -> dict[Par, list[int]]:
    """Uma passada: `{(provedor, cliente): [votos, máx. de VPs]}`."""
    votos: dict[Par, list[int]] = {}
    rot = lambda x, y: ev.rotulo_ancora(x, y, extra)           # noqa: E731
    for caminho, n_vps, vp0 in caminhos:
        r = votar_caminho(caminho, vp0, rot)
        if not r:
            continue
        for _, par in r:
            v = votos.get(par)
            if v is None:
                votos[par] = [1, n_vps]
            else:
                v[0] += 1
                if n_vps > v[1]:
                    v[1] = n_vps
    return votos


def propagar(abrir: Callable[[], Iterator[CaminhoVP]], ev: Evidencias, cfg: Config) -> dict[Par, list[int]]:
    """Roda `cfg.rodadas` passadas; a cada uma, elos com votos suficientes e direção quase unânime viram âncora da seguinte.
    `abrir()` devolve um iterador novo dos caminhos (streaming: o arquivo é relido a cada rodada). Devolve os votos da última."""
    extra: dict[Par, str] = {}
    votos: dict[Par, list[int]] = {}
    for _ in range(max(1, cfg.rodadas)):
        votos = rodada(abrir(), ev, extra)
        novos: dict[Par, str] = {}
        por_elo: dict[tuple[int, int], dict[Par, int]] = defaultdict(dict)
        for (p, c), (n, _) in votos.items():
            por_elo[(min(p, c), max(p, c))][(p, c)] = n
        for (a, b), dirs in por_elo.items():
            total = sum(dirs.values())
            (par, n) = max(dirs.items(), key=lambda kv: kv[1])
            if n >= cfg.votos_para_ancora and n / total >= cfg.razao_para_ancora:
                p, c = par
                novos[(c, p)] = "U"                              # lido (cliente, provedor): sobe
                novos[(p, c)] = "D"
        if novos == extra:
            break
        extra = novos
    return votos
