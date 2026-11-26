# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Todas as sessões do AS nos route servers de um PTT do IX.br estão down há 7 dias ou mais."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from core import alerta_textos

REGRA = Regra(id="sessao_rs_down", categoria="presenca", severidade="aviso", versao=1,
              descricao="membro_down no artefato route_servers do ASN: todas as sessões down há 7 dias ou mais, com cache de vizinhos do Alice atual")


def avaliar(ctx: Contexto) -> list[dict]:
    doc = getattr(ctx.store, "route_servers_asns_doc", lambda d: None)(ctx.date_str)
    ixps = ((doc or {}).get("asns") or {}).get(str(ctx.asn), {}).get("ixps") or {}
    down = {code: x for code, x in ixps.items() if x.get("membro_down")}
    if not down:
        return []
    nomes = {row.get("code"): row.get("name") for row in getattr(ctx.store, "ixp_index", lambda d: [])(ctx.date_str)}
    partes = [f"{alerta_textos.nome_ptt(code, nomes)}: {x['max_dias_down']} {alerta_textos.palavra(x['max_dias_down'], 'dia', 'dias')}"
              for code, x in sorted(down.items(), key=lambda kv: -(kv[1].get("max_dias_down") or 0))]
    return [achado(
        alerta_textos.TITULO_SESSAO_RS_DOWN,
        alerta_textos.sessoes_inativas(doc.get('coletado_em', '')[:10], doc.get('dias_down', 7), partes),
        {"ixps": {code: x["max_dias_down"] for code, x in down.items()}, "coletado_em": doc.get("coletado_em")})]
