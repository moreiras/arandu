// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Série de acessos: sem divisão PF/PJ, nada de área "B2C" igual ao total nem dica "B2B 0" (PANORAMA-E2). */
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AccessHistoryChart } from './AccessHistoryChart'
import { somaValores } from '../../lib/acessos'
import type { SiciSeriePoint } from '../../types/api'

const dica = () => screen.getByText((_, el) => el?.tagName === 'SPAN' && /^\d{4}-\d{2}:/.test(el.textContent ?? ''))
const serie: SiciSeriePoint[] = [['2026-08', 57_000_000, 0, 0], ['2026-09', 58_000_000, 0, 0]]

describe('AccessHistoryChart', () => {
  it('soTotal: sem legenda B2C e a dica mostra só o total, nunca "B2B 0"', () => {
    const { container } = render(<AccessHistoryChart serie={serie} soTotal />)
    expect(screen.queryByText(/B2C/)).toBeNull()
    fireEvent.mouseEnter(container.querySelectorAll('rect')[1])
    expect(dica().textContent).toBe('2026-09: 58.000.000')
    expect(container.querySelectorAll('path')).toHaveLength(1)        // só a linha do total
  })

  it('com PF/PJ (operadora) mantém a área B2C e a dica completa', () => {
    const { container } = render(<AccessHistoryChart serie={[['2026-08', 100, 90, 10], ['2026-09', 120, 100, 20]]} />)
    expect(screen.getByText('B2C (pessoa física)')).toBeInTheDocument()
    fireEvent.mouseEnter(container.querySelectorAll('rect')[1])
    expect(dica().textContent).toBe('2026-09: 120 · B2C 100 · B2B 20')
  })
})

describe('base das barras de geração do móvel (PANORAMA-E1)', () => {
  it('a base é a soma das categorias (todas as linhas), e as barras somam 100%', () => {
    const geracao = { '4G': 176_342_409, '5G': 69_777_357, '2G': 20_876_072, '3G': 13_475_359 }
    const base = somaValores(geracao)
    expect(base).toBe(280_471_197)
    expect(Object.values(geracao).reduce((a, v) => a + (100 * v) / base, 0)).toBeCloseTo(100, 6)
    expect(somaValores(undefined)).toBe(0)
  })
})
