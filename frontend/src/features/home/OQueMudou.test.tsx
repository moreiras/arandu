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
const montar = (limitReached: boolean) => {
  server.use(
    http.get('*/auth/me', () => HttpResponse.json(anon(limitReached))),
    http.post('*/api/v1/query/eventos', () => { chamadas += 1; return HttpResponse.json({ items: [], total: 3 }) }),
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

// Bloco `degradavel` da página de entrada: com o orçamento anônimo esgotado, a rota `metered` daria 403, que o navegador registra
// no console mesmo tratado. O bloco não chama a API e mostra o mesmo aviso.
describe('blocos avançados da página de entrada', () => {
  it('com orçamento esgotado não chama a rota e pede login', async () => {
    montar(true)
    expect(await screen.findByText(/entre para ver as mudanças recentes/)).toBeInTheDocument()
    expect(chamadas).toBe(0)
  })

  it('com orçamento disponível consulta normalmente', async () => {
    montar(false)
    await waitFor(() => expect(screen.getByTestId('o-que-mudou')).toHaveTextContent('3 ASes brasileiros novos'))
    expect(chamadas).toBe(1)
  })
})
