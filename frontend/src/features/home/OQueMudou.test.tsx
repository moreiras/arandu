// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../../test/server'
import { useAppStore } from '../../store/app'
import { AuthProvider } from '../../auth/AuthContext'
import { OQueMudou } from './OQueMudou'

const anon = (limitReached: boolean) => ({
  authenticated: false,
  anon: { active_seconds: 0, limit_seconds: 600, limit_reached: limitReached, heartbeat_interval_seconds: 60, inactivity_timeout_seconds: 120 },
})

let chamadas = 0
const resposta = { snapshot_date: '2026-09-20', destaques: {}, o_que_mudou: { total: 3, de: '2026-09-13', mais_recente: '2026-09-20' } }
const montar = (limitReached: boolean, corpo: unknown = resposta) => {
  server.use(
    http.get('*/auth/me', () => HttpResponse.json(anon(limitReached))),
    http.get('*/api/v1/brasil/destaques', () => { chamadas += 1; return HttpResponse.json(corpo as object) }),
  )
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter><AuthProvider><OQueMudou /></AuthProvider></MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  chamadas = 0
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
})

// TRANSV-E20: o "O que mudou" da home vem de `/brasil/destaques`, rota fixa e aberta; não depende do orçamento anônimo e só conta a janela dos snapshots atuais.
describe('O que mudou na home', () => {
  it('consulta a rota aberta mesmo com o orçamento anônimo esgotado e diz desde quando conta', async () => {
    montar(true)
    await waitFor(() => expect(screen.getByTestId('o-que-mudou')).toHaveTextContent('3 ASes brasileiros novos confirmados na tabela de roteamento desde 13/09/2026, o mais recente em 20/09/2026'))
    expect(chamadas).toBe(1)
  })

  it('sem ASes novos na janela diz desde quando, em vez de afirmar "nos últimos snapshots"', async () => {
    montar(false, { ...resposta, o_que_mudou: { total: 0, de: '2026-09-13', mais_recente: null } })
    await waitFor(() => expect(screen.getByTestId('o-que-mudou')).toHaveTextContent('nenhum AS brasileiro novo confirmado desde 13/09/2026'))
  })
})
