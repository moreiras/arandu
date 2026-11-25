// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { CorpoInfraFisica, InfraFisicaRaio } from './InfraFisicaRaio'
import type { InfraProximos } from '../../types/api'

const DADOS: InfraProximos = {
  snapshot_date: '2026-11-22', ponto: { lat: -7.2258, lon: -39.3252 }, raio_km: 80, indisponiveis: [],
  camadas: {
    enlaces: { camada: 'Enlaces', fonte: 'UIT', total: 27, por_status: { 'Fibre Operational': 26, 'Fibre Planned': 1 }, itens: [{ distancia_km: 0.3, name: 'Juazeiro', status: 'Fibre Operational' }] },
    linhas_transmissao: { camada: 'Linhas', fonte: 'ONS/Aneel', total: 15, itens: [{ distancia_km: 17.3, name: 'LT 500 kV' }] },
    cabos: { camada: 'Cabos', fonte: 'TeleGeography', total: 0, itens: [] },
    pontos_aterrissagem: { camada: 'Pontos', fonte: 'TeleGeography', total: 0, itens: [] },
  },
  instalacoes: { raio_km: 150, total: 0, fonte: 'PeeringDB', itens: [] },
}

describe('infraestrutura física no raio (PT-25 / localizador 5.5)', () => {
  it('corpo: contagem e status por tipo, distância das mais próximas, selo e a frase de ausência de instalações', () => {
    render(<MemoryRouter><CorpoInfraFisica dados={DADOS} raioKm={80} /></MemoryRouter>)
    const t = screen.getByTestId('infra-corpo').textContent ?? ''
    expect(t).toMatch(/Enlaces terrestres de transmissão \(UIT\)27/)
    expect(t).toMatch(/26 Fibre Operational, 1 Fibre Planned/)
    expect(t).toMatch(/Juazeiro: 0,3 km; Fibre Operational/)
    expect(t).toMatch(/LT 500 kV: 17 km/)
    expect(t).toMatch(/nenhuma a até 80 km/)                                           // zero dito, não vazio
    expect(screen.getByTestId('infra-instalacoes').textContent).toMatch(/Nenhuma instalação cadastrada no PeeringDB a até 150 km\./)
    expect(t).toMatch(/inferido/)
    expect(t).toMatch(/Planejado não é existente/)
    expect(t).toMatch(/não quer dizer que as redes locais o usam/)
    expect(screen.getAllByRole('columnheader').every((th) => th.getAttribute('scope') === 'col')).toBe(true)
  })

  it('só pede à rota quando o bloco é aberto, e com ponto e raio na consulta', async () => {
    const pedidos: string[] = []
    server.use(http.get('*/api/v1/territorio/infra-proximos', ({ request }) => { pedidos.push(new URL(request.url).search); return HttpResponse.json(DADOS) }))
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><InfraFisicaRaio lat={-7.22584} lon={-39.32516} raioKm={80} date="2026-11-22" /></MemoryRouter></QueryClientProvider>)
    expect(pedidos).toHaveLength(0)
    const det = screen.getByTestId('infra-fisica') as HTMLDetailsElement
    det.open = true
    fireEvent(det, new Event('toggle'))
    await waitFor(() => expect(screen.getByTestId('infra-corpo')).toBeTruthy())
    expect(pedidos).toHaveLength(1)
    expect(pedidos[0]).toContain('lat=-7.2258')
    expect(pedidos[0]).toContain('raio_km=80')
    expect(pedidos[0]).toContain('date=2026-11-22')
  })
})
