// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { fixtures, server } from '../test/server'
import { useAppStore } from '../store/app'
import { blocosDe } from '../features/entidade/registry'
import '../features/prefixo'
import { PrefixoPage } from './PrefixoPage'
import { SearchBar } from '../components/layout/SearchBar'
import { MOAS_INDISPONIVEL } from '../features/prefixo/blocks/MoasBloco'

const info = { prefix: '198.18.0.0/24', ip_version: 4, origin_asn: 64496, uf: 'ES', country: 'BR', geo_confidence: 'city_centroid', geo_source: 'dbip-lite-2026-09',
  snapshot_date: '2026-09-20', geo_org: { name: 'Provedor 01 Telecom Ltda', cnpj: '90000001000100' } }

const analiseComMoas = {
  snapshot_date: '2026-09-20',
  moas: [{ prefix: '198.18.0.0/24', afi: 'v4', origins: [64496, 64497], br_origins: [64496, 64497], is_prefix_br: true, origens: [
    { asn: 64496, name: 'Provedor 01 Telecom Ltda', coletores: 2, coletores_nomes: ['rvT', 'rvU'], asn_br: true },
    { asn: 64497, name: 'Provedor 02 Telecom Ltda', coletores: 1, coletores_nomes: ['rvU'], asn_br: true }] }],
  moas_resumo: { prefixos: { v6: { global: 1, br: 1 }, v4: { global: 2, br: 1 } }, coletores: { v6: ['rvT', 'rvU'], v4: ['rvT', 'rvU'] },
    lista: 'prefixos brasileiros', lista_truncada: false, lista_limite: 2000, definicao: 'Prefixo com mais de um AS de origem.',
    como_ler: 'É fato observado; a causa não é medida. Hipóteses, a conferir caso a caso.', limites: 'Visão de poucos coletores.' },
}

function montar(caminho: string) {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[caminho]}><Routes><Route path="/prefixo/*" element={<PrefixoPage />} /></Routes></MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' })
  server.use(
    http.get('*/api/v1/snapshots/:date', () => HttpResponse.json({ date: '2026-09-20', summary: null, manifest: { sources: [{ id: 'rpki_collector', as_of: '2026-09-20', frescor: 'ok' }] } })),
    http.get('*/api/v1/prefixes/*', ({ request }) => {
      const p = new URL(request.url).pathname.replace('/api/v1/prefixes/', '')
      return p === '198.18.0.0/24' ? HttpResponse.json(info) : new HttpResponse('nada', { status: 404 })
    }),
  )
})

