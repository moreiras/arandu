# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Nome de exibição de um grupo societário, por regra visível na página (decisão D5; substitui o nome mais longo).

Duas regras, nesta ordem, e o resultado diz qual valeu:

  1. `marca_curada`: uma marca da tabela curada (`config/curada_marcas_operadoras.yaml`) cujas raízes de CNPJ estão **todas** no grupo; havendo mais de uma,
     a que cobre mais raízes e, em empate, a primeira da tabela. Marca que cobre só parte das raízes de um conjunto maior não nomeia um grupo menor.
  2. `maior_acesso_sici`: o nome do CNPJ do grupo com mais acessos fixos declarados ao SICI; em empate (ou sem acesso declarado nenhum), o de menor CNPJ.

O nome é um rótulo de navegação do conjunto inferido: não afirma quem controla quem nem que o grupo é "o" grupo econômico da marca.
"""
from __future__ import annotations

from typing import Callable, Iterable

REGRAS = {
    "marca_curada": "marca curada que cobre as raízes de CNPJ do grupo",
    "maior_acesso_sici": "nome do CNPJ do grupo com mais acessos fixos declarados ao SICI",
    "menor_cnpj": "nome do menor CNPJ do grupo (nenhum declara acessos fixos ao SICI)",
}


def nome_do_grupo(cnpjs: Iterable[str], acessos: dict[str, int], nome_de: Callable[[str], str], curada: dict | None) -> dict:
    """`{"nome", "nome_regra", "nome_regra_texto", "nome_base"}` para os CNPJs do grupo; `acessos` = acessos fixos declarados por CNPJ."""
    cnpjs = sorted(set(cnpjs))
    raizes = {c[:8] for c in cnpjs}
    melhor = None
    for m in ((curada or {}).get("marcas") or {}).values():
        rs = set(m["raizes"])
        if rs and rs <= raizes and (melhor is None or len(rs) > len(melhor["raizes"])):
            melhor = m
    if melhor:
        return {"nome": melhor["marca"], "nome_regra": "marca_curada", "nome_regra_texto": REGRAS["marca_curada"], "nome_base": melhor["base"]}
    com = [c for c in cnpjs if acessos.get(c, 0) > 0]
    if com:
        c = min(com, key=lambda x: (-acessos[x], x))
        return {"nome": nome_de(c) or c, "nome_regra": "maior_acesso_sici", "nome_regra_texto": REGRAS["maior_acesso_sici"], "nome_base": c}
    c = cnpjs[0]
    return {"nome": nome_de(c) or c, "nome_regra": "menor_cnpj", "nome_regra_texto": REGRAS["menor_cnpj"], "nome_base": c}
