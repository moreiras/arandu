// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { server } from '../../test/server'
import { useAppStore } from '../../store/app'
import { CHAVE_RECENTES, lembrarBusca, lerRecentes } from '../../lib/buscaRecentes'
import { SearchBar } from './SearchBar'

const RESPOSTA = {
  q: 'prov', reconhecido: [], snapshot_date: '2026-09-20',
  grupos: [
    { tipo: 'asn', rotulo: 'Sistemas autônomos', total: 1, itens: [{ tipo: 'asn', titulo: 'AS64496', detalhe: 'Provedor 01 Telecom Ltda', url: '/asn/64496', selo: 'BR', motivo: 'texto' }] },
    { tipo: 'operadora', rotulo: 'Operadoras', total: 6, itens: [{ tipo: 'operadora', titulo: 'Provedor 01 Telecom Ltda', detalhe: '90.000.001/0001-29', url: '/operadora/90000001000129', selo: null, motivo: 'texto' }] },
  ],
}

function Onde() { const l = useLocation(); return <div data-testid="onde">{l.pathname}</div> }

function montar() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={['/']}>
        <SearchBar />
        <Routes><Route path="*" element={<Onde />} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  localStorage.clear()
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(http.get('*/api/v1/busca', ({ request }) => {
    const q = new URL(request.url).searchParams.get('q')
    return q === 'nada' ? HttpResponse.json({ q, reconhecido: [], grupos: [], snapshot_date: '2026-09-20' }) : HttpResponse.json(RESPOSTA)
  }))
})

describe('SearchBar (busca universal)', () => {
  it('mostra os resultados agrupados por tipo, com rótulo de grupo', async () => {
    montar()
    fireEvent.change(screen.getByRole('combobox', { name: 'Buscar no site' }), { target: { value: 'prov' } })
    expect(await screen.findByRole('group', { name: 'Sistemas autônomos' })).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Operadoras' })).toBeInTheDocument()
    expect(screen.getAllByRole('option')).toHaveLength(2)
    expect(screen.getByText(/e mais 5 em operadoras/)).toBeInTheDocument()
  })

  it('teclado: ↓ percorre, Enter abre a página e a busca vai para as últimas buscas', async () => {
    montar()
    const campo = screen.getByRole('combobox', { name: 'Buscar no site' })
    fireEvent.change(campo, { target: { value: 'prov' } })
    await screen.findAllByRole('option')
    expect(screen.getAllByRole('option')[0]).toHaveAttribute('aria-selected', 'true')
    fireEvent.keyDown(campo, { key: 'ArrowDown' })
    expect(screen.getAllByRole('option')[1]).toHaveAttribute('aria-selected', 'true')
    fireEvent.keyDown(campo, { key: 'Enter' })
    expect(screen.getByTestId('onde')).toHaveTextContent('/operadora/90000001000129')
    expect(lerRecentes()[0]).toMatchObject({ url: '/operadora/90000001000129', titulo: 'Provedor 01 Telecom Ltda' })
  })

  it('Esc fecha a lista', async () => {
    montar()
    const campo = screen.getByRole('combobox', { name: 'Buscar no site' })
    fireEvent.change(campo, { target: { value: 'prov' } })
    await screen.findAllByRole('option')
    fireEvent.keyDown(campo, { key: 'Escape' })
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('sem resultado: mensagem com o que tentar', async () => {
    montar()
    fireEvent.change(screen.getByRole('combobox', { name: 'Buscar no site' }), { target: { value: 'nada' } })
    expect(await screen.findByText(/Nada encontrado para “nada”/)).toBeInTheDocument()
  })

  it('foco sem texto mostra as últimas buscas e “limpar” apaga', () => {
    lembrarBusca({ titulo: 'AS64496', detalhe: 'Provedor 01', url: '/asn/64496' })
    montar()
    fireEvent.focus(screen.getByRole('combobox', { name: 'Buscar no site' }))
    expect(screen.getByRole('listbox', { name: 'Últimas buscas' })).toBeInTheDocument()
    expect(screen.getByText('AS64496')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'limpar' }))
    expect(localStorage.getItem(CHAVE_RECENTES)).toBeNull()
  })

  it('IP e prefixo vão direto à página do prefixo, sem consultar o servidor', async () => {
    montar()
    const campo = screen.getByRole('combobox', { name: 'Buscar no site' })
    fireEvent.change(campo, { target: { value: '177.75.0.0/16' } })
    fireEvent.keyDown(campo, { key: 'Enter' })
    await waitFor(() => expect(screen.getByTestId('onde').textContent).toMatch(/^\/prefixo\//))
  })
})

describe('últimas buscas', () => {
  beforeEach(() => localStorage.clear())
  it('põe no topo, sem repetir, até 6, e ignora lixo no armazenamento', () => {
    for (let i = 0; i < 8; i++) lembrarBusca({ titulo: `AS${i}`, detalhe: '', url: `/asn/${i}` })
    lembrarBusca({ titulo: 'AS3', detalhe: '', url: '/asn/3' })
    const r = lerRecentes()
    expect(r).toHaveLength(6)
    expect(r[0].url).toBe('/asn/3')
    expect(r.filter((x) => x.url === '/asn/3')).toHaveLength(1)
    localStorage.setItem(CHAVE_RECENTES, '{quebrado')
    expect(lerRecentes()).toEqual([])
  })
})
