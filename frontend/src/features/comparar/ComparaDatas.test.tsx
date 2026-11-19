// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { ComparaDatas } from './ComparaDatas'

vi.mock('../../auth/AuthContext', () => ({ useAuth: () => ({ requireLogin: () => true }) }))

describe('Comparar datas', () => {
  it('mostra os totais das duas últimas datas, a variação e as mudanças sem os eventos de provedor', async () => {
    let pedido = ''
    server.use(http.get('*/api/v1/snapshots/diff', ({ request }) => {
      pedido = new URL(request.url).search
      return HttpResponse.json({
        a: '2026-09-13', b: '2026-09-20',
        totais: { n_asns: { a: 100, b: 104, variacao: 4 }, users: { a: 1000, b: 900, variacao: -100 } },
        eventos: { entre: ['2026-09-13', '2026-09-20'], total: 3, por_tipo: { asn_novo: { confirmado: 2, pendente: 1, revertido: 0 }, provedor_novo: { confirmado: 9, pendente: 0, revertido: 0 } } },
        nota: 'Totais por UF somam ASNs com sede na UF; usuários são estimativas da APNIC.',
      })
    }))
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><ComparaDatas /></MemoryRouter></QueryClientProvider>)
    await waitFor(() => expect(screen.getByText('ASNs brasileiros (por UF da sede)')).toBeTruthy())
    expect(pedido).toContain('a=')
    expect(pedido).toContain('b=')
    expect(screen.getByText('+4')).toBeTruthy()
    expect(screen.getByText('-100')).toBeTruthy()
    expect(screen.getByText(/asn novo: 2 confirmadas, 1 em confirmação/)).toBeTruthy()
    expect(screen.queryByText(/provedor novo/)).toBeNull()
  })
})
