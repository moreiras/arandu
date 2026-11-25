// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { ScmBloco } from './ScmBloco'

describe('ScmBloco sem declaração (OPERADORA-E12)', () => {
  it('diz só o fato e o mês, sem hipótese de causa', () => {
    const dados = { data: { municipios_detalhe: [], asns: [] }, hasScm: true, hasSici: false, b2cPct: 0, indicadores: { mes_referencia: '2026-09' } }
    render(<MemoryRouter><ScmBloco dados={dados as never} snapshot="2026-11-22" /></MemoryRouter>)
    expect(screen.getByText(/Outorga SCM sem declaração ao SICI em 2026-09/)).toBeTruthy()
    const corpo = document.body.textContent ?? ''
    expect(corpo).not.toMatch(/pode não ser|não está em operação|ainda não/i)
  })
})
