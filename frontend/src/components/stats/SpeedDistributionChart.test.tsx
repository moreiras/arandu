// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { DistribVelocidade } from '../../types/api'
import { SpeedDistributionChart } from './SpeedDistributionChart'

describe('panorama: alternâncias com estado (OPERADORA-E5, PANORAMA)', () => {
  it('PF/PJ da distribuição de velocidade são botões com aria-pressed', () => {
    const distrib = { SP: { pf: { '12Mbps a 34Mbps': 10 }, pj: { '12Mbps a 34Mbps': 5 } } } as unknown as DistribVelocidade
    render(<SpeedDistributionChart distrib={distrib} />)
    const grupo = screen.getByRole('group', { name: 'Tipo de assinante' })
    const [todos, pf] = within(grupo).getAllByRole('button')
    expect(todos).toHaveAttribute('type', 'button')
    expect(todos).toHaveAttribute('aria-pressed', 'true')
    expect(pf).toHaveAttribute('aria-pressed', 'false')
    fireEvent.click(pf)
    expect(pf).toHaveAttribute('aria-pressed', 'true')
    expect(todos).toHaveAttribute('aria-pressed', 'false')
  })

  it('as abas de "Maiores operadoras" (SICI × APNIC) têm type e aria-pressed', () => {
    const fonte = readFileSync(resolve(__dirname, 'BandaLargaFixaSection.tsx'), 'utf-8')
    expect(fonte).toContain(`<button type="button" aria-pressed={aba === 'sici'}`)
    expect(fonte).toContain(`<button type="button" aria-pressed={aba === 'asn'}`)
  })
})
