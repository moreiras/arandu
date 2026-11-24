// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../test/server'
import { useAppStore } from '../store/app'
import { CDNPage } from './CDNPage'

beforeEach(() => {
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(
    http.get('*/api/v1/cdns/presence', () => HttpResponse.json({
      snapshot_date: '2026-09-20',
      cdns: [{ name: 'Exemplo CDN', categorias: ['CDN'], asns: [64500], ixbr: ['sp'], external: [], ixbr_count: 1, external_count: 0 }],
      ixbr_columns: [{ code: 'sp', name: 'São Paulo', cdn_count: 1 }, { code: 'rj', name: 'Rio de Janeiro', cdn_count: 0 }],
      external_columns: [],
    })),
    http.get('*/api/v1/external-ixps', () => HttpResponse.json({ snapshot_date: '2026-09-20', total: 0, ixps: [] })),
  )
})

const montar = () => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><CDNPage /></MemoryRouter>
  </QueryClientProvider>,
)

describe('/cdns: grade e controles acessíveis (CDNS-E7, SEG-E1)', () => {
  it('a grade tem caption, cabeçalhos com scope e estado de cada célula em texto', async () => {
    montar()
    const tabela = await screen.findByRole('table')
    expect(tabela.querySelector('caption')).toHaveTextContent(/Presença de cada CDN/)
    for (const th of tabela.querySelectorAll('thead th')) expect(th).toHaveAttribute('scope', 'col')
    expect(within(tabela).getByRole('rowheader', { name: /Exemplo CDN/ })).toBeInTheDocument()
    expect(within(tabela).getByText('Exemplo CDN em São Paulo: presente')).toBeInTheDocument()
    expect(within(tabela).getByText('Exemplo CDN em Rio de Janeiro: ausente')).toBeInTheDocument()
    // região e contagem fora do title
    expect(within(tabela).getByText(/IX\.br \(Brasil\) · 1 CDNs/)).toBeInTheDocument()
  })

  it('botões de filtro anunciam o estado com aria-pressed', async () => {
    montar()
    await screen.findByRole('table')
    const ixbr = screen.getByRole('button', { name: /^IX\.br/ })
    expect(ixbr).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(ixbr)
    expect(ixbr).toHaveAttribute('aria-pressed', 'false')
    const cat = screen.getByRole('button', { name: 'CDN' })
    expect(cat).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(cat)
    expect(cat).toHaveAttribute('aria-pressed', 'false')
  })
})
