# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Perfil da conta: dados mínimos, uso, chave de MCP, "sair de todos os dispositivos" e pedido de exclusão (30 dias).

Fica em `/auth/perfil` (fora de `/api/v1` e do OpenAPI público). Exige a sessão de uma conta (cookie `auth_token`): IP da allowlist não tem conta. Os
verbos que mudam estado exigem o cabeçalho `X-Arandu-Acao` (um cabeçalho próprio força preflight de CORS e barra formulário de outro site).
A chave completa aparece uma única vez, na resposta de `POST /chave-mcp` (`Cache-Control: no-store`); nada a registra.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api import uso_conta
from api.auth import chaves_mcp, contas, sessao
from api.auth.config import get_auth_config
from api.ratelimit import limiter

router = APIRouter(prefix="/auth/perfil", tags=["perfil"], include_in_schema=False)
_SEM_CACHE = {"Cache-Control": "no-store"}


def _conta(request: Request):
    cfg = get_auth_config(request)
    user = sessao.usuario_do_cookie(request.cookies.get("auth_token"), cfg.jwt_secret, cfg.data_dir)
    if not user:
        raise HTTPException(401, "Esta ação exige login. Faça login para continuar.")
    return cfg, user


def _acao(request: Request) -> None:
    if not request.headers.get("X-Arandu-Acao"):
        raise HTTPException(400, "Cabeçalho X-Arandu-Acao ausente.")


def _sair(resp: JSONResponse) -> JSONResponse:
    resp.delete_cookie("auth_token", path="/")
    return resp


@router.get("")
def perfil(request: Request) -> JSONResponse:
    cfg, user = _conta(request)
    c = contas.por_id(cfg.data_dir, user["conta_id"])
    return JSONResponse({
        "email": c.email, "nome": c.nome, "provedor": c.provedor, "criada_em": c.criada_em[:10], "ultimo_acesso": c.ultimo_acesso[:10],
        "chave_mcp": {"disponivel": chaves_mcp.ativa(), "ativa": chaves_mcp.da_conta(cfg.data_dir, c.conta_id) if chaves_mcp.ativa() else None},
        "uso": uso_conta.resumo_dias(cfg.data_dir, c.conta_id, 30),
    }, headers=_SEM_CACHE)


class _PedidoChave(BaseModel):
    rotulo: Optional[str] = None


@router.post("/chave-mcp")
@limiter.limit("10/hour")
def gerar_chave(request: Request, corpo: _PedidoChave) -> JSONResponse:
    _acao(request)
    cfg, user = _conta(request)
    if not chaves_mcp.ativa():
        raise HTTPException(404, "A chave de MCP ainda não está disponível.")
    chave, meta = chaves_mcp.gerar(cfg.data_dir, user["conta_id"], corpo.rotulo)
    return JSONResponse({"chave": chave, **meta, "aviso": "Guarde a chave agora: ela não será mostrada de novo."}, headers=_SEM_CACHE)


@router.delete("/chave-mcp")
def revogar_chave(request: Request) -> JSONResponse:
    _acao(request)
    cfg, user = _conta(request)
    return JSONResponse({"revogada": chaves_mcp.revogar(cfg.data_dir, user["conta_id"])}, headers=_SEM_CACHE)


@router.post("/sair-de-todos")
def sair_de_todos(request: Request) -> JSONResponse:
    _acao(request)
    cfg, user = _conta(request)
    contas.sair_de_todos(cfg.data_dir, user["conta_id"])
    sessao.limpar_cache()
    return _sair(JSONResponse({"ok": True}, headers=_SEM_CACHE))


@router.post("/excluir")
@limiter.limit("5/hour")
def solicitar_exclusao(request: Request) -> JSONResponse:
    """Desativa a conta agora e agenda o apagamento para 30 dias depois (nunca imediato)."""
    _acao(request)
    cfg, user = _conta(request)
    chaves_mcp.revogar(cfg.data_dir, user["conta_id"])
    c = contas.solicitar_exclusao(cfg.data_dir, user["conta_id"])
    sessao.limpar_cache()
    return _sair(JSONResponse({"exclusao_efetiva_em": c.exclusao_efetiva_em(), "prazo_dias": contas.PRAZO_EXCLUSAO_DIAS}, headers=_SEM_CACHE))
