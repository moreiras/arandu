# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Todas as sessões do AS nos route servers de um PTT do IX.br estão down há 7 dias ou mais."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado

REGRA = Regra(id="sessao_rs_down", categoria="presenca", severidade="aviso", versao=1,
              descricao="membro_down no artefato route_servers do ASN: todas as sessões down há 7 dias ou mais, com cache de vizinhos do Alice atual")


def avaliar(ctx: Contexto) -> list[dict]:
    doc = getattr(ctx.store, "route_servers_asns_doc", lambda d: None)(ctx.date_str)
    ixps = ((doc or {}).get("asns") or {}).get(str(ctx.asn), {}).get("ixps") or {}
    down = {code: x for code, x in ixps.items() if x.get("membro_down")}
    if not down:
        return []
    partes = [f"{code.upper()} ({x['max_dias_down']} dias)" for code, x in sorted(down.items(), key=lambda kv: -(kv[1].get("max_dias_down") or 0))]
    return [achado(
        "Sessões down nos route servers do IX.br",
        f"No Alice-LG do IX.br, em {doc.get('coletado_em', '')[:10]}, todas as sessões do AS estavam down há {doc.get('dias_down', 7)} dias ou mais nos route servers de: "
        f"{', '.join(partes)}. É o estado medido no route server; não diz a causa e o AS pode manter peering bilateral no PTT.",
        {"ixps": {code: x["max_dias_down"] for code, x in down.items()}, "coletado_em": doc.get("coletado_em")})]
