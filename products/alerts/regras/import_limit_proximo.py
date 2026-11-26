# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Sessão do AS com 80% ou mais do limite de importação ocupado em um route server do IX.br."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado
from core import alerta_textos

REGRA = Regra(id="import_limit_proximo", categoria="presenca", severidade="info", versao=1,
              descricao="perto_do_limite no artefato route_servers do ASN: rotas recebidas ≥ 80% do limite de importação em alguma sessão up")


def avaliar(ctx: Contexto) -> list[dict]:
    doc = getattr(ctx.store, "route_servers_asns_doc", lambda d: None)(ctx.date_str)
    ixps = ((doc or {}).get("asns") or {}).get(str(ctx.asn), {}).get("ixps") or {}
    perto = {code: x for code, x in ixps.items() if x.get("perto_do_limite")}
    if not perto:
        return []
    nomes = {row.get("code"): row.get("name") for row in getattr(ctx.store, "ixp_index", lambda d: [])(ctx.date_str)}
    partes = [f"{alerta_textos.nome_ptt(code, nomes)}: {round((x.get('max_uso_limite') or 0) * 100)}% do limite" for code, x in sorted(perto.items(), key=lambda kv: -(kv[1].get("max_uso_limite") or 0))]
    return [achado(
        "Perto do limite de importação no route server",
        f"No Alice-LG do IX.br, em {doc.get('coletado_em', '')[:10]}, ao menos uma sessão do AS tinha {round((doc.get('uso_limite') or 0.8) * 100)}% ou mais do limite de "
        f"importação ocupado: {', '.join(partes)}. Passar do limite derruba a sessão ou descarta rotas, conforme a configuração do route server.",
        {"ixps": {code: x["max_uso_limite"] for code, x in perto.items()}, "coletado_em": doc.get("coletado_em")})]
