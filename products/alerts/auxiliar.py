# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cálculos compartilhados entre regras de alerta."""
from __future__ import annotations

from bisect import bisect_left

from products.alerts.base import Contexto, net

# Raio (km) para considerar um AS "próximo" de um PTT onde não participa.
GEO_PROXIMITY_KM = 80.0
# maxLength - prefixlen a partir do qual um ROA é considerado folgado demais.
ROA_MAXLENGTH_SLACK = 8
# Razão global/RIR (e mínimo absoluto) para sinalizar desagregação excessiva.
DEAGG_RATIO = 4
DEAGG_MIN = 8


def alcancavel(p_net, starts_sorted: list, origin_map: dict) -> bool:
    """Um bloco alocado é alcançável se um agregado que o cobre, o próprio bloco,
    ou qualquer rota mais-específica dentro dele (de qualquer origem) aparece na
    full table."""
    # Agregado menos-específico que cobre o bloco
    minlen = 8 if p_net.version == 4 else 12
    n = p_net
    while n.prefixlen > minlen:
        n = n.supernet()
        if str(n) in origin_map:
            return True
    # Qualquer rota cujo início caia dentro do bloco (exato ou mais-específico)
    lo = int(p_net.network_address)
    hi = int(p_net.broadcast_address)
    i = bisect_left(starts_sorted, lo)
    return i < len(starts_sorted) and starts_sorted[i] <= hi


def blocos_rir(ctx: Contexto) -> tuple[list, list]:
    """(blocos RIR sem rota global, blocos RIR originados por outro AS), compartilhado por duas regras."""
    if "blocos_rir" not in ctx.memo:
        unreachable: list[str] = []
        by_other: list[dict] = []
        for afi, rir in (("v4", ctx.rir_v4), ("v6", ctx.rir_v6)):
            if not rir:
                continue
            origin_map = ctx.store.origin_by_prefix(ctx.date_str, afi)
            starts = ctx.store.announced_starts(ctx.date_str, afi)
            for p in rir:
                pn = net(p)
                if pn is None:
                    continue
                if not alcancavel(pn, starts, origin_map):
                    unreachable.append(p)
                origin = origin_map.get(p)
                if origin is not None and origin != ctx.asn:
                    by_other.append({"prefix": p, "origin_asn": origin})
        ctx.memo["blocos_rir"] = (unreachable, by_other)
    return ctx.memo["blocos_rir"]


def roas(ctx: Contexto) -> list:
    """[(rede do ROA, maxLength)] do `roa_list` do documento."""
    if "roas" not in ctx.memo:
        out = []
        for r in ctx.doc.get("roa_list") or []:
            rn = net(r.get("prefix", ""))
            if rn is not None:
                out.append((rn, r.get("maxLength")))
        ctx.memo["roas"] = out
    return ctx.memo["roas"]


def analise_bgp(ctx: Contexto):
    """`routing_analysis.json` do snapshot (None se ausente)."""
    if "ra" not in ctx.memo:
        ctx.memo["ra"] = ctx.store.routing_analysis(ctx.date_str)
    return ctx.memo["ra"]
