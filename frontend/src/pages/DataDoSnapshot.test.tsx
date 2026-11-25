// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../test/server'
import { useAppStore } from '../store/app'
import { MunicipiosPage } from './MunicipiosPage'
import { UsoInternetPage } from './UsoInternetPage'
import { QualidadePage } from './QualidadePage'
import { RegulatorioPage } from './RegulatorioPage'
import { MercadoIpv4Page } from './MercadoIpv4Page'
import { CommunitiesPage } from './CommunitiesPage'
import { EntrouSaiuBloco } from '../features/ptt/blocks/EntrouSaiuBloco'
import { CompararEntidades } from '../features/comparar/CompararEntidades'

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ anon: null, user: null, loading: false, requireLogin: () => true }) }))

// Datas do dataset sintético das fixtures (`snapshots.json`): 2026-09-13 é a antiga, 2026-09-20 a atual. A página tem de pedir a antiga.
const ANTIGA = '2026-09-13'
const ATUAL = '2026-09-20'

/** Toda requisição à API feita pela página. As respostas são 500: o que se confere aqui é a URL pedida, não a tela. */
let pedidos: URL[] = []
beforeEach(() => {
  pedidos = []
  useAppStore.setState({ activeDate: null, latestSnapshot: ATUAL })
  server.use(http.get('*/api/v1/*', ({ request }) => { pedidos.push(new URL(request.url)); return new HttpResponse('boom', { status: 500 }) }))
})

function Local() { const l = useLocation(); return <output data-testid="local">{l.search}</output> }
const local = () => new URLSearchParams(screen.getByTestId('local').textContent ?? '')
const montar = (el: JSX.Element, url: string) => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter initialEntries={[url]}><Local />{el}</MemoryRouter>
  </QueryClientProvider>,
)
/** Caminhos pedidos sem a data do snapshot (fora a lista de snapshots, que não é datada). */
const semData = () => pedidos.filter((u) => u.searchParams.get('date') !== ANTIGA && !u.pathname.endsWith('/snapshots')).map((u) => u.pathname + u.search)
const pediu = (caminho: string) => pedidos.some((u) => u.pathname === caminho && u.searchParams.get('date') === ANTIGA)

