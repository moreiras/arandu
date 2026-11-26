# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Desagregação excessiva: muito mais prefixos anunciados do que blocos alocados (id derivado por família: desagregacao_ipv4/ipv6)."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from core import alerta_textos
from products.alerts.auxiliar import DEAGG_MIN, DEAGG_RATIO

REGRA = Regra(id="desagregacao", categoria="roteamento", severidade="info", versao=1,
              descricao="prefixos anunciados >= 4x os blocos alocados (mínimo 8)")


def avaliar(ctx: Contexto) -> list[dict]:
    achados = []
    for afi, rir, gcount in (
        ("IPv4", ctx.rir_v4, ctx.doc.get("global_prefixes_v4_count") or 0),
        ("IPv6", ctx.rir_v6, ctx.doc.get("global_prefixes_v6_count") or 0),
    ):
        base = len(rir)
        if gcount >= DEAGG_MIN and base > 0 and gcount >= DEAGG_RATIO * base:
            achados.append(achado(
                f"Desagregação {afi} elevada",
                alerta_textos.desagregacao(gcount, afi, base),
                {"global_count": gcount, "rir_count": base},
                id=f"desagregacao_{afi.lower()}"))
    return achados
