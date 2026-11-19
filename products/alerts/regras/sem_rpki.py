# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""AS com blocos alocados e nenhum ROA (só quando a validação RPKI foi avaliada)."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado

REGRA = Regra(id="sem_rpki", categoria="rpki", severidade="aviso", versao=1,
              descricao="roa_list presente e vazio com alocação própria")


def avaliar(ctx: Contexto) -> list[dict]:
    roa_list = ctx.doc.get("roa_list")
    # só faz sentido quando a validação RPKI foi avaliada (roa_list presente, mesmo que vazio) e o AS tem alocação própria
    if roa_list is not None and ctx.has_alloc and len(roa_list) == 0:
        return [achado(
            "Sem RPKI (ROA)",
            "O AS possui blocos alocados mas nenhum ROA publicado. Sem RPKI, "
            "os prefixos ficam sujeitos a sequestro de rota sem proteção de "
            "origem.")]
    return []
