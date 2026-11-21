// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import type { AsStability, BgpStability } from '../../types/bgpStability'
import { StabilitySection, contarCategorias } from './StabilitySection'

// recharts (ResponsiveContainer) mede o contêiner com ResizeObserver, que o jsdom não tem
beforeAll(() => { vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} }) })

const periodo = { events_per_prefix_per_day: 3, events_per_prefix_per_day_v4: 2, events_per_prefix_per_day_v6: 1, announcements: 10, withdrawals: 5, flapping_prefixes: 1 }
const as = (asn: number, rank: number, severity: string, cat?: string): AsStability => ({
  asn, name: `Operadora ${asn}`, rank, classification: 'chronic_flapper', severity, noise_category: cat, prefix_count_v4: 4, prefix_count_v6: 1,
  period: periodo, daily: [{ total_events: 5 }], top_prefixes: [],
} as unknown as AsStability)
const dist = { buckets: [{ label: '0-1', asn_count: 3 }], p50: 1, p90: 2, p95: 3, p99: 4, max: 5, asn_count_total: 3 }
const base = (ases: AsStability[]): BgpStability => ({
  period: { start: '2026-10-21', end: '2026-10-27', files_processed: 1, collector: 'rv', br_events_v4: 1, br_events_v6: 1 },
  distribution: { v4: dist, v6: dist }, epppd_stats: { median: 1, mean: 2, max: 9 }, hourly_global: { timestamps: [], ann: [], wd: [], attr_upd: [] },
  as_stability: ases, published_at: 'x',
} as unknown as BgpStability)
const montar = (ui: JSX.Element) => render(<MemoryRouter>{ui}</MemoryRouter>)

describe('contarCategorias', () => {
  it('conta por categoria e trata ASes sem categoria como estáveis', () => {
    expect(contarCategorias([as(1, 1, 'high', 'critico'), as(2, 2, 'low'), as(3, 3, 'low', 'estavel')])).toEqual({ estavel: 2, inquieto: 0, barulhento: 0, critico: 1, total: 3 })
  })
})

describe('StabilitySection com a visão geral (1.4.2.5)', () => {
  const top = [as(10, 1, 'critical', 'critico'), as(11, 2, 'high', 'barulhento')]

  it('usa as contagens prontas (não as do top) e oferece "Ver todos" com o total de fora do top', () => {
    const pedir = vi.fn()
    montar(<StabilitySection data={base(top)} categorias={{ estavel: 4329, inquieto: 3753, barulhento: 640, critico: 19, total: 8741 }} totalMedioOuMaior={8027} onPedirTodos={pedir} />)
    expect(screen.getByText('8.741')).toBeInTheDocument()                         // total da tabela de categorias, não 2
    expect(screen.getByRole('link', { name: 'AS10' })).toBeInTheDocument()
    fireEvent.click(screen.getByText(/Ver todos os 8\.027 ASes/))
    expect(pedir).toHaveBeenCalledTimes(1)
  })

  it('enquanto a lista completa não chega mostra só o top e um aviso; ao chegar mostra todos', () => {
    const todos = Array.from({ length: 12 }, (_, i) => as(20 + i, i + 1, 'medium', 'inquieto'))
    const { rerender } = montar(<StabilitySection data={base(todos.slice(0, 2))} totalMedioOuMaior={12} carregandoTodos onPedirTodos={() => {}} />)
    fireEvent.click(screen.getByText(/Ver todos os 12 ASes/))
    expect(screen.getByRole('status')).toHaveTextContent('Carregando a lista completa')
    expect(screen.getByText('Top 10 ASes mais ruidosos')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'AS31' })).toBeNull()
    rerender(<MemoryRouter><StabilitySection data={base(todos)} totalMedioOuMaior={12} onPedirTodos={() => {}} /></MemoryRouter>)
    expect(screen.getByText('12 ASes com severidade média ou maior')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'AS31' })).toBeInTheDocument()
  })

  it('ordenar a tabela recolhida usa a ordem da lista inteira (API), não as 10 linhas do top', () => {
    const v4 = (asn: number, rank: number, ev4: number) => ({ ...as(asn, rank, 'medium'), period: { ...periodo, events_per_prefix_per_day_v4: ev4 } } as AsStability)
    const data = { ...base([v4(1, 1, 0.1), v4(2, 2, 0.2)]), ordens: { epppd_v4: { desc: [77, 2], asc: [1, 2] } }, as_stability_ordens: [v4(77, 40, 50)] }
    montar(<StabilitySection data={data} totalMedioOuMaior={50} onPedirTodos={() => {}} />)
    expect(screen.queryByRole('link', { name: 'AS77' })).toBeNull()
    fireEvent.click(screen.getByText('v4'))
    const links = screen.getAllByRole('link', { name: /^AS\d+$/ }).map((l) => l.textContent)
    expect(links.slice(0, 2)).toEqual(['AS77', 'AS2'])
  })

  it('sem a visão geral (documento completo) continua contando as categorias no próprio documento', () => {
    montar(<StabilitySection data={base([as(1, 1, 'high', 'critico'), as(2, 2, 'low', 'estavel')])} />)
    expect(screen.getAllByText('Crítico').length).toBeGreaterThan(0)
  })
})
