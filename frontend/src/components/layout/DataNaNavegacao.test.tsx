// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { AppLayout } from './AppLayout'
import { Link } from './LinkDatado'
import { AcoesEntidade } from '../entidade/AcoesEntidade'
import { useAppStore } from '../../store/app'

vi.mock('../../auth/AuthContext', () => ({ useAuth: () => ({ user: null, anon: null, loading: false, requireLogin: () => true }) }))

// Datas do dataset sintético das fixtures (`snapshots.json`): 2026-09-13 é a antiga, 2026-09-20 a atual.
const ANTIGA = '2026-09-13'
const ATUAL = '2026-09-20'

function Local() {
  const l = useLocation()
  return <output data-testid="local">{l.pathname + l.search}</output>
}
const local = () => screen.getByTestId('local').textContent

function Pagina() {
  const navigate = useNavigate()
  return (
    <div>
      <Local />
      <button type="button" onClick={() => navigate('/b')}>ir para b</button>
      <button type="button" onClick={() => navigate(-1)}>voltar</button>
      <Link to="/ixp/sp#bloco-membros">PTT</Link>
      <AcoesEntidade tipo="operadora" id="04596419000109" />
    </div>
  )
}

const montar = (entradas: string[], indice = entradas.length - 1) => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter initialEntries={entradas} initialIndex={indice}>
      <Routes><Route element={<AppLayout />}><Route path="*" element={<Pagina />} /></Route></Routes>
    </MemoryRouter>
  </QueryClientProvider>,
)

beforeEach(() => { useAppStore.setState({ activeDate: null, latestSnapshot: null }) })

describe('data do snapshot na navegação (PT-02)', () => {
  it('links de entidade e as ações Comparar e Relatório levam a data da página (TRANSV-E2, REL-E6)', async () => {
    montar([`/operadora/04596419000109?date=${ANTIGA}`])
    await waitFor(() => expect(screen.getByText('PTT').getAttribute('href')).toBe(`/ixp/sp?date=${ANTIGA}#bloco-membros`))
    expect(screen.getByText('Comparar com outros').getAttribute('href')).toBe(`/comparar?tipo=operadora&ids=04596419000109&date=${ANTIGA}`)
    expect(screen.getByText('Relatório de uma página').getAttribute('href')).toBe(`/relatorio/operadora/04596419000109?date=${ANTIGA}`)
  })

  it('sem data na URL os links seguem sem data (snapshot mais recente)', async () => {
    montar(['/operadora/04596419000109'])
    await waitFor(() => expect(screen.getByText('PTT').getAttribute('href')).toBe('/ixp/sp#bloco-membros'))
  })

  it('navegar para um endereço sem data mantém a data escolhida em vez de zerá-la (AppLayout)', async () => {
    montar([`/a?date=${ANTIGA}`])
    await waitFor(() => expect(local()).toBe(`/a?date=${ANTIGA}`))
    fireEvent.click(screen.getByText('ir para b'))
    await waitFor(() => expect(local()).toBe(`/b?date=${ANTIGA}`))
    expect(useAppStore.getState().activeDate).toBe(ANTIGA)
  })

  it('o Voltar do navegador obedece à URL do histórico', async () => {
    montar(['/b', `/a?date=${ANTIGA}`])
    await waitFor(() => expect(local()).toBe(`/a?date=${ANTIGA}`))
    fireEvent.click(screen.getByText('voltar'))
    await waitFor(() => expect(local()).toBe('/b'))
    await waitFor(() => expect(useAppStore.getState().activeDate).not.toBe(ANTIGA))
  })

  it('o seletor de snapshot cria entrada no histórico (Voltar desfaz) e escolher o atual tira a data', async () => {
    montar(['/a'])
    const seletor = await screen.findAllByRole('combobox', { name: 'Snapshot' })
    fireEvent.change(seletor[0], { target: { value: ANTIGA } })
    await waitFor(() => expect(local()).toBe(`/a?date=${ANTIGA}`))
    fireEvent.click(screen.getByText('voltar'))
    await waitFor(() => expect(local()).toBe('/a'))

    fireEvent.change(screen.getAllByRole('combobox', { name: 'Snapshot' })[0], { target: { value: ANTIGA } })
    await waitFor(() => expect(local()).toBe(`/a?date=${ANTIGA}`))
    fireEvent.change(screen.getAllByRole('combobox', { name: 'Snapshot' })[0], { target: { value: ATUAL } })
    await waitFor(() => expect(local()).toBe('/a'))
    fireEvent.click(screen.getByText('ir para b'))
    await waitFor(() => expect(local()).toBe('/b'))
  })

  it('link de entidade em HTML cru (balão de mapa) navega pela SPA com a data', async () => {
    montar([`/a?date=${ANTIGA}`])
    await waitFor(() => expect(local()).toBe(`/a?date=${ANTIGA}`))
    const balao = document.createElement('div')
    balao.innerHTML = '<a href="/operadora/04596419000109">EMPRESA</a>'
    screen.getByTestId('local').parentElement!.appendChild(balao)
    fireEvent.click(screen.getByText('EMPRESA'))
    await waitFor(() => expect(local()).toBe(`/operadora/04596419000109?date=${ANTIGA}`))
  })
})
