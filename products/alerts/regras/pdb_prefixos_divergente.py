# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Prefixos declarados no PeeringDB abaixo da metade do observado (max-prefix arriscado); ids por família: ..._ipv4/ipv6."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado

REGRA = Regra(id="pdb_prefixos_divergente", categoria="presenca", severidade="info", versao=1,
              descricao="observado > 2x o declarado no PeeringDB")


def avaliar(ctx: Contexto) -> list[dict]:
    pdb = ctx.doc.get("pdb") or {}
    achados = []
    for afi, declared_key, gcount in (
        ("IPv4", "info_prefixes4", ctx.doc.get("global_prefixes_v4_count") or 0),
        ("IPv6", "info_prefixes6", ctx.doc.get("global_prefixes_v6_count") or 0),
    ):
        declared = pdb.get(declared_key)
        if isinstance(declared, int) and declared > 0 and gcount > 2 * declared:
            achados.append(achado(
                f"Prefixos {afi} declarados no PeeringDB abaixo do real",
                f"PeeringDB declara {declared} prefixos {afi}, mas {gcount} são "
                "observados na full table. Peers que usam esse número como "
                "max-prefix podem derrubar a sessão.",
                {"declared": declared, "observed": gcount},
                id=f"pdb_prefixos_divergente_{afi.lower()}"))
    return achados
