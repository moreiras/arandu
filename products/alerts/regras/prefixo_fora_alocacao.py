# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Prefixo anunciado que não está contido em nenhum bloco atribuído ao AS."""
from __future__ import annotations

from products.alerts.base import Contexto, Regra, achado, net, nets

REGRA = Regra(id="prefixo_fora_alocacao", categoria="roteamento", severidade="info", versao=1,
              descricao="prefixo global fora dos blocos RIR do AS")


def avaliar(ctx: Contexto) -> list[dict]:
    outside: list[str] = []
    for rir, glob in ((ctx.rir_v4, ctx.glob_v4), (ctx.rir_v6, ctx.glob_v6)):
        if not rir:
            continue
        rir_nets = nets(rir)
        for p in glob:
            gn = net(p)
            if gn is None:
                continue
            if not any(gn.version == r.version and (gn.subnet_of(r) or gn == r) for r in rir_nets):
                outside.append(p)
    if not outside:
        return []
    return [achado(
        "Prefixo anunciado fora da alocação",
        f"{len(outside)} prefixo(s) anunciado(s) não estão contidos em "
        "nenhum bloco atribuído a este AS no Registro.br — pode ser espaço "
        "sub-alocado por um provedor ou de terceiro.",
        {"prefixes": outside[:30]})]
