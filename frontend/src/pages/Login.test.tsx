// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import colors from 'tailwindcss/colors'
import { describe, expect, it } from 'vitest'
import { contraste } from '../lib/contraste'
import { Login } from './Login'

describe('Login: erro acessível (INST-E10)', () => {
  it('o erro é anunciado (role=alert) e tem contraste ≥ 4,5:1 sobre o fundo', () => {
    render(<MemoryRouter initialEntries={['/login?error=cancelled']}><Login /></MemoryRouter>)
    const alerta = screen.getByRole('alert')
    expect(alerta).toHaveTextContent('Login cancelado.')
    expect(alerta.className).toContain('text-perigo-700')
    expect(alerta.className).toContain('bg-perigo-50')
    expect(contraste(colors.red[700], colors.red[50])).toBeGreaterThanOrEqual(4.5)
    // a combinação antiga ficava abaixo
    expect(contraste(colors.red[600], colors.red[50])).toBeLessThan(4.5)
  })

  it('sem erro, nada de alerta; o hover do LinkedIn é por classe, sem JavaScript', () => {
    render(<MemoryRouter initialEntries={['/login']}><Login /></MemoryRouter>)
    expect(screen.queryByRole('alert')).toBeNull()
    const li = screen.getByRole('link', { name: /LinkedIn/ })
    expect(li.className).toContain('hover:bg-[#004182]')
    expect(li.getAttribute('style')).toBeNull()
  })
})
