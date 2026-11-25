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
import { server } from '../test/server'
import { ASes } from './ASes'

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ user: { id: 'x' }, anon: null, loading: false, requireLogin: () => {} }), useOrcamentoAvancado: () => ({ pronto: true, esgotado: false }) }))
vi.mock('../components/stats/OrganizacoesVariosAsns', () => ({ OrganizacoesVariosAsns: () => null }))      // outro bloco da página, com sua própria consulta
vi.mock('../hooks/useSnapshot', () => ({ useActiveDate: () => '2026-11-22' }))

const base = { name: 'REDE', cnpj: null, apnic_v6_users: 0, ixps_direct_count: 0, ixps_origin_v6_count: 0, ixps_origin_v4_count: 0, has_rpki: true, has_aspa: false, pdb_registered: false, external_ixps_count: 2 }
const itens = [
  { ...base, asn: 275784, apnic_users: 364, pct_v6: 98.9, epppd: 25, prontidao_indice: 40.3, prontidao_classe: 'atrasado', prontidao_pilares_medidos: 2 },
  { ...base, asn: 53214, apnic_users: 9451, pct_v6: 97.8, epppd: 0.4, prontidao_indice: 91.2, prontidao_classe: 'pronto', prontidao_pilares_medidos: 4 },
  { ...base, asn: 64500, apnic_users: 12000, pct_v6: 3.1, epppd: 8, prontidao_indice: 52.4, prontidao_classe: 'em_progresso', prontidao_pilares_medidos: 3 },
]

function montar() {
  server.use(http.get('*/api/v1/asns', () => HttpResponse.json({ items: itens, total: 3, pages: 1, page: 1 })))
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><ASes /></MemoryRouter></QueryClientProvider>)
}

describe('/ases: política editorial (D6, ASES-E9, ASES-E10)', () => {
  it('amostra pequena (abaixo de 1.000 usuários estimados) leva o selo, com a contagem visível, e ninguém sai da lista', async () => {
    montar()
    await waitFor(() => expect(screen.getByText('AS275784')).toBeTruthy())
    const selos = screen.getAllByTestId('amostra-pequena')
    expect(selos).toHaveLength(1)                                   // só o AS com 364 usuários; 9.451 e 12.000 não
    expect(selos[0].closest('tr')?.textContent).toContain('364')
    expect(selos[0].getAttribute('title')).toContain('364 usuários APNIC estimados')
    expect(screen.getByText('AS53214')).toBeTruthy()
    expect(screen.getByText('AS64500')).toBeTruthy()
  })

  it('nenhuma célula usa cor de avaliação (verde, amarelo, vermelho) e a classe de prontidão aparece em texto', async () => {
    const { container } = montar()
    await waitFor(() => expect(screen.getByText('AS275784')).toBeTruthy())
    expect(container.innerHTML).not.toMatch(/(?:text|bg|border)-(?:ok|perigo|alerta|aviso)-\d{2,3}/)
    const linha = screen.getByText('AS275784').closest('tr')!.textContent ?? ''
    expect(linha).toContain('40,3')
    expect(linha).toContain('atrasado')
    expect(linha).toContain('2/4')
    expect(screen.getByText('AS64500').closest('tr')!.textContent).toContain('em progresso')
  })

  it('o tooltip de %IPv6 não descreve faixas de cor', async () => {
    montar()
    await waitFor(() => expect(screen.getByText('AS275784')).toBeTruthy())
    expect(document.body.innerHTML).not.toMatch(/Verde ≥|Vermelho 20/)
  })
})
