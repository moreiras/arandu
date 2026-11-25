# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PTT em que o AS é membro registrado mas não faz peering direto observado."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from core import alerta_textos

REGRA = Regra(id="membro_sem_peering", categoria="presenca", severidade="aviso", versao=1,
              descricao="membro (ixp_member_codes) sem peering direto v4 nem v6")


def avaliar(ctx: Contexto) -> list[dict]:
    presence = ctx.doc.get("ixp_presence") or {}
    not_peering = []
    for code in set(ctx.doc.get("ixp_member_codes") or []):
        pres = presence.get(code) or {}
        d4 = bool((pres.get("v4") or {}).get("direct"))
        d6 = bool((pres.get("v6") or {}).get("direct"))
        if not d4 and not d6:
            not_peering.append(code)
    if not not_peering:
        return []
    return [achado(
        alerta_textos.TITULO_MEMBRO_SEM_PEERING,
        alerta_textos.membro_sem_sessao(len(not_peering)),
        {"ixps": sorted(not_peering)})]
