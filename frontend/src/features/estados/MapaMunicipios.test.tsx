// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { server } from '../../test/server'
import { useAppStore } from '../../store/app'
import MapaMunicipios from './MapaMunicipios'

// MapLibre precisa de WebGL: o duplo só registra com que cor, nível e texto o mapa foi chamado.
const chamadas: Array<{ cor: unknown; nivel?: string; rotulo?: (i: string, n: string, u: string) => string; aoClicar?: (c: string, n: 'municipio' | 'uf') => void }> = []
vi.mock('../../components/maps/Coropletico', () => ({
  Coropletico: (p: any) => { chamadas.push(p); return <div data-testid="coropletico" aria-label={p.descricao} /> },
}))

const resposta = (indicador: string, v: Record<string, number>) => HttpResponse.json({
  snapshot_date: '2026-09-20', mes_referencia_sici: '2026-08', censo_ano: '2022', pnad_ano: '2025', indicador, rotulo: indicador, normalizacao: 'x', total: Object.keys(v).length, limites: '', fonte: 'IBGE', valores: v,
})
const montar = () => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><MapaMunicipios /></MemoryRouter>
  </QueryClientProvider>,
)

beforeEach(() => {
  chamadas.length = 0
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(http.get('*/api/v1/territorio/mapa', ({ request }) => {
    const i = new URL(request.url).searchParams.get('indicador')!
    return resposta(i, i === 'km_ptt' ? { '3205309': 5, '1300029': 700, '3550308': 40 } : { '3205309': 90, '1300029': 10, '3550308': 60 })
  }))
})

describe('mapa dos municípios', () => {
  it('colore pela classe do indicador, mostra a legenda com o método, a normalização e a atribuição ao IBGE', async () => {
    montar()
    expect(await screen.findByTestId('legenda')).toHaveTextContent('Acessos por 100 domicílios')
    const ultima = chamadas[chamadas.length - 1]
    expect(JSON.stringify(ultima.cor)).toContain('3205309')
    expect(screen.getByText(/acessos fixos declarados ÷ domicílios projetados × 100/)).toBeInTheDocument()
    expect(screen.getByText(/Fonte: IBGE/)).toBeInTheDocument()
    expect(screen.getByTestId('legenda')).toHaveTextContent('mesmo número de municípios')
  })

  it('tooltip diz o valor com a unidade; sem dado diz "sem dado"; clique abre o município', async () => {
    montar()
    await screen.findByTestId('legenda')
    const p = chamadas[chamadas.length - 1]
    expect(p.rotulo!('3205309', 'Vitória', 'ES')).toBe('Vitória/ES: 90 acessos por 100 domicílios')
    expect(p.rotulo!('9999999', 'Nada', 'XX')).toBe('Nada/XX: sem dado')
  })

  it('"Comparar com" troca para o bivariado, com a legenda 3 × 3 e as duas normalizações', async () => {
    montar()
    await screen.findByTestId('legenda')
    fireEvent.change(screen.getByLabelText('Comparar com'), { target: { value: 'km_ptt' } })
    expect(await screen.findByTestId('legenda-bivariada')).toBeInTheDocument()
    expect(screen.queryByTestId('legenda')).toBeNull()
    expect(screen.getByText(/distância em linha reta do centróide/)).toBeInTheDocument()
    await waitFor(() => expect(JSON.stringify(chamadas[chamadas.length - 1].cor)).toContain('#'))
  })

  it('o seletor só oferece indicadores normalizados', async () => {
    montar()
    const opcoes = (await screen.findByLabelText('Indicador')).querySelectorAll('option')
    expect([...opcoes].map((o) => o.textContent)).not.toContain('Acessos')
    expect(opcoes.length).toBeGreaterThanOrEqual(4)
  })

  it('sem o produto de território no snapshot, avisa em vez de quebrar', async () => {
    server.use(http.get('*/api/v1/territorio/mapa', () => new HttpResponse('não há', { status: 404 })))
    montar()
    expect(await screen.findByText(/Não foi possível carregar este indicador agora/)).toBeInTheDocument()
  })
})
