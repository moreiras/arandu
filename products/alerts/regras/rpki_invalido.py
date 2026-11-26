# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Anúncios próprios marcados como inválidos pelo RPKI (só avalia ASes com ROA)."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from core import alerta_textos

REGRA = Regra(id="rpki_invalido", categoria="rpki", severidade="critico", versao=1,
              descricao="prefixo com validação RPKI invalid")


def avaliar(ctx: Contexto) -> list[dict]:
    if not ctx.doc.get("roa_list"):
        return []
    invalid = [p for p, st in (ctx.doc.get("rpki_validation") or {}).items() if st == "invalid"]
    if not invalid:
        return []
    return [achado(
        "Anúncio RPKI inválido",
        alerta_textos.rpki_invalido(len(invalid)),
        {"prefixes": invalid[:30]})]
