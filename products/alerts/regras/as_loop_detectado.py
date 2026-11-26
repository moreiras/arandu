# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Prefixos do AS com AS_PATH em loop (mesmo ASN de forma não consecutiva)."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from core import alerta_textos
from products.alerts.auxiliar import analise_bgp

REGRA = Regra(id="as_loop_detectado", categoria="roteamento", severidade="aviso", versao=1,
              descricao="routing_analysis: hygiene_issues as_loop")


def avaliar(ctx: Contexto) -> list[dict]:
    ra = analise_bgp(ctx)
    as_path = (ra or {}).get("as_path_stats") or {}
    if not as_path:
        return []
    loop_prefixes = [
        r["prefix"]
        for r in (as_path.get("hygiene_issues") or [])
        if r.get("origin_as") == ctx.asn and r.get("issue") == "as_loop"
    ]
    if not loop_prefixes:
        return []
    return [achado(
        "Loop de AS detectado",
        alerta_textos.as_loop(len(loop_prefixes)),
        {"prefixes": loop_prefixes[:30]})]
