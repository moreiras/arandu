// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
// Respostas de erro da API para os testes de estado (`components/ui/EstadoDados`), no formato do servidor:
// 401 do `api/main.py` (login_required), 403 e 429 do orçamento anônimo (anon_limit_reached), 429 do limitador
// (`api/limites.py`, com Retry-After), 429 sem corpo nem cabeçalho (nginx), 500 e falha de rede.
import { http, HttpResponse } from 'msw'

export const RESPOSTAS_ERRO = {
  login: () => HttpResponse.json(
    { detail: 'Esta ação exige login. Faça login para continuar.', login_required: true, reason: 'historico' },
    { status: 401, headers: { 'X-Login-Required': 'true' } }),
  orcamento403: () => HttpResponse.json(
    { detail: 'Limite de navegação anônima atingido. Faça login para continuar.', anon_limit_reached: true },
    { status: 403, headers: { 'X-Anon-Limit-Reached': 'true' } }),
  orcamento429: () => HttpResponse.json(
    { detail: 'Limite de navegação anônima atingido. Faça login para continuar.', anon_limit_reached: true },
    { status: 429, headers: { 'X-Anon-Limit-Reached': 'true', 'Retry-After': '3600' } }),
  taxaComEspera: () => HttpResponse.json(
    { detail: 'Limite de uso por minuto atingido para sua rede. Tente novamente em 42 s.', rate_limited: true, janela: 'minuto', limite: 60, retry_after: 42 },
    { status: 429, headers: { 'Retry-After': '42' } }),
  taxaSemEspera: () => new HttpResponse('Too Many Requests', { status: 429 }),
  falha500: () => new HttpResponse('Internal Server Error', { status: 500 }),
  rede: () => HttpResponse.error(),
} as const

export type CasoErro = keyof typeof RESPOSTAS_ERRO

/** O que a tela tem de mostrar em cada caso (o título do `EstadoDados`). */
export const ESPERADO: Record<CasoErro, RegExp> = {
  login: /Entre para ver este dado/,
  orcamento403: /Limite de uso sem login atingido/,
  orcamento429: /Limite de uso sem login atingido/,
  taxaComEspera: /Muitas consultas em pouco tempo/,
  taxaSemEspera: /Muitas consultas em pouco tempo/,
  falha500: /Falha ao carregar/,
  rede: /Falha ao carregar/,
}

/** Todas as rotas da API respondem com o erro do caso (como com o orçamento esgotado ou a API fora do ar). */
export function apiInteiraCom(caso: CasoErro) {
  return http.all('*/api/v1/*', RESPOSTAS_ERRO[caso])
}

/** Frases que afirmam ausência de dado: nenhuma pode aparecer quando a causa é acesso, taxa ou falha. */
export const AFIRMA_AUSENCIA = /não encontrad|sem dado|não há informação|não tem ASN|não está publicad|não estão publicad|não foi publicad|indisponíve|não disponíve/i
