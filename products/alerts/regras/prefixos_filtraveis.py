# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Prefixos mais específicos que /48 (IPv6) ou /24 (IPv4) que operadores de backbone podem descartar (exceto /32 e /64)."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from products.alerts.auxiliar import analise_bgp
from products.alerts.base import net

REGRA = Regra(id="prefixos_filtraveis", categoria="roteamento", severidade="aviso", versao=1,
              descricao="routing_analysis: too_specific do AS (exceto /32 v4 e /64 v6)")


def avaliar(ctx: Contexto) -> list[dict]:
    ra = analise_bgp(ctx)
    if not ra:
        return []
    too_spec = ra.get("too_specific") or {}
    filterable: list[str] = []
    for r in (too_spec.get("v4") or []):
        if r.get("origin_as") != ctx.asn:
            continue
        n = net(r.get("prefix", ""))
        if n and n.prefixlen != 32:
            filterable.append(r["prefix"])
    for r in (too_spec.get("v6") or []):
        if r.get("origin_as") != ctx.asn:
            continue
        n = net(r.get("prefix", ""))
        if n and n.prefixlen != 64:
            filterable.append(r["prefix"])
    if not filterable:
        return []
    return [achado(
        "Prefixos potencialmente filtráveis",
        f"{len(filterable)} prefixo(s) excedem os limites convencionais "
        "(IPv6 >/48, IPv4 >/24) e podem ser descartados por operadores "
        "de backbone. Se há um agregado menos específico cobrindo o espaço, "
        "o tráfego seria absorvido por ele; do contrário, o descarte "
        "causaria blackhole.",
        {"prefixes": filterable[:30]})]
