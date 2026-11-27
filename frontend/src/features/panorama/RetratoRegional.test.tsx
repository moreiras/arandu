// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Retrato por região do Panorama técnico (PT-22 / 5.2): as linhas fecham o total e a nota diz que a região é a da sede. */
import { MemoryRouter } from 'react-router-dom'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PALAVRAS_PROIBIDAS } from '../../lib/sintese'
import { linhasRegionais, RetratoRegional } from './RetratoRegional'

const z = (asns: number, usuarios: number, v6: number, roa: number, rs: number) => ({ asns, usuarios, usuarios_ipv6: v6, usuarios_com_roa: roa, usuarios_sessao_rs: rs, asns_com_ipv6: 0 })
const por = {
  regioes: [
    { regiao: 'N', nome: 'Norte', ...z(580, 5_900_000, 3_100_000, 3_800_000, 3_600_000) },
    { regiao: 'NE', nome: 'Nordeste', ...z(2411, 31_700_000, 12_400_000, 21_300_000, 20_100_000) },
    { regiao: 'CO', nome: 'Centro-Oeste', ...z(859, 6_000_000, 3_000_000, 3_900_000, 3_200_000) },
    { regiao: 'SE', nome: 'Sudeste', ...z(3681, 100_500_000, 70_000_000, 62_100_000, 44_100_000) },
    { regiao: 'S', nome: 'Sul', ...z(1521, 16_600_000, 8_600_000, 11_800_000, 12_500_000) },
  ],
  sem_regiao: z(77, 588_456, 0, 549_040, 423_846),
  total: z(9129, 161_288_456, 97_100_000, 103_449_040, 83_923_846),
  fonte: 'x', nota: 'y',
}

describe('RetratoRegional', () => {
  it('linhas das cinco regiões, a sem região e o total, com os percentuais da própria linha', () => {
    const l = linhasRegionais(por)
    expect(l.map((x) => x.id)).toEqual(['N', 'NE', 'CO', 'SE', 'S', 'sem_regiao', 'total'])
    expect(l[1].ipv6).toBeCloseTo((100 * 12_400_000) / 31_700_000)
    expect(linhasRegionais(null)).toEqual([])
  })

  it('sem usuários na linha o percentual é nulo, nunca zero', () => {
    const vazio = { ...por, regioes: [{ regiao: 'N', nome: 'Norte', ...z(1, 0, 0, 0, 0) }, ...por.regioes.slice(1)] }
    expect(linhasRegionais(vazio)[0].ipv6).toBeNull()
  })

  it('tabela acessível com cabeçalhos de coluna e de linha e a nota da sede', () => {
    render(<MemoryRouter><RetratoRegional por={por} dataRef="2026-11-22" /></MemoryRouter>)
    const t = screen.getByRole('table')
    expect(within(t).getAllByRole('columnheader')).toHaveLength(6)
    expect(within(t).getByRole('rowheader', { name: 'Nordeste' })).toBeInTheDocument()
    expect(within(t).getByRole('rowheader', { name: 'ASNs sem região' })).toBeInTheDocument()
    expect(within(t).getByText('3.681')).toBeInTheDocument()
    const nota = screen.getByTestId('retrato-regional-nota').textContent ?? ''
    expect(nota).toContain('sede da empresa dona do AS, não a dos usuários')
    expect(nota).toContain('77 ASNs sem região')
    expect(PALAVRAS_PROIBIDAS.test(nota)).toBe(false)
  })

  it('sem o agregado a seção não aparece', () => {
    const { container } = render(<MemoryRouter><RetratoRegional por={undefined} /></MemoryRouter>)
    expect(container).toBeEmptyDOMElement()
  })
})
