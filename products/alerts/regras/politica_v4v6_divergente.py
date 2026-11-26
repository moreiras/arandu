# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Peering direto assimétrico entre IPv4 e IPv6 nos IXPs (só para quem tem IPv6)."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from core import alerta_textos

REGRA = Regra(id="politica_v4v6_divergente", categoria="v4v6", severidade="info", versao=1,
              descricao="IXPs com peering só v4 ou só v6 em AS com IPv6")


def avaliar(ctx: Contexto) -> list[dict]:
    presence = ctx.doc.get("ixp_presence") or {}
    v4_only, v6_only = [], []
    for code, pres in presence.items():
        d4 = bool((pres.get("v4") or {}).get("direct"))
        d6 = bool((pres.get("v6") or {}).get("direct"))
        if d4 and not d6:
            v4_only.append(code)
        elif d6 and not d4:
            v6_only.append(code)
    # Só sinaliza quando o AS é capaz de IPv6 (tem v6) mas faz peering assimétrico entre as famílias.
    has_v6 = bool(ctx.rir_v6 or ctx.glob_v6)
    if not (has_v6 and (v4_only or v6_only)):
        return []
    return [achado(
        "Políticas IPv6 e IPv4 divergentes",
        alerta_textos.politica_v4v6(len(v6_only), len(v4_only)),
        {"v4_only": sorted(v4_only), "v6_only": sorted(v6_only)})]
