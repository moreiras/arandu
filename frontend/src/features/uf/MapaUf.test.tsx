// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { useAppStore } from '../../store/app'
import { MapaUf } from './MapaUf'

vi.mock('../../components/maps/Coropletico', () => ({ Coropletico: ({ descricao }: { descricao: string }) => <div data-testid="coropletico" aria-label={descricao} /> }))
vi.mock('../../hooks/entidades', () => ({ useCentroides: () => ({ data: { '3550308': [-46.6, -23.5], '3304557': [-43.2, -22.9] } }) }))

const dados: any = { uf: 'SP', municipios: [{ ibge: '3550308', nome: 'São Paulo', acessos: 10, operadores: 3, hhi: 2000, kmPtt: 5, fibraPct: 60 }, { ibge: '3304557', nome: 'Rio', acessos: 5, operadores: 2, hhi: 1500, kmPtt: 9, fibraPct: 40 }] }

beforeEach(() => { useAppStore.setState({ activeDate: null, latestSnapshot: '2026-11-05' }) })

function montar() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><MapaUf dados={dados} /></MemoryRouter></QueryClientProvider>)
}

describe('MapaUf: indicadores de Rede', () => {
  it('os indicadores de Rede só buscam o mapa nacional quando escolhidos e mostram a natureza do dado', async () => {
    let chamadas = 0
    server.use(http.get('*/api/v1/territorio/mapa', ({ request }) => { chamadas += 1; expect(new URL(request.url).searchParams.get('indicador')).toBe('ipv6_estimado_pct'); return HttpResponse.json({ valores: { '3550308': 64 }, indicador: 'ipv6_estimado_pct' }) }))
    montar()
    expect(chamadas).toBe(0)                                                              // o padrão é fibra: nada de rede é buscado
    fireEvent.click(screen.getByRole('button', { name: /Acessos em IPv6/ }))
    await waitFor(() => expect(chamadas).toBe(1))
    expect(await screen.findByText(/Natureza:/)).toBeTruthy()
    expect(screen.getByText(/não é medida direta/)).toBeTruthy()
  })

  it('UF sem nenhum município com o indicador diz que faltam dados e que isso não é zero', async () => {
    server.use(http.get('*/api/v1/territorio/mapa', () => HttpResponse.json({ valores: { '9999999': 10 }, indicador: 'transito_unico_pct' })))
    montar()
    fireEvent.click(screen.getByRole('button', { name: /único provedor/ }))
    expect(await screen.findByText(/Não quer dizer que o valor seja zero/)).toBeTruthy()
  })
})
