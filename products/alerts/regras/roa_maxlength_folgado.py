# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""ROA com maxLength muito acima do tamanho do prefixo (8 bits ou mais)."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from core import alerta_textos
from products.alerts.auxiliar import ROA_MAXLENGTH_SLACK, roas

REGRA = Regra(id="roa_maxlength_folgado", categoria="rpki", severidade="info", versao=1,
              descricao="maxLength - prefixlen >= 8")


def avaliar(ctx: Contexto) -> list[dict]:
    if not ctx.doc.get("roa_list"):
        return []
    loose = []
    for rn, maxlen in roas(ctx):
        if isinstance(maxlen, int) and maxlen - rn.prefixlen >= ROA_MAXLENGTH_SLACK:
            loose.append({"prefix": str(rn), "maxLength": maxlen})
    if not loose:
        return []
    return [achado(
        "ROA com maxLength folgado",
        alerta_textos.roa_maxlength_folgado(len(loose)),
        {"items": loose[:30]})]
