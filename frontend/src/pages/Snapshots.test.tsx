// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../test/server'
import { Snapshots } from './Snapshots'

const montar = () => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><Snapshots /></MemoryRouter></QueryClientProvider>,
)

describe('/snapshots', () => {
  it('rótulos de contagem dizem o que o campo mede', async () => {
    server.use(
      http.get('*/api/v1/brasil/snapshots', () => HttpResponse.json({ count: 1, latest: '2026-11-22', snapshots: ['2026-11-22'] })),
      http.get('*/api/v1/brasil/snapshots/:date', () => HttpResponse.json({ date: '2026-11-22', summary: { total_asns_br: 9129, ixp_aggregate: { br_asns_origin_union_count: 8550 } }, manifest: null })),
      http.get('*/api/v1/rpki/summary', () => HttpResponse.json({})),
      http.get('*/api/v1/outorgas/stats', () => HttpResponse.json({ total: 1 })),
    )
    montar()
    fireEvent.click(await screen.findByText('2026-11-22'))
    expect(await screen.findByText('ASNs brasileiros no índice do snapshot')).toBeTruthy()
    expect(screen.getByText('ASNs BR com rotas vistas no IX.br (originadores)')).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/alocados pelo Registro\.br|ASN BR no IX\.br/)
  })

  const resumo = { total_asns_br: 9129, global_table: { br_asns_in_ft: 8500 }, br_asns_ft_v6: 7573, br_asns_ft_v4: 8400, ixp_aggregate: { br_asns_origin_union_count: 8550 }, br_apnic_users_total: 150000000 }
  const rotas = () => [
    http.get('*/api/v1/brasil/snapshots', () => HttpResponse.json({ count: 1, latest: '2026-11-22', snapshots: ['2026-11-22'] })),
    http.get('*/api/v1/rpki/summary', () => HttpResponse.json({ br_asns_with_roa: 6000 })),
    http.get('*/api/v1/outorgas/stats', () => HttpResponse.json({ total: 1 })),
  ]

  it('SNAP 5.1: cada indicador mostra a data da sua fonte e o selo, e o estado da coleta; IPv6 antes de IPv4', async () => {
    const manifest = {
      generated_at: '2026-11-23T04:00:00Z', pipeline_version: '2.0.33', coleta: 'completa', coleta_ok: true, ixps_configured: ['sp', 'rj'], ixps_collected: ['sp', 'rj'],
      checks: { ptt_coletados: { status: 'ok', configurados: 2, coletados: 2 }, asns_br: { status: 'ok', valor: 9129, anterior: 9124, variacao_pct: 0.05, limite_pct: 1 } },
      sources: [
        { id: 'lg_ixbr', as_of: '2026-11-17', frescor: 'ok' }, { id: 'rpki_collector', as_of: '2026-11-13', frescor: 'atrasado', limite_dias: 2 },
        { id: 'fulltable_routeviews', as_of: '2026-11-22', frescor: 'ok' }, { id: 'registro_br', as_of: '2026-11-22', frescor: 'ok' }, { id: 'apnic_pop', as_of: '2026-11-15', frescor: 'ok' },
      ],
    }
    server.use(...rotas(), http.get('*/api/v1/brasil/snapshots/:date', () => HttpResponse.json({ date: '2026-11-22', summary: resumo, manifest })))
    montar()
    fireEvent.click(await screen.findByText('2026-11-22'))
    await screen.findByTestId('indicadores-snapshot')
    const cartao = (rotulo: string) => screen.getByText(rotulo).closest('div')!
    expect(cartao('ASNs BR com rotas vistas no IX.br (originadores)').textContent).toContain('lg_ixbr · ref. 17/11/2026')
    expect(cartao('ASN com objetos RPKI').textContent).toContain('ref. 13/11/2026 (atrasada (limite 2 dias))')
    expect(cartao('Usuários BR estimados (APNIC)').textContent).toContain('Estimado')
    const rotulos = screen.getAllByRole('term').map((t) => t.textContent)
    expect(rotulos.indexOf('ASN BR com prefixos IPv6 na full table')).toBeLessThan(rotulos.indexOf('ASN BR com prefixos IPv4 na full table'))
    expect(cartao('ASN BR com prefixos IPv6 na full table').textContent).toContain('7.573')
    const coleta = screen.getByTestId('coleta-snapshot').textContent!
    expect(coleta).toContain('Coleta: completa (2 de 2 PTTs)')
    expect(coleta).toContain('Versão do processamento: 2.0.33')
    expect(coleta).toContain('9.129')
    expect(coleta).toContain('contra 9.124 no snapshot comparado')
  })

  it('TRANSV-E9: snapshot sem manifest.sources diz que a data da fonte não foi registrada, sem data inventada', async () => {
    server.use(...rotas(), http.get('*/api/v1/brasil/snapshots/:date', () => HttpResponse.json({ date: '2026-11-22', summary: resumo, manifest: { sources: null, pipeline_version: '1.1.5.7', generated_at: '2026-11-16T04:00:00Z' } })))
    montar()
    fireEvent.click(await screen.findByText('2026-11-22'))
    await screen.findByTestId('indicadores-snapshot')
    const refs = screen.getAllByTestId('referencia-indicador').map((r) => r.textContent)
    expect(refs.length).toBeGreaterThan(5)
    for (const r of refs) { expect(r).toContain('data da fonte não registrada neste snapshot'); expect(r).not.toMatch(/ref\. \d/) }
    expect(screen.getByTestId('coleta-snapshot').textContent).toContain('não traz as verificações')
  })

  it('sem snapshot, nenhuma instrução de operador', async () => {
    server.use(http.get('*/api/v1/brasil/snapshots', () => HttpResponse.json({ count: 0, latest: null, snapshots: [] })))
    montar()
    expect(await screen.findByText('Nenhum snapshot publicado até agora.')).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/pipeline|summary\.json/i)
  })
})
