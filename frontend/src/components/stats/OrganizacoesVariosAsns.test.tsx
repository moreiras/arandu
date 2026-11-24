// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { server } from '../../test/server'
import { OrganizacoesVariosAsns } from './OrganizacoesVariosAsns'

vi.mock('../../auth/AuthContext', async (original) => ({
  ...(await original<typeof import('../../auth/AuthContext')>()),
  useOrcamentoAvancado: () => ({ pronto: true, esgotado: false }),
}))

const asn = (n: number) => ({ asn: n, name: `Rede ${n}`, apnic_users: 10, pct_v6: 50, rir_prefixes_v6_count: 1, rir_prefixes_v4_count: 1, has_rpki: true, has_aspa: null, ixps_direct_count: 0 })

beforeEach(() => {
  server.use(http.get('*/api/v1/asns/by-organization', () => HttpResponse.json({ snapshot_date: '2026-09-20', total: 1, groups: [
    { cnpj: '90000001000129', razao_social: 'Provedor Exemplo Ltda', nome_fantasia: '', uf: 'SP', asn_count: 2, total_apnic_users: 20, total_v4_blocks: 2, total_v6_blocks: 2, asns: [asn(64500), asn(64501)] },
  ] })))
})

describe('/ases, organizações com vários ASNs: linha expansível por teclado (ASES-E8)', () => {
  it('o botão expande a linha com aria-expanded e aria-controls só quando o detalhe existe', async () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter><OrganizacoesVariosAsns /></MemoryRouter>
      </QueryClientProvider>,
    )
    const tabela = await screen.findByRole('table', { name: 'Organizações com vários ASNs' })
    for (const th of within(tabela).getAllByRole('columnheader')) expect(th).toHaveAttribute('scope', 'col')
    const botao = within(tabela).getByRole('button', { name: 'ASNs de Provedor Exemplo Ltda' })
    expect(botao).toHaveAttribute('type', 'button')
    expect(botao).toHaveAttribute('aria-expanded', 'false')
    expect(botao).not.toHaveAttribute('aria-controls')
    expect(screen.queryByRole('link', { name: 'AS64500' })).toBeNull()
    fireEvent.click(botao)
    expect(botao).toHaveAttribute('aria-expanded', 'true')
    const detalhe = document.getElementById(botao.getAttribute('aria-controls')!)
    expect(detalhe).not.toBeNull()
    expect(within(detalhe!).getByRole('link', { name: 'AS64500' })).toHaveAttribute('href', '/asn/64500')
    fireEvent.click(botao)
    expect(botao).toHaveAttribute('aria-expanded', 'false')
  })
})
