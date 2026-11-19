# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Média de repetições de prepend acima de 2x no AS_PATH (id por AFI: prepend_excessivo_v4/v6)."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from products.alerts.auxiliar import analise_bgp

REGRA = Regra(id="prepend_excessivo", categoria="roteamento", severidade="aviso", versao=1,
              descricao="routing_analysis: avg_excess > 2")


def avaliar(ctx: Contexto) -> list[dict]:
    ra = analise_bgp(ctx)
    as_path = (ra or {}).get("as_path_stats") or {}
    if not as_path:
        return []
    achados = []
    for row in (as_path.get("top_prependers") or []):
        if row.get("asn") != ctx.asn:
            continue
        avg_excess = row.get("avg_excess", 0)
        if avg_excess > 2:
            afi = row.get("afi", "")
            achados.append(achado(
                f"Prepend excessivo no AS_PATH ({afi.upper()})",
                f"A média de repetições de prepend em {afi.upper()} é "
                f"{avg_excess:.1f}x nas rotas deste AS. Prepend excessivo "
                "pode causar seleção de caminho subótima por peers e "
                "provedores; o valor recomendado é ≤ 2.",
                {"afi": afi,
                 "avg_excess": avg_excess,
                 "routes_with_prepend": row.get("routes_with_prepend")},
                id=f"prepend_excessivo_{afi}"))
    return achados
