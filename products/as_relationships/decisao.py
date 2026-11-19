# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Decisão por elo: soma de pesos (log-verossimilhanças aproximadas) por hipótese e posterior por softmax.

Hipóteses para o elo não orientado {a, b} (a < b): `ab` (a é provedor de b), `ba`, `pp` (par) e `ss` (irmãos).
O nível depende da probabilidade **e** do nº de fontes independentes que sustentam a hipótese vencedora (aspa, rs, colecao, clique):
o CAIDA e os irmãos sozinhos nunca passam de 'possível'. ASPA positivo é 'declarado' (evidência de alto peso, **não veto**: o BGP
pode contrariá-lo e a disputa é registrada em `evid.contra`)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from products.as_relationships.config import Config
from products.as_relationships.evidencias import Evidencias, Par

HIPOTESES = ("ab", "ba", "pp", "ss")
INDEPENDENTES = ("aspa", "rs", "colecao", "clique")


@dataclass
class Veredito:
    a: int
    b: int
    tipo: str                    # p2c (a é provedor de b) | p2p | s2s | sem_classificacao
    p: float
    nivel: str                   # declarado | confirmado | provavel | possivel | sem_classificacao
    evid: dict = field(default_factory=dict)
    n_vps: int = 0
    n_ptt: int = 0


def _saturar(maximo: float, taxa: float, n: int) -> float:
    return maximo * (1.0 - math.exp(-taxa * n)) if n > 0 else 0.0


def decidir(a: int, b: int, ev: Evidencias, cfg: Config, votos_col: dict[Par, list[int]]) -> Veredito:
    w = cfg.pesos
    s = {h: 0.0 for h in HIPOTESES}
    fontes: dict[str, set[str]] = {h: set() for h in HIPOTESES}
    s["pp"] += w.prior_par
    info: dict = {}
    n_ptt = 0
    for h, par in (("ab", (a, b)), ("ba", (b, a))):
        m, t = len(ev.rs_membros.get(par, ())), len(ev.rs_ptts.get(par, ()))
        if m:
            s[h] += _saturar(w.rs_max, 0.7, m) + w.rs_bonus_ptt * min(t - 1, 2)
            fontes[h].add("rs")
            info.setdefault("rs", {})[h] = {"membros": m, "ptts": t}
            n_ptt = max(n_ptt, t)
        v = votos_col.get(par)
        if v:
            s[h] += _saturar(w.colecao_max, 0.4, v[0])
            fontes[h].add("colecao")
            info.setdefault("colecao", {})[h] = {"votos": v[0], "vps": v[1]}
        if par in ev.aspa_pos:
            s[h] += w.aspa_positivo
            fontes[h].add("aspa")
            info.setdefault("aspa", {})[h] = "declarado"
        elif ev.aspa_nega(par):
            s[h] -= w.aspa_negativo
            info.setdefault("aspa", {})[h] = "nao_lista"
        if par in ev.caida_p2c:
            s[h] += w.caida_p2c
            info.setdefault("caida", {})[h] = "p2c"
    if (a, b) in ev.caida_p2p:
        s["pp"] += w.caida_p2p
        info.setdefault("caida", {})["pp"] = "p2p"
    if ev.no_clique(a, b):
        s["pp"] += w.clique_par
        fontes["pp"].add("clique")
        info["clique"] = "par"
    if (a in ev.clique) != (b in ev.clique):                      # borda do clique: quem está fora é cliente (CoreToLeaf)
        h = "ab" if a in ev.clique else "ba"
        s[h] += w.clique_borda
        fontes[h].add("clique")
        info.setdefault("clique", {})[h] = "borda"
    ga, gb = ev.grupo.get(a), ev.grupo.get(b)
    if ga is not None and ga == gb:
        s["ss"] += w.irmaos
        info["irmaos"] = True

    hipoteses = HIPOTESES if info.get("irmaos") else HIPOTESES[:3]          # 'irmãos' só compete se há indício de grupo
    mx = max(s[h] for h in hipoteses)
    exp = {h: math.exp(s[h] - mx) for h in hipoteses}
    z = sum(exp.values())
    post = {h: exp[h] / z for h in hipoteses}
    ordem = sorted(hipoteses, key=lambda h: (-post[h], h))
    melhor, segundo = ordem[0], ordem[1]
    p = post[melhor]
    tipo = {"ab": "p2c", "ba": "p2c", "pp": "p2p", "ss": "s2s"}[melhor]
    prov, cli = (a, b) if melhor == "ab" else (b, a)
    nivel = "sem_classificacao"
    declarado = melhor in ("ab", "ba") and "aspa" in fontes[melhor]
    if declarado:
        nivel = "declarado"
    else:
        for nome, p_min, n_min in cfg.niveis:
            if p >= p_min and len(fontes[melhor]) >= n_min:
                nivel = nome
                break
    if melhor == "ss":
        nivel = "possivel" if nivel != "sem_classificacao" else nivel
    if not info:
        nivel = "sem_classificacao"
    if nivel == "sem_classificacao":
        tipo = "sem_classificacao"
    contra = [h for h in ordem[1:] if fontes[h]]                      # alguma fonte independente aponta outra relação: disputa visível
    if contra or (post[segundo] >= 0.2 and segundo == "pp"):
        h = contra[0] if contra else segundo
        alt = {"ab": {"tipo": "p2c", "a": a, "b": b}, "ba": {"tipo": "p2c", "a": b, "b": a}, "pp": {"tipo": "p2p"}, "ss": {"tipo": "s2s"}}[h]
        info["contra"] = {**alt, "p": round(post[h], 3), "fontes": sorted(fontes[h])}
    return Veredito(
        a=prov if tipo == "p2c" else a, b=cli if tipo == "p2c" else b, tipo=tipo, p=round(p, 4), nivel=nivel,
        evid={**info, "fontes": sorted(fontes[melhor])}, n_vps=ev.n_vps_elo.get((a, b), 0), n_ptt=n_ptt)
