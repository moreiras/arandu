# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Rotas REST geradas das capacidades declaradas (`serve/capabilities/*.yaml`).

`gerar_rotas(entidade)` devolve o `APIRouter` e as funções das rotas (`list_scms`, `scm_stats`, `get_scm`…) com a mesma assinatura,
o mesmo `operationId`, o mesmo resumo, descrição e parâmetros que as rotas escritas à mão tinham; o OpenAPI não muda. A leitura dos
dados vem do `Store` (`<sigla>_index`, `<sigla>_for_cnpj`, `<sigla>_asn_set`, `_load_<sigla>`): contatos nunca passam por aqui.

Para a política de acesso, o contrato e o MCP nada muda: a classe da rota é a de `api/auth/access_policy.py` e os contratos
(`tests/contracts/`) são os mesmos.
"""
from __future__ import annotations

import inspect
from typing import Callable, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from api.store import Store
from core.capacidades import Capacidade, Operacao, capacidade
from core.consulta_outorgas import consultar, estatisticas, limpar_cnpj, paginar


def _parametro(nome: str, default, anotacao) -> inspect.Parameter:
    return inspect.Parameter(nome, inspect.Parameter.POSITIONAL_OR_KEYWORD, default=default, annotation=anotacao)


def _com_assinatura(funcao: Callable, nome: str, parametros: list[inspect.Parameter]) -> Callable:
    funcao.__name__ = funcao.__qualname__ = nome
    funcao.__signature__ = inspect.Signature(parametros, return_annotation=dict)
    funcao.__annotations__ = {p.name: p.annotation for p in parametros} | {"return": dict}
    return funcao


def _snapshot(request: Request) -> tuple[Store, Callable[[Optional[str]], str]]:
    store: Store = request.app.state.store

    def resolver(date: Optional[str]) -> str:
        d = store.resolve_date(date)
        if d is None:
            raise HTTPException(404, "Nenhum snapshot disponível")
        return d
    return store, resolver


_DATE = lambda: _parametro("date", Query(None, description="Data do snapshot (YYYY-MM-DD)."), Optional[str])    # noqa: E731


def _lista(cap: Capacidade, op: Operacao) -> Callable:
    sigla = cap.servico
    campos = set(op.ordena_por)
    sem_dados = f"Dados de {cap.rotulo} não disponíveis para este snapshot." + (f" {op.dica_ausente}" if op.dica_ausente else "")
    pg = op.paginacao

    def lista(request: Request, **kw) -> dict:
        store, resolver = _snapshot(request)
        d = resolver(kw["date"])
        registros = getattr(store, f"{sigla}_index")(d)
        if not registros:
            raise HTTPException(404, sem_dados)
        registros = consultar(op, registros, kw, sort_by=kw["sort_by"], sort_desc=kw["sort_desc"])
        total, paginas, itens = paginar(registros, kw["page"], kw["limit"])
        return {"snapshot_date": d, "total": total, "page": kw["page"], "limit": kw["limit"], "pages": paginas, "items": itens}

    params = [_parametro("request", inspect.Parameter.empty, Request), _DATE(),
              _parametro("page", Query(1, ge=1, description=pg.get("page")), int),
              _parametro("limit", Query(100, ge=1, le=1000, description=pg.get("limit")), int)]
    for f in op.filtros:
        if f.tipo == "tem_asn":
            params.append(_parametro(f.nome, Query(False, description=f.descricao), bool))
        elif f.tipo == "ativo":
            params.append(_parametro(f.nome, Query(None, description=f.descricao), Optional[bool]))
        elif f.tipo == "minimo":
            params.append(_parametro(f.nome, Query(None, ge=0, description=f.descricao), Optional[int]))
        else:
            params.append(_parametro(f.nome, Query(None, description=f.descricao), Optional[str]))
    params += [_parametro("sort_by", Query(None, description=f"Campo para ordenação: {', '.join(sorted(campos))}"), Optional[str]),
               _parametro("sort_desc", Query(False, description=pg.get("sort_desc")), bool)]

    def chamar(request: Request, *args, **kw):
        return lista(request, **kw)
    return _com_assinatura(chamar, op.funcao, params)


def _stats(cap: Capacidade, op: Operacao) -> Callable:
    sigla = cap.servico
    sem_dados = f"Dados de {cap.rotulo} não disponíveis para este snapshot."

    def chamar(request: Request, date: Optional[str] = None) -> dict:
        store, resolver = _snapshot(request)
        d = resolver(date)
        dados = getattr(store, f"_load_{sigla}")(d)
        if not dados:
            raise HTTPException(404, sem_dados)
        return estatisticas(cap, op, store, d, dados)
    return _com_assinatura(chamar, op.funcao, [_parametro("request", inspect.Parameter.empty, Request), _DATE()])


def _por_cnpj(cap: Capacidade, op: Operacao) -> Callable:
    sigla = cap.servico

    def chamar(cnpj: str, request: Request, date: Optional[str] = None) -> dict:
        store, resolver = _snapshot(request)
        d = resolver(date)
        limpo = limpar_cnpj(cnpj)
        if len(limpo) != 14:
            raise HTTPException(400, "CNPJ inválido — informe 14 dígitos (com ou sem formatação).")
        registros = getattr(store, f"{sigla}_for_cnpj")(d, limpo)
        if not registros:
            raise HTTPException(404, f"CNPJ {limpo} não encontrado nos dados de {cap.rotulo} do snapshot '{d}'")
        return {"snapshot_date": d, "cnpj": limpo, "total": len(registros), "outorgas": registros}
    return _com_assinatura(chamar, op.funcao, [_parametro("cnpj", inspect.Parameter.empty, str),
                                                _parametro("request", inspect.Parameter.empty, Request), _DATE()])


_FABRICAS = {"lista_outorgas": _lista, "stats_outorgas": _stats, "por_cnpj": _por_cnpj}


def gerar_rotas(entidade: str) -> tuple[APIRouter, dict[str, Callable]]:
    """O router da entidade (rotas na ordem declarada: `/x/stats` antes de `/x/{cnpj}`) e as funções, por nome."""
    cap = capacidade(entidade)
    router = APIRouter()
    funcoes: dict[str, Callable] = {}
    for op in cap.operacoes:
        fn = _FABRICAS[op.tipo](cap, op)
        router.get(op.caminho, summary=op.summary, **({"description": op.descricao} if op.descricao else {}))(fn)
        funcoes[op.funcao] = fn
    return router, funcoes
