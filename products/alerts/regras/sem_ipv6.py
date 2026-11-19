# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Sem IPv6: presença em IPv4 sem nenhum prefixo IPv6."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado

REGRA = Regra(id="sem_ipv6", categoria="roteamento", severidade="aviso", versao=1,
              descricao="AS com IPv4 e nenhum prefixo IPv6 alocado nem anunciado")


def avaliar(ctx: Contexto) -> list[dict]:
    if (ctx.rir_v4 or ctx.glob_v4) and not (ctx.rir_v6 or ctx.glob_v6):
        return [achado(
            "Sem IPv6",
            "O AS tem presença em IPv4 mas nenhum prefixo IPv6 alocado nem "
            "anunciado. IPv6 é requisito de boas práticas para novas redes.")]
    return []
