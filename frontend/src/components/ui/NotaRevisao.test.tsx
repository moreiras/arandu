// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { SITE } from '../../lib/site'
import { MudancasPage } from '../../pages/MudancasPage'
import { Snapshots } from '../../pages/Snapshots'
import { NotaRevisao } from './NotaRevisao'

vi.mock('../../auth/AuthContext', () => ({ useAuth: () => ({ anon: null, loading: false }) }))

const montar = (el: JSX.Element) => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>{el}</MemoryRouter></QueryClientProvider>,
)
const NOME = 'Nota de revisão de 25/11/2026: eventos de ROA, ASPA e RPKI'

describe('NotaRevisao', () => {
  it('tem papel note e nome acessível com a data da revisão', () => {
    montar(<NotaRevisao />)
    expect(screen.getByRole('note', { name: NOME })).toBeTruthy()
  })

  it('é recolhível: fechada por padrão, aberta com `aberta`, e o resumo carrega o rótulo em texto', () => {
    const { container, unmount } = montar(<NotaRevisao />)
    const d = container.querySelector('details')!
    expect(d.open).toBe(false)
    expect(d.querySelector('summary')!.textContent).toBe(NOME)
    fireEvent.click(d.querySelector('summary')!)
    unmount()
    const aberta = montar(<NotaRevisao aberta />)
    expect(aberta.container.querySelector('details')!.open).toBe(true)
  })

  it('mostra data, contagens antes e depois, causa, regra e link do CHANGELOG no endereço do código-fonte', () => {
    montar(<NotaRevisao aberta />)
    const nota = screen.getByRole('note')
    const texto = nota.textContent ?? ''
    expect(texto).toContain('eventos_regra = 2')
    expect(texto).toContain('campo ausente era contado como zero')
    expect(texto).toContain('roa_list de ASNs estrangeiros foi publicado só a partir de 2026-06-28')
    const t = within(screen.getByRole('table', { name: /05\/07\/2026/ }))
    const linha = (tipo: string) => t.getByRole('rowheader', { name: tipo }).closest('tr')!.textContent
    expect(linha('roa_perdido')).toBe('roa_perdido50.12763')
    expect(linha('aspa_perdido')).toBe('aspa_perdido1.8272')
    expect(linha('rpki_invalido_resolvido')).toBe('rpki_invalido_resolvido1.81514')
    const total = within(screen.getByRole('table', { name: /20 datas/ }))
    expect(total.getByRole('rowheader', { name: 'roa_perdido' }).closest('tr')!.textContent).toBe('roa_perdido50.919834')
    const link = within(nota).getByRole('link', { name: /CHANGELOG/ })
    expect(link.getAttribute('href')).toBe(`${SITE.codigoFonte}/blob/main/CHANGELOG.md`)
    expect(link.getAttribute('rel')).toContain('noopener')
  })

  it('as tabelas têm legenda e cabeçalhos de coluna', () => {
    montar(<NotaRevisao aberta />)
    for (const tabela of screen.getAllByRole('table')) {
      expect(tabela.querySelector('caption')?.textContent).toBeTruthy()
      expect(within(tabela).getAllByRole('columnheader').map((c) => c.textContent)).toEqual(['Tipo de evento', 'Antes', 'Depois'])
    }
  })
})

describe('NotaRevisao nas páginas', () => {
  const resposta = (extra: object = {}) => ({ total: 0, limit: 100, offset: 0, items: [], ...extra })

  it('/mudancas mostra a nota aberta com o filtro padrão e quando o tipo é de ROA, ASPA ou RPKI', async () => {
    server.use(
      http.get('*/api/v1/changes/summary', () => HttpResponse.json({ total: 0, por_tipo: {}, por_data: {}, snapshots_com_historico: 3 })),
      http.get('*/api/v1/changes', () => HttpResponse.json(resposta())),
    )
    montar(<MudancasPage />)
    const nota = await screen.findByRole('note', { name: NOME })
    expect(nota.querySelector('details')!.open).toBe(true)
    fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'roa_perdido' } })
    expect(screen.getByRole('note', { name: NOME })).toBeTruthy()
  })

  it('/mudancas não mostra a nota quando o tipo filtrado não é afetado pela revisão', async () => {
    server.use(
      http.get('*/api/v1/changes/summary', () => HttpResponse.json({ total: 0, por_tipo: {}, por_data: {}, snapshots_com_historico: 3 })),
      http.get('*/api/v1/changes', () => HttpResponse.json(resposta())),
    )
    montar(<MudancasPage />)
    await screen.findByRole('note', { name: NOME })
    fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'asn_novo' } })
    await waitFor(() => expect(screen.queryByRole('note')).toBeNull())
  })

  it('/snapshots mostra a nota como aviso compacto (fechada)', async () => {
    server.use(
      http.get('*/api/v1/brasil/snapshots', () => HttpResponse.json({ count: 2, latest: '2026-11-22', snapshots: ['2026-11-15', '2026-11-22'] })),
    )
    montar(<Snapshots />)
    const nota = await screen.findByRole('note', { name: NOME })
    expect(nota.querySelector('details')!.open).toBe(false)
  })
})
