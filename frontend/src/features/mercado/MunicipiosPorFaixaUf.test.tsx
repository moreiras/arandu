// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Municípios por faixa de HHI local, por UF, no Panorama de mercado (PT-23 / PANORAMA 5.2): contagem que fecha com o total, por CNPJ e por grupo, sem lista nominal. */
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { MunicipiosPorFaixaUf } from './ConcentracaoPanorama'
import type { MunicipiosPorFaixa } from '../../types/api'

const f = (a: number, b: number, c: number, d = 0): MunicipiosPorFaixa => ({ competitivo: a, moderado: b, concentrado: c, sem_dado: d })
const ufs: [string, { municipios: number; municipios_por_faixa_cnpj: MunicipiosPorFaixa; municipios_por_faixa_grupo: MunicipiosPorFaixa }][] = [
  ['SP', { municipios: 10, municipios_por_faixa_cnpj: f(6, 3, 1), municipios_por_faixa_grupo: f(5, 3, 2) }],
  ['AC', { municipios: 4, municipios_por_faixa_cnpj: f(0, 1, 3), municipios_por_faixa_grupo: f(0, 1, 3) }],
]
const resumo = { municipios: 14, por_faixa_cnpj: f(6, 4, 4), por_faixa_grupo: f(5, 4, 5) }

describe('Municípios por faixa de HHI local, por UF', () => {
  it('traz síntese, legenda, cabeçalhos com escopo e o total do país', () => {
    render(<MemoryRouter><MunicipiosPorFaixaUf ufs={ufs} resumo={resumo} /></MemoryRouter>)
    const sintese = screen.getByTestId('municipios-por-faixa').querySelector('p')!.textContent!
    expect(sintese).toMatch(/Nos 14 municípios, 4 têm HHI local de 2\.500 ou mais por CNPJ e 5 por grupo \(inferido\)/)
    expect(sintese).toMatch(/O HHI da UF, na tabela acima, soma as operadoras de todos os municípios/)
    const t = screen.getByRole('table')
    expect(t.querySelector('caption')?.textContent).toMatch(/por CNPJ declarado e por grupo inferido/)
    expect(t.querySelectorAll('th[scope="colgroup"]').length).toBe(2)
    const brasil = within(t).getByRole('row', { name: /^Brasil/ })
    expect(brasil.textContent).toContain('14')
  })

  it('cada UF fecha: as faixas somam o número de municípios da UF', () => {
    render(<MemoryRouter><MunicipiosPorFaixaUf ufs={ufs} resumo={resumo} /></MemoryRouter>)
    for (const [, v] of ufs) {
      const s = v.municipios_por_faixa_cnpj
      expect(s.competitivo + s.moderado + s.concentrado + s.sem_dado).toBe(v.municipios)
    }
    expect(screen.queryByText(/não somam o total/)).toBeNull()
  })

  it('avisa quando as faixas não somam o total (documento inconsistente)', () => {
    render(<MemoryRouter><MunicipiosPorFaixaUf ufs={ufs} resumo={{ ...resumo, por_faixa_cnpj: f(1, 1, 1) }} /></MemoryRouter>)
    expect(screen.getByText(/não somam o total de municípios/)).toBeTruthy()
  })

  it('ordena por uma faixa com aria-sort e não lista operadora nem líder por nome', () => {
    render(<MemoryRouter><MunicipiosPorFaixaUf ufs={ufs} resumo={resumo} /></MemoryRouter>)
    const cab = screen.getAllByRole('columnheader', { name: /2\.500 ou mais/ })[0]
    fireEvent.click(within(cab).getByRole('button'))
    expect(cab.getAttribute('aria-sort')).toBe('descending')
    const primeira = screen.getAllByRole('row').find((r) => /^(SP|AC) —/.test(r.textContent ?? ''))!
    expect(primeira.textContent).toMatch(/^AC —/)
    expect(screen.getByTestId('municipios-por-faixa').textContent).not.toMatch(/líder|Starlink|Vivo|Claro/i)
  })
})
