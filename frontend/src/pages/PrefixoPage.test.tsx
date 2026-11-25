// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { fixtures, server } from '../test/server'
import { useAppStore } from '../store/app'
import { blocosDe } from '../features/entidade/registry'
import '../features/prefixo'
import { PrefixoPage } from './PrefixoPage'
import { SearchBar } from '../components/layout/SearchBar'

const info = { prefix: '198.18.0.0/24', ip_version: 4, origin_asn: 64496, uf: 'ES', country: 'BR', geo_confidence: 'city_centroid', geo_source: 'dbip-lite-2026-09',
  snapshot_date: '2026-09-20', geo_org: { name: 'Provedor 01 Telecom Ltda', cnpj: '90000001000100' } }

function montar(caminho: string) {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[caminho]}><Routes><Route path="/prefixo/*" element={<PrefixoPage />} /></Routes></MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(
    http.get('*/api/v1/brasil/snapshots/:date', () => HttpResponse.json({ date: '2026-09-20', summary: null, manifest: { sources: [{ id: 'rpki_collector', as_of: '2026-09-20', frescor: 'ok' }] } })),
    http.get('*/api/v1/prefixes/*', ({ request }) => {
      const p = new URL(request.url).pathname.replace('/api/v1/prefixes/', '')
      return p === '198.18.0.0/24' ? HttpResponse.json(info) : new HttpResponse('nada', { status: 404 })
    }),
  )
})

describe('página de prefixo', () => {
  it('blocos na ordem do plano', () => {
    expect(blocosDe('prefixo').map((b) => b.id)).toEqual(['origem', 'rpki', 'ptts', 'registro', 'geo', 'moas', 'ciclo-de-vida'])
  })

  it('mostra origem, validação RPKI com o ROA que cobre, PTTs, Registro.br e geolocalização', async () => {
    montar('/prefixo/198.18.0.0/24')
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent('198.18.0.0/24')
    expect(await screen.findByText('válido')).toBeInTheDocument()                       // rpki_validation do fixture do ASN 64496
    expect(await screen.findByText('lacnic')).toBeInTheDocument()                        // o ROA que cobre o prefixo, com o TA
    expect(screen.queryByText(/Nenhum ROA cobre/)).toBeNull()
    expect(await screen.findByRole('link', { name: 'ZA' })).toHaveAttribute('href', '/ixp/za')        // PTT onde aparece
    expect(screen.getByText(/Alocado ao AS pelo Registro.br/)).toBeInTheDocument()
    expect(screen.getByText('centro do município')).toBeInTheDocument()
    expect(screen.getAllByTestId('proveniencia').length).toBeGreaterThanOrEqual(5)
  })

  it('prefixo malformado explica sem chamar a API; prefixo ausente diz que não consta', async () => {
    montar('/prefixo/abc')
    expect(await screen.findByText('Prefixo inválido')).toBeInTheDocument()
  })

  it('prefixo bem formado mas fora do Registro.br: "não encontrado"', async () => {
    montar('/prefixo/203.0.113.0/24')
    expect(await screen.findByText('Prefixo não encontrado')).toBeInTheDocument()
  })

  it('MOAS: indisponível, sem afirmar ausência e sem baixar a análise de roteamento (PFX-E3)', async () => {
    let chamadas = 0
    server.use(http.get('*/api/v1/routing-analysis', () => { chamadas += 1; return HttpResponse.json({ moas: null }) }))
    montar('/prefixo/198.18.0.0/24')
    const aviso = await screen.findByTestId('moas-indisponivel')
    expect(aviso.textContent).toMatch(/não medida neste snapshot/)
    expect(aviso.textContent).toMatch(/limite da coleta, não ausência de eventos/)
    expect(document.body.textContent).not.toMatch(/Nenhuma origem múltipla/)
    expect(chamadas).toBe(0)
  })
})

describe('busca global aceita prefixo', () => {
  it('Enter com um CIDR leva à página do prefixo', async () => {
    let destino = ''
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={['/']}>
          <SearchBar />
          <Routes><Route path="/prefixo/*" element={<div data-testid="alvo">{(destino = 'ok')}</div>} /><Route path="*" element={null} /></Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    const campo = screen.getByPlaceholderText(/prefixo/)
    fireEvent.change(campo, { target: { value: '177.75.0.0/16' } })
    fireEvent.keyDown(campo, { key: 'Enter' })
    expect(await screen.findByTestId('alvo')).toBeInTheDocument()
    expect(destino).toBe('ok')
  })
})
