# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Membro de PTT do IX.br sem registro no PeeringDB."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from core import alerta_textos

REGRA = Regra(id="sem_peeringdb", categoria="presenca", severidade="aviso", versao=1,
              descricao="ixp_member_codes não vazio e pdb_registered falso")


def avaliar(ctx: Contexto) -> list[dict]:
    membros = set(ctx.doc.get("ixp_member_codes") or [])
    if membros and not bool(ctx.doc.get("pdb_registered")):
        return [achado(
            "Sem cadastro no PeeringDB",
            alerta_textos.sem_peeringdb(len(membros)))]
    return []
