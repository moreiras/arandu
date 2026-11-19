# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Potencial de agregação acima de 90% na análise BGP (id por AFI: agregacao_elevada_v4/v6)."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from products.alerts.auxiliar import analise_bgp

REGRA = Regra(id="agregacao_elevada", categoria="roteamento", severidade="info", versao=1,
              descricao="routing_analysis: savings_path_pct > 90")


def avaliar(ctx: Contexto) -> list[dict]:
    ra = analise_bgp(ctx)
    if not ra:
        return []
    achados = []
    for row in (ra.get("aggregation_by_asn") or []):
        if row.get("asn") != ctx.asn:
            continue
        pct = row.get("savings_path_pct", 0)
        if pct > 90:
            afi = row.get("afi", "")
            achados.append(achado(
                f"Potencial de agregação {afi.upper()} > 90%",
                f"Análise de agregação indica que {pct}% dos prefixos "
                f"{afi.upper()} poderiam ser eliminados agrupando blocos "
                "contíguos (RFC 4632). Anunciar mais-específicos desnecessários "
                "infla a tabela global.",
                {"current": row.get("current"),
                 "aggregated": row.get("by_origin"),
                 "savings_pct": pct},
                id=f"agregacao_elevada_{afi}"))
    return achados
