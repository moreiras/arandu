// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MoasTable } from './MoasTable'
import { SummaryCards } from './SummaryCards'
import type { MoasEntry, MoasResumo, RoutingAnalysis } from '../../types/routingAnalysis'

const origem = (asn: number, coletores: string[], asn_br = true) => ({ asn, name: `Rede ${asn}`, coletores: coletores.length, coletores_nomes: coletores, asn_br })
const lista: MoasEntry[] = [
  { prefix: '2001:db8::/48', afi: 'v6', origins: [64496, 4200000102], br_origins: [64496], is_prefix_br: true,
    origens: [origem(64496, ['rvT']), origem(4200000102, ['rvU'], false)] },
  { prefix: '198.18.0.0/24', afi: 'v4', origins: [64496, 64497], br_origins: [64496, 64497], is_prefix_br: true,
    origens: [origem(64496, ['rvT', 'rvU']), origem(64497, ['rvU'])] },
]
const resumo: MoasResumo = {
  prefixos: { v6: { global: 1, br: 1 }, v4: { global: 2, br: 1 } }, coletores: { v6: ['rvT', 'rvU'], v4: ['rvT', 'rvU'] },
  lista: 'prefixos brasileiros', lista_truncada: false, lista_limite: 2000, definicao: 'd', como_ler: 'c', limites: 'l',
}
const linhas = () => Array.from(document.querySelectorAll('tbody tr')).map((tr) => tr.querySelector('th')?.textContent)

describe('MoasTable (PT-04b / BGP-E2)', () => {
  it('tabela acessível: caption, cabeçalhos de coluna e de linha; IPv6 antes de IPv4', () => {
    render(<MemoryRouter><MoasTable data={lista} resumo={resumo} date="2026-09-20" /></MemoryRouter>)
    const tabela = screen.getByRole('table')
    expect(tabela.querySelector('caption')?.textContent).toMatch(/mais de um AS de origem/)
    expect(within(tabela).getAllByRole('columnheader').every((th) => th.getAttribute('scope') === 'col')).toBe(true)
    expect(within(tabela).getAllByRole('rowheader')).toHaveLength(2)
    expect(linhas()).toEqual(['2001:db8::/48', '198.18.0.0/24'])
    expect(screen.getByRole('link', { name: '198.18.0.0/24' })).toHaveAttribute('href', '/prefixo/198.18.0.0/24?date=2026-09-20')
    expect(screen.getByTestId('moas-contagem').textContent).toBe(
      'IPv6: 1 brasileiros de 1 na tabela, entre 2 coletores · IPv4: 1 brasileiros de 2 na tabela, entre 2 coletores')
    fireEvent.click(screen.getByRole('button', { name: 'IPv4' }))
    expect(linhas()).toEqual(['198.18.0.0/24'])
    expect(document.body.textContent).toMatch(/AS64497 1 coletor/)
    expect(document.body.textContent).not.toMatch(/sequestro|hijack|anycast/i)
  })

  it('zero observado com coleta capaz: estado vazio honesto, sem tabela', () => {
    const zero = { ...resumo, prefixos: { v6: { global: 0, br: 0 }, v4: { global: 3, br: 0 } } }
    render(<MemoryRouter><MoasTable data={[]} resumo={zero} /></MemoryRouter>)
    expect(screen.queryByRole('table')).toBeNull()
    expect(screen.getByTestId('moas-vazio').textContent).toMatch(/Nenhum MOAS observado neste snapshot/)
  })

  it('família sem medida aparece como "não medido", não como zero', () => {
    render(<MemoryRouter><MoasTable data={lista.slice(1)} resumo={{ ...resumo, prefixos: { v6: null, v4: { global: 2, br: 1 } }, coletores: { v6: null, v4: ['rvT'] } }} /></MemoryRouter>)
    expect(screen.getByTestId('moas-contagem').textContent).toMatch(/^IPv6: não medido neste snapshot · IPv4: 1 brasileiros/)
  })
})

const base = {
  summary: { v6: { pbr_routes: 1, pbr_pct: 1, br_origin_asns: 1, total_prefixes_global: 1, total_asns_global: 1 },
    v4: { pbr_routes: 1, pbr_pct: 1, br_origin_asns: 1, total_prefixes_global: 1, total_asns_global: 1 } },
  more_specifics: { v6: { pbr_root: 1, pbr_more_specific: 0 }, v4: { pbr_root: 1, pbr_more_specific: 0 } },
  too_specific: { v6: [], v4: [] },
  pbr_composition: { v6: { total: {} }, v4: { total: {} } },
  br_asns_visible: 1, br_asns_registered: 1,
}
const cartao = () => screen.getByText(/^MOAS/).closest('div.rounded-lg') as HTMLElement

describe('cartão de MOAS da /bgp: três estados', () => {
  it('com MOAS: brasileiros por família e o total da tabela', () => {
    render(<SummaryCards data={{ ...base, moas: lista, moas_resumo: resumo } as unknown as RoutingAnalysis} />)
    expect(cartao().textContent).toMatch(/1 · 1/)
    expect(cartao().textContent).toMatch(/3 prefixos com origem múltipla na tabela inteira/)
  })

  it('zero observado: 0, não "não medido"', () => {
    const zero = { ...resumo, prefixos: { v6: { global: 0, br: 0 }, v4: { global: 0, br: 0 } } }
    render(<SummaryCards data={{ ...base, moas: [], moas_resumo: zero } as unknown as RoutingAnalysis} />)
    expect(cartao().textContent).toMatch(/0 · 0/)
  })

  it('snapshot sem o artefato: "não medido"', () => {
    render(<SummaryCards data={{ ...base, moas: null, moas_resumo: null } as unknown as RoutingAnalysis} />)
    expect(cartao().textContent).toMatch(/não medido/)
  })
})
