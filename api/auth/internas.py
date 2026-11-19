# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Rotas internas, só para o contêiner do MCP: verificar a chave e enviar eventos de uso por conta.

Fora de `/api/v1` (isentas do guard) e que o nginx não encaminha. Exigem `X-Internal-Token` = `INTERNAL_API_TOKEN` (sem fallback de loopback).
A chave chega no corpo (nunca na URL) e não é registrada; o cliente é o hash diário do IP+navegador que o MCP já calcula.
"""
from __future__ import annotations

import os
import secrets
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api import uso_conta
from api.auth import chaves_mcp, contas
from api.auth.config import get_auth_config
from api.auth.tentativas import LimiteTentativas

_log = structlog.get_logger(__name__)
router = APIRouter(prefix="/internal", tags=["interno"], include_in_schema=False)
limite = LimiteTentativas()


def _token(request: Request) -> None:
    esperado = os.environ.get("INTERNAL_API_TOKEN", "")
    if not esperado or not secrets.compare_digest(request.headers.get("X-Internal-Token", ""), esperado):
        raise HTTPException(403, "Acesso restrito")


class _Verificar(BaseModel):
    chave: str = Field(max_length=200)
    cliente: str = Field(default="?", max_length=64)


@router.post("/mcp-chave/verificar")
def verificar(request: Request, corpo: _Verificar) -> JSONResponse:
    _token(request)
    if not chaves_mcp.ativa():
        return JSONResponse({"valida": False, "desligada": True})
    espera = limite.espera(corpo.cliente)
    if espera:
        return JSONResponse({"valida": False, "limitada": True}, status_code=429, headers={"Retry-After": str(espera)})
    cfg = get_auth_config(request)
    conta_id = chaves_mcp.verificar(cfg.data_dir, corpo.chave)
    c = contas.por_id(cfg.data_dir, conta_id) if conta_id else None
    if c is None or c.desativada:                           # conta em exclusão: a chave já foi revogada, mas não custa conferir
        limite.falha(corpo.cliente)
        # com o limite global saturado, só a chave INVÁLIDA recebe 429; senão, quem saturasse o
        # global (variando o User-Agent) negaria serviço a todas as chaves válidas fora do cache por 10 min. O global vira alerta.
        if limite.saturado():
            _log.warning("mcp_chave_limite_global_saturado")
            return JSONResponse({"valida": False, "limitada": True}, status_code=429, headers={"Retry-After": "60"})
        return JSONResponse({"valida": False})
    limite.sucesso(corpo.cliente)
    return JSONResponse({"valida": True, "conta_id": conta_id})


class _Evento(BaseModel):
    conta: str = Field(max_length=64)
    rota: str = Field(max_length=200)
    status: int = 200
    bytes: int = 0
    ms: float = 0.0
    classe: str = Field(default="tool", max_length=20)


class _Eventos(BaseModel):
    eventos: list[_Evento] = Field(max_length=500)


@router.post("/uso-conta")
def receber_uso(request: Request, corpo: _Eventos) -> JSONResponse:
    _token(request)
    cfg = get_auth_config(request)
    for e in corpo.eventos:
        uso_conta.registrar(cfg.data_dir, e.conta, "mcp", e.rota, e.status, e.bytes, e.ms, e.classe)
    return JSONResponse({"recebidos": len(corpo.eventos)})
