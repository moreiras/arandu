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
import { server } from '../test/server'
import { MudancasPage } from './MudancasPage'

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ anon: null, loading: false }) }))

const resposta = {
  total: 2, limit: 100, offset: 0,
  items: [
    { id: 'a', data: '2026-10-31', tipo: 'asn_novo', entidade: 'asn:64500', chave: '', estado: 'confirmado', asn: 64500, uf: 'PR', natureza: 'observado' },
    { id: 'b', data: '2026-10-30', tipo: 'mudanca_origem', entidade: 'prefixo:198.18.24.0/21', chave: '64503', de: 64502, para: 64503, estado: 'pendente', destaque: true, asn: 64503, uf: 'AM', natureza: 'observado' },
  ],
}

const montar = (el: JSX.Element) => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>{el}</MemoryRouter></QueryClientProvider>,
)

describe('página O que mudou', () => {
  it('lista as mudanças como diferenças observadas, sem provedor, e liga cada uma à entidade', async () => {
    let tipoPedido = ''
    server.use(
      http.get('*/api/v1/changes/summary', () => HttpResponse.json({ total: 2, por_tipo: {}, por_data: { '2026-10-30': 1, '2026-10-31': 1 }, snapshots_com_historico: 3 })),
      http.get('*/api/v1/changes', ({ request }) => { tipoPedido = new URL(request.url).searchParams.get('tipo') ?? ''; return HttpResponse.json(resposta) }),
    )
    montar(<MudancasPage />)
    await waitFor(() => expect(screen.getByText('Passou a aparecer na tabela de roteamento')).toBeTruthy())
    expect(screen.getByText(/origem mudou de AS64502 para AS64503/)).toBeTruthy()
    expect(screen.getByText('AS64500').getAttribute('href')).toBe('/asn/64500')
    expect(screen.getByText('em confirmação')).toBeTruthy()
    expect(tipoPedido).toContain('asn_novo')
    expect(tipoPedido).not.toContain('provedor')
    expect(screen.getByText(/sem causa nem intenção atribuída/)).toBeTruthy()
  })

  it('tira a data inicial da lista de snapshots e explica a confirmação por tipo', async () => {
    server.use(
      http.get('*/api/v1/brasil/snapshots', () => HttpResponse.json({ count: 3, latest: '2026-11-22', snapshots: ['2026-06-28', '2026-11-15', '2026-11-22'] })),
      http.get('*/api/v1/changes/summary', () => HttpResponse.json({ total: 0, por_tipo: {}, por_data: {}, snapshots_com_historico: 3 })),
      http.get('*/api/v1/changes', () => HttpResponse.json({ total: 0, limit: 100, offset: 0, items: [] })),
    )
    montar(<MudancasPage />)
    await waitFor(() => expect(screen.getByText(/Os snapshots publicados começam em 28\/06\/2026\./)).toBeTruthy())
    const texto = document.body.textContent ?? ''
    expect(texto).toContain('contam como confirmados no snapshot em que aparecem')
    expect(texto).not.toMatch(/outubro de 2026|persistiu por mais de um/)
  })
  it('marca a data atípica (D7) sem apagar a contagem e lista os eventos por data na tabela', async () => {
    server.use(
      http.get('*/api/v1/changes/summary', () => HttpResponse.json({
        total: 70, por_tipo: {}, por_data: { '2026-07-05': 65, '2026-07-12': 5 }, snapshots_com_historico: 2,
        datas_atipicas: { '2026-07-05': { motivo: 'o campo de ROA dos ASNs estrangeiros deixou de vir nesta data (causa a confirmar)', tipos: ['roa_perdido'] } },
      })),
      http.get('*/api/v1/changes', () => HttpResponse.json({ total: 0, limit: 100, offset: 0, items: [] })),
    )
    montar(<MudancasPage />)
    const aviso = await screen.findByTestId('data-atipica')
    expect(aviso.textContent).toMatch(/Data atípica marcada, 2026-07-05.*roa perdido.*causa a confirmar.*contagem foi mantida/)
    const tabela = screen.getByTestId('mudancas-por-data').querySelector('table')
    expect(tabela?.textContent).toContain('65')
    expect(tabela?.textContent).toContain('data atípica')
  })
})