describe('páginas com ?date= pedem a API na data e a mantêm na navegação interna (PT-02)', () => {
  it('Municípios: lista com a data e a troca de lente mantém data, UF e porte (MUNS-E1, MUNS-E2)', async () => {
    montar(<MunicipiosPage />, `/municipios?uf=ES&dom=5000&date=${ANTIGA}`)
    await waitFor(() => expect(pediu('/api/v1/ranking/municipios')).toBe(true))
    fireEvent.click(screen.getByRole('tab', { name: 'Penetração' }))
    await waitFor(() => expect(pediu('/api/v1/territorio/ranking')).toBe(true))
    expect(local().get('date')).toBe(ANTIGA)
    expect(local().get('uf')).toBe('ES')
    expect(local().get('dom')).toBe('5000')
    expect(semData()).toEqual([])
  })

  it('Uso da Internet: tabelas, estimativas e demanda × oferta com a data (MUNS-E1, afeta USO)', async () => {
    montar(<UsoInternetPage />, `/uso-da-internet?date=${ANTIGA}`)
    await waitFor(() => expect(['/api/v1/cetic/tabelas', '/api/v1/cetic/estimativas', '/api/v1/mercado/demanda-oferta'].every(pediu)).toBe(true))
    expect(semData()).toEqual([])
  })

  it('Qualidade: resumo com a data e a troca de aba mantém a data (QUALIDADE-E1)', async () => {
    montar(<QualidadePage />, `/qualidade?aba=reclamacoes&date=${ANTIGA}`)
    await waitFor(() => expect(pediu('/api/v1/reclamacoes/resumo')).toBe(true))
    fireEvent.click(screen.getByRole('tab', { name: 'Consumidor.gov.br' }))
    await waitFor(() => expect(pediu('/api/v1/consumidor/resumo')).toBe(true))
    expect(local().get('aba')).toBe('consumidor')
    expect(local().get('date')).toBe(ANTIGA)
    fireEvent.click(screen.getByRole('tab', { name: 'Indicadores (RQUAL)' }))
    await waitFor(() => expect(pediu('/api/v1/qualidade/resumo')).toBe(true))
    expect(local().get('date')).toBe(ANTIGA)
    expect(semData()).toEqual([])
  })

  it('Regulatório: FUST com a data e a aba Multas mantém a data (QUALIDADE-E1, afeta REGULATORIO)', async () => {
    montar(<RegulatorioPage />, `/regulatorio?aba=fust&date=${ANTIGA}`)
    await waitFor(() => expect(['/api/v1/fust/resumo', '/api/v1/fust/municipios'].every(pediu)).toBe(true))
    fireEvent.click(screen.getByRole('tab', { name: 'Multas' }))
    await waitFor(() => expect(['/api/v1/multas/resumo', '/api/v1/multas/empresas'].every(pediu)).toBe(true))
    expect(local().get('aba')).toBe('multas')
    expect(local().get('date')).toBe(ANTIGA)
    fireEvent.click(screen.getByRole('tab', { name: 'Espectro' }))
    fireEvent.click(screen.getByRole('tab', { name: 'Satélites' }))
    await waitFor(() => expect(['/api/v1/espectro/resumo', '/api/v1/satelites/resumo', '/api/v1/satelites/direitos'].every(pediu)).toBe(true))
    expect(semData()).toEqual([])
  })

  it('Mercado IPv4: todas as abas com a data; aba e filtros na URL junto com a data (IPV4-E2)', async () => {
    montar(<MercadoIpv4Page />, `/mercado-ipv4?aba=espaco&uf=RJ&date=${ANTIGA}`)
    await waitFor(() => expect(pedidos.some((u) => u.pathname === '/api/v1/ipv4/espaco' && u.searchParams.get('uf') === 'RJ' && u.searchParams.get('date') === ANTIGA)).toBe(true))
    // sem fonte oficial a aba Sub-asignações não existe (IPV4-E15); a consulta dela segue pedida, com a data
    for (const aba of ['Transferências', 'Recuperação', 'Uso por terceiros']) fireEvent.click(screen.getByRole('tab', { name: aba }))
    for (const c of ['/api/v1/ipv4/transferencias', '/api/v1/ipv4/transferencias/resumo', '/api/v1/ipv4/recuperacao', '/api/v1/ipv4/uso-por-terceiros', '/api/v1/ipv4/subasignacoes']) {
      await waitFor(() => expect(pediu(c), `${c} com a data; pedidos: ${pedidos.map((u) => u.pathname + u.search).join(' ')}`).toBe(true))
    }
    expect(local().get('aba')).toBe('terceiros')
    expect(local().get('date')).toBe(ANTIGA)
    expect(local().get('uf')).toBeNull()
    expect(semData()).toEqual([])
  })

  it('Communities: a busca leva a data (IPV4-E2, afeta /communities)', async () => {
    montar(<CommunitiesPage />, `/communities?q=65535:666&date=${ANTIGA}`)
    await waitFor(() => expect(pediu('/api/v1/communities')).toBe(true))
    expect(semData()).toEqual([])
  })

  it('PTT, Quem entrou e quem saiu: eventos até o snapshot em exibição (IXP-E9)', async () => {
    montar(<EntrouSaiuBloco {...({ dados: { code: 'sp', nameMap: {} } } as any)} />, `/ixp/sp?date=${ANTIGA}`)
    await waitFor(() => expect(pedidos.some((u) => u.pathname === '/api/v1/changes' && u.searchParams.get('to') === ANTIGA && u.searchParams.get('ixp') === 'sp')).toBe(true))
  })

  it('Comparar: acrescentar uma coluna mantém a data (TRANSV-E2)', async () => {
    montar(<CompararEntidades tipo="asn" />, `/comparar?tipo=asn&ids=64496,64497&date=${ANTIGA}`)
    await waitFor(() => expect(pedidos.some((u) => u.pathname === '/api/v1/asns' && u.searchParams.get('date') === ANTIGA)).toBe(true))
    fireEvent.change(screen.getByPlaceholderText(/nome ou/), { target: { value: '64498' } })
    fireEvent.click(screen.getByRole('button', { name: 'Adicionar' }))
    await waitFor(() => expect(local().get('ids')).toBe('64496,64497,64498'))
    expect(local().get('date')).toBe(ANTIGA)
    expect(local().get('tipo')).toBe('asn')
  })
})
