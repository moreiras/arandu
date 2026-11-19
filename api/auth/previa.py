# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Prévia anônima de listas e histórico, a mesma no site, no corpo do `/query` e no MCP.

O `classify` (`access_policy.py`) só vê a query string; o corpo do `/query` e os argumentos das tools do MCP passam por `conferir`.
"""
from __future__ import annotations

from typing import Sequence

from api.auth.access_policy import PREVIEW_LIMIT

HISTORICO = frozenset({"historico_serie", "historico_mudancas", "historico_acessos"})
COLECOES_HISTORICO = frozenset({"eventos", "series_asn"})
COMO_TER_CHAVE = ("Sem chave de MCP o acesso é uma prévia, como no site sem login. Para mais, entre no site, gere a chave em /perfil e configure o "
                  "cliente com o cabeçalho `Authorization: Bearer <chave>`.")


class PreviaExcedida(ValueError):
    """Pedido além da prévia anônima: a tool devolve a mensagem ao cliente (como erro de validação)."""


COMO_FAZER_LOGIN = "Faça login no site para ver mais."


def conferir(nome: str, args: dict, recentes: Sequence[str], como: str = COMO_TER_CHAVE) -> dict:
    """Aplica a prévia anônima aos argumentos efetivos (já com os padrões) de uma tool. Devolve os argumentos (talvez com `limit` reduzido)."""
    explicitos = args.pop("__explicitos__", set())
    lim = args.get("limit")
    if isinstance(lim, int) and lim > PREVIEW_LIMIT:
        if "limit" in explicitos:
            raise PreviaExcedida(f"limit={lim}: sem login ou chave, até {PREVIEW_LIMIT} itens. {como}")
        args["limit"] = PREVIEW_LIMIT
    pag = args.get("page")
    if isinstance(pag, int) and pag > 1:
        raise PreviaExcedida(f"page={pag}: sem login ou chave, só a primeira página. {como}")
    off = args.get("offset")
    if isinstance(off, int) and off > 0:
        raise PreviaExcedida(f"offset={off}: sem login ou chave, só o começo da lista. {como}")
    data = args.get("date")
    if recentes and isinstance(data, str) and data and data not in recentes:
        raise PreviaExcedida(f"date={data}: sem login ou chave, só os snapshots {', '.join(recentes)}. {como}")
    historico = nome in HISTORICO or (nome == "query" and args.get("collection") in COLECOES_HISTORICO)
    if historico and recentes:
        inicio = args.get("de") or args.get("date")
        if not (isinstance(inicio, str) and inicio >= min(recentes)):
            raise PreviaExcedida(f"{nome}: sem login ou chave, o histórico só a partir de {min(recentes)} (informe `de`). {como}")
    return args
