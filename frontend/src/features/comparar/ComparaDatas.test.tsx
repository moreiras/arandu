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
import { server } from '../../test/server'
import { ComparaDatas } from './ComparaDatas'

vi.mock('../../auth/AuthContext', () => ({ useAuth: () => ({ requireLogin: () => true }) }))

describe('Comparar datas', () => {
  it('mostra os totais das duas últimas datas, a variação e as mudanças sem os eventos de provedor', async () => {
    let pedido = ''
    server.use(http.get('*/api/v1/snapshots/diff', ({ request }) => {
      pedido = new URL(request.url).search
      return HttpResponse.json({
        a: '2026-09-13', b: '2026-09-20',
        totais: { n_asns: { a: 100, b: 104, variacao: 4 }, users: { a: 1000, b: 900, variacao: -100 } },
        eventos: { entre: ['2026-09-13', '2026-09-20'], total: 3, por_tipo: { asn_novo: { confirmado: 2, pendente: 1, revertido: 0 }, provedor_novo: { confirmado: 9, pendente: 0, revertido: 0 } } },
        nota: 'Totais por UF somam ASNs com sede na UF; usuários são estimativas da APNIC.',
      })
    }))
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><ComparaDatas /></MemoryRouter></QueryClientProvider>)
    await waitFor(() => expect(screen.getByText('ASNs brasileiros (por UF da sede)')).toBeTruthy())
    expect(pedido).toContain('a=')
    expect(pedido).toContain('b=')
    expect(screen.getByText('+4')).toBeTruthy()
    expect(screen.getByText('-100')).toBeTruthy()
    expect(screen.getByText(/asn novo: 2 confirmadas, 1 em confirmação/)).toBeTruthy()
    expect(screen.queryByText(/provedor novo/)).toBeNull()
  })
  it('não mostra variação quando os pontos não são comparáveis e traz a razão de IPv6 na mesma base e a regra', async () => {
    server.use(http.get('*/api/v1/snapshots/diff', () => HttpResponse.json({
      a: '2026-11-15', b: '2026-11-22',
      totais: {
        users: { a: 1000, b: 1010, variacao: 10, comparavel: true },
        ptts_membros: { a: 100, b: 98, variacao: null, comparavel: false, motivos: [{ codigo: 'cobertura_mudou', texto: 'a cobertura da coleta ou da medição mudou muito entre os pontos', detalhe: 'ptts_coletados: 30 para 20' }] },
      },
      razoes: { ipv6_pct_usuarios: { a: 60.21, b: 60.48, variacao_pp: 0.27, comparavel: true, base: 'linhas de histórico por UF' } },
      eventos: { entre: ['2026-11-15', '2026-11-22'], total: 0, por_tipo: {} },
      comparabilidade: { versao: 1, texto: ['Variação só entre pontos comparáveis.'], avisos: [] },
      nota: 'n',
    })))
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><ComparaDatas /></MemoryRouter></QueryClientProvider>)
    await waitFor(() => expect(screen.getByText('Membros cadastrados nos PTTs')).toBeTruthy())
    expect(screen.getByText('+10')).toBeTruthy()
    expect(screen.getByText(/não comparável/)).toBeTruthy()
    expect(screen.getByText(/ptts_coletados: 30 para 20/)).toBeTruthy()
    expect(screen.getByTestId('razao-ipv6').textContent).toContain('+0,27 p.p.')
    expect(screen.getByText('Variação só entre pontos comparáveis.')).toBeTruthy()
  })
})
