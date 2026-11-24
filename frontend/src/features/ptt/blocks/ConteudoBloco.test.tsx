// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../../test/server'
import type { PttCtx } from '../contexto'
import { ConteudoBloco } from './ConteudoBloco'

const presenca = {
  snapshot_date: '2026-11-22', ixbr_columns: [], external_columns: [],
  cdns: [
    { name: 'CDN Um', asns: [64500], ixbr: ['sp', 'rj'], external: [], ixbr_count: 2, external_count: 0 },
    { name: 'CDN Dois', asns: [64501], ixbr: ['sp'], external: [], ixbr_count: 1, external_count: 0 },
  ],
}

const montar = (code: string) => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>
      <ConteudoBloco snapshot={null} dados={{ code, date: null, mergedV4: { asn_direct: [64500] }, mergedV6: null } as unknown as PttCtx} />
    </MemoryRouter>
  </QueryClientProvider>,
)

describe('bloco Conteúdo do PTT', () => {
  it('trata a presença como adesão à lista de membros e separa a sessão com o route server', async () => {
    server.use(http.get('*/api/v1/cdns/presence', () => HttpResponse.json(presenca)))
    montar('sp')
    expect(await screen.findByText(/membros deste PTT pela lista do IX\.br/)).toBeTruthy()
    expect(screen.getByText('ASNs com sessão no route server aqui')).toBeTruthy()
    expect(screen.getByText('IPv4: AS64500')).toBeTruthy()
    expect(screen.getByText('membro sem sessão no route server nas rotas coletadas')).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/peering direto/)
  })

  it('sem CDN no PTT, não fala em peering', async () => {
    server.use(http.get('*/api/v1/cdns/presence', () => HttpResponse.json(presenca)))
    montar('ce')
    expect(await screen.findByText('Nenhuma CDN da matriz consta como membro deste PTT no snapshot.')).toBeTruthy()
  })
})