describe('página de prefixo', () => {
  it('blocos na ordem do plano', () => {
    expect(blocosDe('prefixo').map((b) => b.id)).toEqual(['origem', 'rpki', 'ptts', 'registro', 'geo', 'moas', 'ciclo-de-vida'])
  })

  it('mostra origem, validação RPKI com o ROA que cobre, PTTs, Registro.br e geolocalização', async () => {
    montar('/prefixo/198.18.0.0/24')
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent('198.18.0.0/24')
    expect(await screen.findByText('válido')).toBeInTheDocument()                       // rpki_validation do fixture do ASN 64496
    expect(await screen.findByText('lacnic')).toBeInTheDocument()                        // o ROA que cobre o prefixo, com o TA
    expect(screen.queryByText(/Nenhum ROA cobre/)).toBeNull()
    expect(await screen.findByRole('link', { name: 'ZA' })).toHaveAttribute('href', '/ixp/za')        // PTT onde aparece
    expect(screen.getByText(/Alocado ao AS pelo Registro.br/)).toBeInTheDocument()
    expect(screen.getByText('centro do município')).toBeInTheDocument()
    expect(screen.getAllByTestId('proveniencia').length).toBeGreaterThanOrEqual(5)
  })

  it('prefixo malformado explica sem chamar a API; prefixo ausente diz que não consta', async () => {
    montar('/prefixo/abc')
    expect(await screen.findByText('Prefixo inválido')).toBeInTheDocument()
  })

  it('prefixo bem formado mas fora do Registro.br: "não encontrado"', async () => {
    montar('/prefixo/203.0.113.0/24')
    expect(await screen.findByText('Prefixo não encontrado')).toBeInTheDocument()
  })

  it('MOAS: só baixa a análise (14 MB) quando o usuário pede e lista as origens com os coletores (PFX-E3)', async () => {
    let chamadas = 0
    server.use(http.get('*/api/v1/routing-analysis', () => { chamadas += 1; return HttpResponse.json(analiseComMoas) }))
    montar('/prefixo/198.18.0.0/24')
    const botao = await screen.findByRole('button', { name: /Verificar na análise de roteamento/ })
    expect(chamadas).toBe(0)
    fireEvent.click(botao)
    const bloco = await screen.findByTestId('moas-observado')
    expect(bloco.textContent).toMatch(/2 ASes de origem/)
    expect(bloco.textContent).toMatch(/vista em 2 coletores \(rvT, rvU\)/)
    expect(screen.getByRole('link', { name: 'AS64497' })).toHaveAttribute('href', '/asn/64497?date=2026-09-20')
    expect(bloco.textContent).not.toMatch(/sequestro|hijack/i)
    expect(chamadas).toBe(1)
  })

  it('MOAS medido sem o prefixo: "nenhuma observada", com o número de coletores', async () => {
    server.use(http.get('*/api/v1/routing-analysis', () => HttpResponse.json({ ...analiseComMoas, moas: [] })))
    montar('/prefixo/198.18.0.0/24')
    fireEvent.click(await screen.findByRole('button', { name: /Verificar na análise de roteamento/ }))
    expect((await screen.findByTestId('moas-nenhum')).textContent).toMatch(/Nenhuma origem múltipla \(MOAS\) observada para este prefixo exato neste snapshot, entre 2 coletores/)
  })

  it('MOAS não medido no snapshot: aviso de limite da coleta, sem afirmar ausência', async () => {
    server.use(http.get('*/api/v1/routing-analysis', () => HttpResponse.json({ moas: null, moas_resumo: null, moas_indisponivel: MOAS_INDISPONIVEL })))
    montar('/prefixo/198.18.0.0/24')
    fireEvent.click(await screen.findByRole('button', { name: /Verificar na análise de roteamento/ }))
    const aviso = await screen.findByTestId('moas-indisponivel')
    expect(aviso.textContent).toMatch(/não medida neste snapshot/)
    expect(aviso.textContent).toMatch(/limite da coleta, não ausência de eventos/)
    expect(document.body.textContent).not.toMatch(/Nenhuma origem múltipla/)
  })

  it('MOAS com falha da API: EstadoDados, nunca "nenhuma"', async () => {
    server.use(http.get('*/api/v1/routing-analysis', () => new HttpResponse('erro', { status: 500 })))
    montar('/prefixo/198.18.0.0/24')
    fireEvent.click(await screen.findByRole('button', { name: /Verificar na análise de roteamento/ }))
    const falha = await screen.findByText(/Não foi possível carregar a análise de roteamento/)
    expect(falha.closest('[data-estado]')).toHaveAttribute('data-estado', 'falha')
    expect(document.body.textContent).not.toMatch(/Nenhuma origem múltipla/)
  })
})

describe('busca global aceita prefixo', () => {
  it('Enter com um CIDR leva à página do prefixo', async () => {
    let destino = ''
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={['/']}>
          <SearchBar />
          <Routes><Route path="/prefixo/*" element={<div data-testid="alvo">{(destino = 'ok')}</div>} /><Route path="*" element={null} /></Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    const campo = screen.getByPlaceholderText(/prefixo/)
    fireEvent.change(campo, { target: { value: '177.75.0.0/16' } })
    fireEvent.keyDown(campo, { key: 'Enter' })
    expect(await screen.findByTestId('alvo')).toBeInTheDocument()
    expect(destino).toBe('ok')
  })
})
