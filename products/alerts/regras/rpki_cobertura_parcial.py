# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Alocações RIR sem nenhum ROA cobrindo, quando outras estão cobertas."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from core import alerta_textos
from products.alerts.auxiliar import roas
from products.alerts.base import net

REGRA = Regra(id="rpki_cobertura_parcial", categoria="rpki", severidade="aviso", versao=1,
              descricao="parte dos blocos alocados sem ROA")


def avaliar(ctx: Contexto) -> list[dict]:
    if not ctx.doc.get("roa_list"):
        return []
    roa_nets = roas(ctx)
    uncovered: list[str] = []
    for p in (ctx.rir_v4 + ctx.rir_v6):
        pn = net(p)
        if pn is None:
            continue
        covered = any(
            pn.version == rn.version and (pn.subnet_of(rn) or pn == rn)
            for rn, _ in roa_nets
        )
        if not covered:
            uncovered.append(p)
    if uncovered and len(uncovered) < len(ctx.rir_v4 + ctx.rir_v6):
        return [achado(
            "Cobertura RPKI parcial",
            alerta_textos.cobertura_rpki_parcial(len(uncovered)),
            {"prefixes": uncovered[:30]})]
    return []
