// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../test/server'
import { Snapshots } from './Snapshots'

const montar = () => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><Snapshots /></MemoryRouter></QueryClientProvider>,
)

describe('/snapshots', () => {
  it('rótulos de contagem dizem o que o campo mede', async () => {
    server.use(
      http.get('*/api/v1/brasil/snapshots', () => HttpResponse.json({ count: 1, latest: '2026-11-22', snapshots: ['2026-11-22'] })),
      http.get('*/api/v1/brasil/snapshots/:date', () => HttpResponse.json({ date: '2026-11-22', summary: { total_asns_br: 9129, ixp_aggregate: { br_asns_origin_union_count: 8550 } }, manifest: null })),
      http.get('*/api/v1/rpki/summary', () => HttpResponse.json({})),
      http.get('*/api/v1/outorgas/stats', () => HttpResponse.json({ total: 1 })),
    )
    montar()
    fireEvent.click(await screen.findByText('2026-11-22'))
    expect(await screen.findByText('ASNs brasileiros no índice do snapshot')).toBeTruthy()
    expect(screen.getByText('ASNs BR com rotas vistas no IX.br (originadores)')).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/alocados pelo Registro\.br|ASN BR no IX\.br/)
  })

  it('sem snapshot, nenhuma instrução de operador', async () => {
    server.use(http.get('*/api/v1/brasil/snapshots', () => HttpResponse.json({ count: 0, latest: null, snapshots: [] })))
    montar()
    expect(await screen.findByText('Nenhum snapshot publicado até agora.')).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/pipeline|summary\.json/i)
  })
})
