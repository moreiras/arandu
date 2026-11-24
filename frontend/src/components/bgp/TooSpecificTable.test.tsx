// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen } from '@testing-library/react'
import { TooSpecificTable } from './TooSpecificTable'

const e = (prefix: string, has_covering: boolean) => ({ prefix, origin_as: 64500, name: 'Rede', has_covering, is_prefix_br: true })
const v6 = [e('2001:db8::/64', true), e('2001:db8:1::1/128', true), e('2001:db8:2::/56', false)]
const v4 = [e('198.18.0.1/32', true), e('198.18.24.128/26', false), e('198.18.1.0/25', true)]
const linhas = () => Array.from(document.querySelectorAll('tbody tr')).map((tr) => tr.querySelector('td')?.textContent)

describe('prefixos potencialmente filtráveis (BGP-E8)', () => {
  it('mostra todas as linhas por padrão (o mesmo total do cartão), "sem agregado" primeiro', () => {
    render(<MemoryRouter><TooSpecificTable v4={v4} v6={v6} /></MemoryRouter>)
    expect(linhas()).toHaveLength(3)
    expect(linhas()[0]).toBe('2001:db8:2::/56')
    expect(linhas()).toContain('2001:db8::/64')
    expect(screen.getByTestId('too-specific-contagem').textContent).toContain('3 de 3 prefixos')
    fireEvent.click(screen.getByRole('button', { name: /^V4/ }))
    expect(linhas()).toHaveLength(3)
    expect(linhas()[0]).toBe('198.18.24.128/26')
  })

  it('o filtro opcional oculta só rotas de host (/128 e /32), nunca /64', () => {
    render(<MemoryRouter><TooSpecificTable v4={v4} v6={v6} /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: /Ocultar rotas de host/ }))
    expect(linhas()).toEqual(expect.arrayContaining(['2001:db8::/64', '2001:db8:2::/56']))
    expect(linhas()).not.toContain('2001:db8:1::1/128')
    expect(screen.getByTestId('too-specific-contagem').textContent).toMatch(/2 de 3 prefixos · 1 rotas de host \(\/128\) ocultadas/)
  })
})
