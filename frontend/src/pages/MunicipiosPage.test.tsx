// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Lista de municípios: as três lentes que eram abas de Rankings, com o critério à vista e a estimativa rotulada como estimativa. */
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { server } from '../test/server'
import { useAppStore } from '../store/app'
import { MunicipiosPage } from './MunicipiosPage'

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ anon: { id: 'x' }, loading: false }) }))

const montar = (url = '/municipios') => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[url]}><MunicipiosPage /></MemoryRouter></QueryClientProvider>)
beforeEach(() => useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' }))

describe('/municipios', () => {
  it('lente de mercado: lista com HHI e líder, ligada à página do município', async () => {
    server.use(http.get('*/api/v1/ranking/municipios', () => HttpResponse.json({ snapshot_date: '2026-09-20', mes_referencia: '2026-08', criterio: 'Acessos declarados (decrescente)', total: 1,
      items: [{ posicao: 1, ibge: '3550308', nome: 'São Paulo', uf: 'SP', acessos: 4872850, hhi: 1200, n_operadoras: 300, var_aa_pct: 3.2, lider: { cnpj: '1', empresa: 'Provedor A', share: 31.5 } }] })))
    montar()
    await waitFor(() => expect(screen.getByText('São Paulo').getAttribute('href')).toBe('/municipio/3550308'))
    expect(screen.getByText(/Provedor A \(31,5%\)/)).toBeInTheDocument()
    expect(screen.getByText(/SICI 2026-08/)).toBeInTheDocument()
  })

  it('lente de penetração: estimativa rotulada, distância ao PTT e filtro de porte na chamada', async () => {
    let pedido = ''
    server.use(http.get('*/api/v1/territorio/ranking', ({ request }) => {
      pedido = new URL(request.url).search
      return HttpResponse.json({ snapshot_date: '2026-09-20', criterio: 'Acessos fixos declarados por domicílio (decrescente)', limites: "Estimativa. 'Utilização de internet' (PNAD) inclui quem usa só o celular.", total: 1,
        items: [{ posicao: 1, ibge: '3550308', nome: 'São Paulo', uf: 'SP', populacao: 1, populacao_estimada: 11911337, domicilios: 1, domicilios_projetados: 4600000, acessos: 4872850, penetracao: 1.06, nao_visto: 240039, ptt_proximo: 'sp', km_ptt: 0 }] })
    }))
    montar('/municipios?lente=penetracao')
    await waitFor(() => expect(screen.getByText('São Paulo').getAttribute('href')).toBe('/municipio/3550308'))
    expect(screen.getByText('Não visto (estim.)')).toBeTruthy()
    expect(screen.getByText('1,06')).toBeTruthy()
    expect(screen.getByText(/inclui quem usa só o celular/)).toBeTruthy()
    expect(pedido).toContain('min_domicilios=1000')
  })

  it('trocar de lente mantém a UF e muda o que é pedido', async () => {
    let pedido = ''
    server.use(
      http.get('*/api/v1/ranking/municipios', () => HttpResponse.json({ snapshot_date: 'd', mes_referencia: 'm', criterio: 'c', total: 0, items: [] })),
      http.get('*/api/v1/territorio/ranking', ({ request }) => { pedido = new URL(request.url).search; return HttpResponse.json({ snapshot_date: 'd', criterio: 'c', limites: 'l', total: 0, items: [] }) }),
    )
    montar('/municipios?uf=SP')
    fireEvent.click(screen.getByRole('tab', { name: 'Sem PTT a 100 km' }))
    await waitFor(() => expect(pedido).toContain('sem_ptt_proximo=true'))
    expect(pedido).toContain('uf=SP')
  })
})
