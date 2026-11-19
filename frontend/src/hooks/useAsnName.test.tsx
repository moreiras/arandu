// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../test/server'
import { useAsnNomes } from './useAsnName'

let qc: QueryClient
const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider>
beforeEach(() => { qc = new QueryClient({ defaultOptions: { queries: { retry: false } } }) })

describe('useAsnNomes', () => {
  it('pede só os ASNs informados, sem repetidos, e junta os lotes de 500', async () => {
    const pedidos: string[] = []
    server.use(http.get('*/api/v1/asns/names', ({ request }) => {
      const asns = new URL(request.url).searchParams.get('asns') ?? ''
      pedidos.push(asns)
      return HttpResponse.json({ snapshot_date: '2026-09-20', names: Object.fromEntries(asns.split(',').map((a) => [a, `AS${a}`])) })
    }))
    const asns = [...Array.from({ length: 600 }, (_, i) => i + 1), 5, 5]
    const { result } = renderHook(() => useAsnNomes(asns, '2026-09-20'), { wrapper })
    await waitFor(() => expect(Object.keys(result.current)).toHaveLength(600))
    expect(pedidos).toHaveLength(2)
    expect(pedidos[0].split(',')).toHaveLength(500)
    expect(result.current['600']).toBe('AS600')
  })

  it('sem ASNs (ou sem data) não chama a API', async () => {
    let chamadas = 0
    server.use(http.get('*/api/v1/asns/names', () => { chamadas++; return HttpResponse.json({ names: {} }) }))
    renderHook(() => useAsnNomes([], '2026-09-20'), { wrapper })
    renderHook(() => useAsnNomes([1, 2], null), { wrapper })
    await new Promise((r) => setTimeout(r, 50))
    expect(chamadas).toBe(0)
  })
})
