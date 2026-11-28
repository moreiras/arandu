// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { useAppStore } from '../../store/app'
import { AREA_NACIONAL } from './areaInfluencia.fixture'
import { ABAS_MAPA, AreaInfluenciaAbas } from './AreaInfluenciaAbas'

const propsMapa = vi.fn()
const montagensVoronoi = vi.fn()
vi.mock('../../components/maps/Coropletico', () => ({ Coropletico: (p: { descricao: string }) => { propsMapa(p); return <div data-testid="coropletico" aria-label={p.descricao} /> } }))
vi.mock('../../components/maps/IXPVoronoiMap', () => ({ IXPVoronoiMap: (p: { ixps: unknown[]; date?: string }) => { montagensVoronoi(p); return <div data-testid="voronoi">voronoi {p.ixps.length} {p.date}</div> } }))

const ixps: any[] = [{ code: 'za' }, { code: 'zb' }]
let visoesPedidas: string[] = []

beforeEach(() => {
  propsMapa.mockClear(); montagensVoronoi.mockClear(); visoesPedidas = []
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(http.get('*/api/v1/ixps/area-influencia', ({ request }) => {
    const visao = new URL(request.url).searchParams.get('visao') ?? ''
    visoesPedidas.push(visao)
    return HttpResponse.json({ ...AREA_NACIONAL, visao, rotulo_visao: visao })
  }))
})

function montar() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><AreaInfluenciaAbas ixps={ixps} date="2026-09-20" /></MemoryRouter></QueryClientProvider>)
}

describe('mapa de /ixps com três abas', () => {
  it('abas na ordem pedida, como tablist, a primeira aberta e ligada ao painel', async () => {
    montar()
    expect(ABAS_MAPA.map((a) => a.rotulo)).toEqual(['Área de influência total', 'Só diretamente conectados', 'Áreas geométricas (Voronoi)'])
    const lista = screen.getByRole('tablist')
    const abas = within(lista).getAllByRole('tab')
    expect(abas.map((a) => a.textContent)).toEqual(['Área de influência total', 'Só diretamente conectados', 'Áreas geométricas (Voronoi)'])
    expect(abas.map((a) => a.getAttribute('aria-selected'))).toEqual(['true', 'false', 'false'])
    expect(abas.map((a) => a.tabIndex)).toEqual([0, -1, -1])
    const painel = await screen.findByRole('tabpanel')
    expect(painel.getAttribute('aria-labelledby')).toBe(abas[0].id)
    expect(abas[0].getAttribute('aria-controls')).toBe(painel.id)
    await waitFor(() => expect(visoesPedidas).toEqual(['todos']))                 // só a visão aberta é buscada; o Voronoi nem monta
    expect(montagensVoronoi).not.toHaveBeenCalled()
  })

  it('a primeira aba pinta pelo PTT principal, com a legenda dos PTTs e a tabela de números', async () => {
    montar()
    await screen.findByTestId('coropletico')
    const p = propsMapa.mock.calls[propsMapa.mock.calls.length - 1][0]
    expect(p.pontos).toHaveLength(3)                                              // um ponto por PTT
    expect(JSON.stringify(p.cor)).toContain('9900001')
    const legenda = screen.getByTestId('legenda-ptts')
    expect(within(legenda).getAllByRole('listitem').map((l) => l.textContent)).toEqual(expect.arrayContaining(['Arandurápolis/SP', 'Tupãnópolis/RJ', 'Guaraniópolis/PR']))
    expect(screen.getByTestId('legenda-area-nacional').textContent).toContain('Além do P80')
    const tabela = screen.getByTestId('tabela-ptts-area')
    expect(within(tabela).getAllByRole('row')).toHaveLength(4)
    expect(tabela.textContent).toContain('200 km')
    expect(screen.getByText(/Isto não é cobertura de rede/)).toBeTruthy()
    expect(screen.getByText(/1 PTT tem PIX sem coordenada/)).toBeTruthy()
  })

  it('setas, Home e End movem o foco e abrem a aba; a visão dos conectados é buscada ao abrir', async () => {
    montar()
    await screen.findByTestId('coropletico')
    const [a1, a2, a3] = screen.getAllByRole('tab')
    a1.focus()
    fireEvent.keyDown(a1, { key: 'ArrowRight' })
    expect(a2.getAttribute('aria-selected')).toBe('true')
    expect(document.activeElement).toBe(a2)
    await waitFor(() => expect(visoesPedidas).toEqual(['todos', 'diretos']))
    fireEvent.keyDown(a2, { key: 'End' })
    expect(a3.getAttribute('aria-selected')).toBe('true')
    expect(document.activeElement).toBe(a3)
    fireEvent.keyDown(a3, { key: 'ArrowRight' })                                  // dá a volta
    expect(a1.getAttribute('aria-selected')).toBe('true')
    fireEvent.keyDown(a1, { key: 'ArrowLeft' })
    expect(a3.getAttribute('aria-selected')).toBe('true')
    fireEvent.keyDown(a3, { key: 'Home' })
    expect(a1.getAttribute('aria-selected')).toBe('true')
  })

  it('a aba do Voronoi mostra o mapa de antes com os mesmos dados e só um painel fica na página', async () => {
    montar()
    fireEvent.click(screen.getByRole('tab', { name: 'Áreas geométricas (Voronoi)' }))
    expect((await screen.findByTestId('voronoi')).textContent).toBe('voronoi 2 2026-09-20')
    expect(screen.getAllByRole('tabpanel')).toHaveLength(1)
    expect(screen.queryByTestId('coropletico')).toBeNull()
    expect(screen.getByText(/PTT mais próximo \(distância geográfica\) · grade 0,12°/)).toBeTruthy()
  })

  it('snapshot sem o artefato avisa em vez de desenhar', async () => {
    server.use(http.get('*/api/v1/ixps/area-influencia', () => new HttpResponse(null, { status: 204 })))
    montar()
    expect(await screen.findByTestId('area-nacional-vazia')).toBeTruthy()
    expect(screen.queryByTestId('coropletico')).toBeNull()
  })

  it('o texto visível não usa travessão', async () => {
    montar()
    await screen.findByTestId('coropletico')
    expect(screen.getByTestId('mapa-ptts-abas').textContent).not.toMatch(/[—–]/)
  })
})
