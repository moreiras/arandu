# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cadastro no PeeringDB sem as-set de IRR."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado

REGRA = Regra(id="sem_irr_as_set", categoria="presenca", severidade="info", versao=1,
              descricao="pdb_registered e irr_as_set vazio")


def avaliar(ctx: Contexto) -> list[dict]:
    pdb = ctx.doc.get("pdb") or {}
    if bool(ctx.doc.get("pdb_registered")) and not pdb.get("irr_as_set"):
        return [achado(
            "Sem AS-SET no IRR",
            "O cadastro no PeeringDB não informa um as-set no IRR. Sem objeto "
            "IRR, peers e provedores não conseguem montar filtros de prefixo "
            "automaticamente.")]
    return []
