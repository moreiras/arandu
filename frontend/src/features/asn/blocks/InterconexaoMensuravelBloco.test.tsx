// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../../test/server'
import { InterconexaoMensuravelBloco } from './InterconexaoMensuravelBloco'

const resp = (carregadores: object[]) => ({
  snapshot_date: '2026-11-22', asn: 13357, limites: 'Peering bilateral não aparece.', uf_sede: 'PR', usuarios_estimados: 1, carregadores_disponiveis: true,
  origem_sem_direto: [{ ixp: 'cac', nome: 'Cascavel', uf: 'PR', familias: ['v4'], mesma_uf: true, carregadores }],
  sessoes: [], rejeicoes: [], resumo: { origem_sem_direto: 1, sem_sessao: 0, sessao_parcial: 0, ptts_com_rejeicao: 0 },
})
const montar = () => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>
  <InterconexaoMensuravelBloco {...({ dados: { doc: { asn: 13357 }, date: null } } as any)} /></MemoryRouter></QueryClientProvider>)

describe('interconexão mensurável (ASN-E1)', () => {
  it('mostra quem entrega, por onde e o vínculo', async () => {
    server.use(http.get('*/api/v1/asns/13357/interconexao', () => HttpResponse.json(resp([
      { asn: 28158, caminhos: 1, via: [], vinculo: 'mesmo_cnpj' }, { asn: 16735, caminhos: 2, via: [53062], vinculo: null }]))))
    montar()
    expect(await screen.findByText(/entregue por AS28158, mesmo CNPJ \(1\); AS16735 via AS53062 \(2\)/)).toBeTruthy()
    expect(screen.getByText(/aparece por último no caminho observado/)).toBeTruthy()
  })

  it('lista vazia com caminhos disponíveis diz isso, em vez de silêncio', async () => {
    server.use(http.get('*/api/v1/asns/13357/interconexao', () => HttpResponse.json(resp([]))))
    montar()
    expect(await screen.findByText('caminho observado sem AS identificável')).toBeTruthy()
  })
})
