// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { server } from '../../test/server'
import { useAppStore } from '../../store/app'
import MapaQualidade from './MapaQualidade'
import type { QualIndicador } from '../../types/api'

const chamadas: any[] = []
vi.mock('../../components/maps/Coropletico', () => ({ Coropletico: (p: any) => { chamadas.push(p); return <div data-testid="coropletico" aria-label={p.descricao} /> } }))

const ind: QualIndicador = { servico: 'Banda Larga Fixa', codigo: 'IND4', descricao: 'Cumprimento de velocidade', tipo: 'Indicador IQS', grupo: 'Redes', unidade: '%', referencia_superior: '90%', referencia_inferior: '60%' }
const montar = (i = ind) => render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><MapaQualidade servico="Banda Larga Fixa" indicador={i} /></MemoryRouter></QueryClientProvider>)

beforeEach(() => {
  chamadas.length = 0
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(http.get('*/api/v1/qualidade/mapa', () => HttpResponse.json({
    snapshot_date: '2026-09-20', limites: 'x', servico: 'Banda Larga Fixa', unidade: '%', total: 3, valores: { '1': 95, '2': 70, '3': 40 }, prestadoras: { '1': 1, '2': 2, '3': 1 },
    faixas: { '1': 2, '2': 1, '3': 0 }, faixas_rotulos: { '0': 'abaixo da referência inferior', '1': 'entre as referências', '2': 'acima da referência superior' },
    referencias: { superior: '90%', inferior: '60%' }, normalizacao: 'média das prestadoras medidas',
  })))
})

describe('mapa municipal do RQUAL', () => {
  it('mostra o valor em quantis e alterna para a faixa da Anatel, sem dizer melhor ou pior', async () => {
    montar()
    expect(await screen.findByTestId('legenda')).toHaveTextContent('IND4')
    fireEvent.click(screen.getByText('Faixa da Anatel'))
    const leg = await screen.findByTestId('legenda')
    expect(leg).toHaveTextContent('acima da referência superior')
    expect(leg).toHaveTextContent('o sentido depende do indicador')
    expect(JSON.stringify(chamadas[chamadas.length - 1].cor)).toContain('"1"')
    expect(chamadas[chamadas.length - 1].rotulo('2', 'Beta', 'SP')).toContain('70')
    expect(chamadas[chamadas.length - 1].rotulo('9', 'Zeta', 'SP')).toContain('sem medição')
  })

  it('indicador sem as duas referências não oferece a faixa', async () => {
    server.use(http.get('*/api/v1/qualidade/mapa', () => HttpResponse.json({ snapshot_date: 'x', limites: '', servico: 's', unidade: 'Mbps', total: 1, valores: { '1': 5 }, prestadoras: { '1': 1 }, faixas: null, faixas_rotulos: null, referencias: { superior: null, inferior: null }, normalizacao: 'n' })))
    montar({ ...ind, referencia_superior: null, referencia_inferior: null })
    await screen.findByTestId('legenda')
    expect(screen.queryByText('Faixa da Anatel')).toBeNull()
  })
})
