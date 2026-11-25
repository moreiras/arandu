// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { SeriesDaFamilia } from './SeriesDaFamilia'

vi.mock('../../auth/AuthContext', () => ({ useAuth: () => ({ anon: true, loading: false }) }))

const pontos = ['2026-10-04', '2026-10-11', '2026-10-18', '2026-10-25', '2026-11-01'].map((date, i) => (
  { date, valor: 50 + i, comparavel_com_anterior: i === 0 ? null : true, motivos: [], avisos: [] }))
const serie = {
  familia: 'roteamento', total: 5, snapshots: pontos.map((p) => p.date),
  regra: { versao: 1, min_pontos_linha: 4, limiar_cobertura: 0.25, motivos: {}, texto: ['Variação só entre pontos comparáveis.'] },
  metricas: [{ id: 'rpki_valido_pct_v6', rotulo: 'Rotas IPv6 com origem RPKI válida', unidade: '%', selo: 'fato', fonte: 'RouteViews e VRPs do RPKI', desenhar_linha: true, segmentos: [[0, 4]], pontos }],
}

describe('SeriesDaFamilia', () => {
  it('sem login pede a série inteira (sem from) e não esconde a tendência nem avisa de login', async () => {
    let url: URL | null = null
    server.use(http.get('*/api/v1/history/brasil/series', ({ request }) => { url = new URL(request.url); return HttpResponse.json(serie) }))
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><SeriesDaFamilia familia="roteamento" titulo="Estado RPKI" /></QueryClientProvider>)
    await waitFor(() => expect(screen.getByTestId('series-nacionais')).toBeTruthy())
    expect(url).not.toBeNull()
    expect(url!.searchParams.get('familia')).toBe('roteamento')
    expect(url!.searchParams.has('from')).toBe(false)
    expect(screen.queryByText(/entre para ver a série inteira/i)).toBeNull()
    expect(screen.getByText('Rotas IPv6 com origem RPKI válida')).toBeTruthy()
  })
})
