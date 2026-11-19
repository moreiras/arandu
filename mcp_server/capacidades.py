# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tools do MCP geradas das capacidades declaradas (bloco `mcp:` de `serve/capabilities/*.yaml`).

`registrar_tools(mcp, loja, resolver)` cria, para cada operação com `mcp:`, a tool com o nome, o docstring e os parâmetros da
declaração; a consulta é a mesma da REST (`core/consulta_outorgas.py`). Contatos nunca passam por aqui.
Operação sem `mcp:` precisa de `sem_mcp:` com a justificativa (a matriz de cobertura falha se faltar).
"""
from __future__ import annotations

import inspect
from typing import Callable, Optional

from core.capacidades import Capacidade, Operacao, carregar_todas
from core.consulta_outorgas import consultar, limpar_cnpj, paginar


def _par(nome: str, anotacao, default=inspect.Parameter.empty) -> inspect.Parameter:
    return inspect.Parameter(nome, inspect.Parameter.POSITIONAL_OR_KEYWORD, default=default, annotation=anotacao)


def _montar(fn: Callable, op: Operacao, params: list[inspect.Parameter]) -> Callable:
    fn.__name__ = fn.__qualname__ = op.mcp.tool
    fn.__doc__ = op.mcp.descricao
    fn.__signature__ = inspect.Signature(params, return_annotation=dict)
    fn.__annotations__ = {p.name: p.annotation for p in params} | {"return": dict}
    return fn


def _tipo_do_filtro(tipo: str):
    return {"tem_asn": Optional[bool], "ativo": Optional[bool], "minimo": Optional[int]}.get(tipo, Optional[str])


def _lista(cap: Capacidade, op: Operacao, loja, resolver) -> Callable:
    mcp, sigla = op.mcp, cap.servico
    escolhidos = [f for f in op.filtros if f.nome in mcp.filtros]
    sem_dados = f" {op.dica_ausente}" if op.dica_ausente else ""

    def tool(**kw) -> dict:
        d = resolver(kw["date"])
        registros = getattr(loja(), f"{sigla}_index")(d)
        if not registros:
            raise ValueError(f"Dados {cap.rotulo} indisponíveis no snapshot {d}.{sem_dados}")
        limit, page = max(1, min(kw["limit"], mcp.limite_max)), max(1, kw["page"])
        registros = consultar(op, registros, {f.nome: kw[f.nome] for f in escolhidos}, tri_estado=True, deduplicar=mcp.deduplicar_por_cnpj)
        total, paginas, itens = paginar(registros, page, limit)
        return {"snapshot_date": d, "total": total, "page": page, "limit": limit, "pages": paginas, "items": itens}

    params = [_par(f.nome, _tipo_do_filtro(f.tipo), None) for f in escolhidos]
    params += [_par("page", int, 1), _par("limit", int, 100), _par("date", Optional[str], None)]
    return _montar(tool, op, params)


def _por_cnpj(cap: Capacidade, op: Operacao, loja, resolver) -> Callable:
    sigla, chave = cap.servico, op.mcp.chave_resposta

    def tool(cnpj: str, date: Optional[str] = None) -> dict:
        d = resolver(date)
        limpo = limpar_cnpj(cnpj)
        registros = getattr(loja(), f"{sigla}_for_cnpj")(d, limpo)
        if not registros:
            raise ValueError(f"CNPJ '{cnpj}' não encontrado nas outorgas {cap.rotulo} do snapshot {d}.")
        return {"snapshot_date": d, "cnpj": limpo, "total": len(registros), chave: registros}

    return _montar(tool, op, [_par("cnpj", str), _par("date", Optional[str], None)])


_FABRICAS = {"lista_outorgas": _lista, "por_cnpj": _por_cnpj}


def registrar_tools(mcp, loja: Callable, resolver: Callable) -> list[str]:
    """Registra no `mcp` as tools declaradas; devolve os nomes (na ordem das declarações).

    `loja` é uma função que devolve o `Store` a cada chamada (o servidor e os testes podem trocá-lo depois do import)."""
    nomes = []
    for cap in carregar_todas():
        for op in cap.operacoes:
            if op.mcp is None:
                continue
            mcp.tool()(_FABRICAS[op.tipo](cap, op, loja, resolver))
            nomes.append(op.mcp.tool)
    return nomes
