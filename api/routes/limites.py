# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`GET /api/v1/limites`: os tetos de uso em vigor (D9), para quem escreve scripts e para a página /dados.

Aberta e igual para todos (não depende de quem pede), por isso cacheável por URL."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Response
from pydantic import BaseModel

from api.limites_publicos import limites_publicados

router = APIRouter()


class Janela(BaseModel):
    janela: str           # minuto, hora ou dia
    segundos: int
    limite: int


class SemConta(BaseModel):
    identificacao: str
    orcamento_diario_segundos: int
    custo_por_chamada_segundos: int
    chamadas_medidas_por_dia: Optional[int] = None
    renovacao: str
    ao_esgotar: dict
    previa_linhas: int
    snapshots_atuais: int


class LimitesApi(BaseModel):
    sem_conta: list[Janela]
    com_conta: list[Janela]
    custo_por_rota: dict[str, int]
    chave_na_rest: bool


class ChaveMcp(BaseModel):
    ativa: bool
    cota_diaria: Optional[int] = None       # None = sem teto diário (MCP_COTA_DIARIA=0)
    sem_teto_diario: bool
    contagem: str


class LimitesMcp(BaseModel):
    sem_chave: list[Janela]
    com_chave: list[Janela]
    chave: ChaveMcp


class TetosContatos(BaseModel):
    por_10_minutos: int
    por_hora: int
    por_dia: int
    por_30_dias: int
    por_dia_conta_nova: int
    dias_de_conta_nova: int


class Limites(BaseModel):
    sem_conta: SemConta
    api: LimitesApi
    mcp: LimitesMcp
    contatos: TetosContatos


@router.get("/limites", summary="Limites de uso em vigor", response_model=Limites)
def limites_de_uso(response: Response) -> dict:
    """Orçamento sem conta (segundos por dia UTC e custo por chamada), janelas da API e do MCP com e sem conta, cota diária da chave de MCP,
    tetos de contatos por conta, prévia de listas e snapshots abertos. Os valores são lidos do código e da configuração da instalação; o
    estado da chave de MCP (`mcp.chave.ativa`) diz se a instalação a oferece."""
    response.headers["Cache-Control"] = "public, max-age=300"
    return limites_publicados()
