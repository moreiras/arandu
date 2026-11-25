// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/**
 * Tetos de uso sem conta, como publicados em /dados e no Sobre (D9). São os **padrões** do código; a instalação pode mudá-los por variável de ambiente.
 * `tests/unit/test_tetos_publicados.py` confere cada número com o padrão de `api/auth/anon_session.py`, `api/limites.py` e `mcp_server/chave.py`.
 */
export const TETOS = {
  /** `ANON_API_CLIENT_COST_SECONDS`: custo, em segundos de orçamento, de cada chamada medida de um script sem sessão. */
  custoPorChamadaSegundos: 3,
  /** `ANON_SESSION_LIMIT_MINUTES` (10), em segundos: orçamento de uso medido sem login, renovado à meia-noite UTC para quem é identificado pela rede. */
  orcamentoDiarioSegundos: 600,
  /** `MCP_COTA_DIARIA`: requisições POST ao MCP por dia UTC, com chave. */
  mcpCotaDiariaComChave: 1000,
  /** Limitador por rede da API sem conta (`api/limites.py`, `PADROES['api']['anon']`). */
  apiAnonimoPorMinuto: 120,
  apiAnonimoPorHora: 1500,
  apiAnonimoPorDia: 6000,
  /** Limitador por rede do MCP sem chave (`PADROES['mcp']['anon']`). */
  mcpAnonimoPorMinuto: 60,
  mcpAnonimoPorHora: 1000,
  mcpAnonimoPorDia: 5000,
} as const

/** Chamadas medidas que o orçamento diário comporta para um script sem sessão (600 s ÷ 3 s). */
export const CHAMADAS_POR_DIA_SEM_SESSAO = TETOS.orcamentoDiarioSegundos / TETOS.custoPorChamadaSegundos
