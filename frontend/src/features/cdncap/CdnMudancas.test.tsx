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
import { CdnMudancas } from './CdnMudancas'

vi.mock('../../auth/AuthContext', () => ({ useAuth: () => ({ requireLogin: () => true }) }))

describe('Mudanças da matriz de CDNs', () => {
  it('lista entradas e saídas em ordem neutra, separa catálogo e cobertura e traz a regra', async () => {
    let pedido = ''
    server.use(
      http.get('*/api/v1/brasil/snapshots', () => HttpResponse.json({ count: 2, latest: '2026-11-22', snapshots: ['2026-11-15', '2026-11-22'] })),
      http.get('*/api/v1/cdns/mudancas', ({ request }) => {
        pedido = new URL(request.url).search
        return HttpResponse.json({
          a: '2026-11-15', b: '2026-11-22',
          entradas: [{ cdn: 'Sage Networks', ptt: 'rj' }], saidas: [{ cdn: 'Qwilt', ptt: 'ce' }],
          nao_comparaveis: [{ cdn: 'Nova', ptt: 'sp', motivos: ['base_diferente'], detalhes: [{ codigo: 'base_diferente', texto: 'a base (população ou fonte) do número é outra nos dois pontos' }], estava: false, esta: true }],
          catalogo: { cdns_incluidas: ['Nova'], cdns_retiradas: [], asns_alterados: [{ cdn: 'Sage Networks', asns_incluidos: [64501], asns_retirados: [] }] },
          totais: { cdns_a: 60, cdns_b: 61, entradas: 1, saidas: 1, nao_comparaveis: 1 },
          comparabilidade: { versao: 1, texto: ['Variação só entre pontos comparáveis.'], avisos: [] },
          limites: 'Cadastro de membros do PTT não é sessão nem tráfego.', fonte: 'cadastro de participantes dos PTTs do IX.br', selo: 'fato',
        })
      }),
    )
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><CdnMudancas /></MemoryRouter></QueryClientProvider>)
    await waitFor(() => expect(screen.getByTestId('cdn-mudancas-resumo')).toBeTruthy())
    expect(pedido).toContain('a=2026-11-15')
    expect(pedido).toContain('b=2026-11-22')
    expect(screen.getByTestId('cdn-mudancas-resumo').textContent).toBe('Entre 2026-11-15 e 2026-11-22: 1 entrada e 1 saída na lista de membros; 1 não comparável.')
    expect(screen.getByText('Sage Networks em')).toBeTruthy()
    expect(screen.getByTestId('cdn-nao-comparaveis').textContent).toContain('a base (população ou fonte) do número é outra nos dois pontos')
    expect(screen.getByTestId('cdn-catalogo').textContent).toContain('Nova: incluída na lista curada')
    expect(screen.getByTestId('cdn-catalogo').textContent).toContain('ASNs incluídos AS64501')
    expect(screen.getByText('Variação só entre pontos comparáveis.')).toBeTruthy()
    expect(screen.getByTestId('cdn-mudancas').textContent).toMatch(/Fato · cadastro de participantes dos PTTs do IX\.br · ref\. 2026-11-22/)
  })
})
