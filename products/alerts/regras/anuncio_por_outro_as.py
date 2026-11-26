# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Bloco do AS originado na full table por outro ASN."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from core import alerta_textos
from products.alerts.auxiliar import blocos_rir

REGRA = Regra(id="anuncio_por_outro_as", categoria="roteamento", severidade="aviso", versao=1,
              descricao="prefixo do AS originado por um ASN diferente")


def avaliar(ctx: Contexto) -> list[dict]:
    _, by_other = blocos_rir(ctx)
    if not by_other:
        return []
    return [achado(
        "Bloco anunciado por outro AS",
        alerta_textos.anuncio_por_outro_as(len(by_other)),
        {"items": by_other[:30]})]
