# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Um único upstream na visão global (IPv4 e/ou IPv6)."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado

REGRA = Regra(id="single_homed", categoria="presenca", severidade="aviso", versao=2,
              descricao="um único provedor inferido (nível provável ou superior) com visibilidade suficiente; sem `relacoes`, o "
                        "vizinho único da tabela global (legado)")


def _com_relacoes(rel: dict) -> list[dict]:
    afis = [afi for afi in ("v4", "v6") if (rel.get("single_homed") or {}).get(afi) is True]
    if not afis:
        return []
    prov = {afi: next((p for p in rel.get("provedores", []) if afi in p["afi"] and p["nivel"] != "possivel"), None) for afi in afis}
    rotulo = "IPv6 e IPv4" if len(afis) == 2 else ("IPv4" if afis == ["v4"] else "IPv6")
    p0 = prov[afis[0]]
    return [achado(
        "Conectividade single-homed",
        f"Só um provedor foi inferido para o AS ({rotulo}): AS{p0['asn']} (nível {p0['nivel']}, p = {p0['p']}), com visibilidade "
        "suficiente nos coletores e nos route servers. É inferência de AS_PATH, ASPA e CAIDA — não contrato; pode haver provedor "
        "que não aparece nas tabelas públicas.",
        {"provedor_v4": prov.get("v4", {}) and prov["v4"]["asn"], "provedor_v6": prov.get("v6", {}) and prov["v6"]["asn"],
         "nivel": p0["nivel"], "visibilidade": rel.get("visibilidade")})]


def avaliar(ctx: Contexto) -> list[dict]:
    rel = ctx.doc.get("relacoes")
    if rel is not None:
        return _com_relacoes(rel)
    su4 = ctx.doc.get("single_upstream_v4")
    su6 = ctx.doc.get("single_upstream_v6")
    if su4 is None and su6 is None:
        return []
    return [achado(
        "Conectividade single-homed",
        "O AS aparenta depender de um único upstream "
        + ("(IPv4)" if su4 is not None and su6 is None else
           "(IPv6)" if su6 is not None and su4 is None else "(IPv6 e IPv4)")
        + " na tabela global — risco de resiliência.",
        {"upstream_v4": su4, "upstream_v6": su6})]
