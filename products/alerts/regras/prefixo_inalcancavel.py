# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Bloco alocado que não aparece na tabela global (nem agregado que o cubra, nem mais-específico)."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from products.alerts.auxiliar import blocos_rir

REGRA = Regra(id="prefixo_inalcancavel", categoria="roteamento", severidade="aviso", versao=1,
              descricao="bloco atribuído pelo Registro.br sem nenhuma rota na full table")


def avaliar(ctx: Contexto) -> list[dict]:
    unreachable, _ = blocos_rir(ctx)
    if not unreachable:
        return []
    return [achado(
        "Bloco alocado não anunciado",
        f"{len(unreachable)} bloco(s) atribuído(s) pelo Registro.br não têm "
        "nenhuma rota (nem agregado que os cubra, nem mais-específico) na "
        "tabela de roteamento global — espaço alocado mas não anunciado.",
        {"prefixes": unreachable[:30]})]
