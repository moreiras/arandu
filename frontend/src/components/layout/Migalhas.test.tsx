// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Migalhas } from './Migalhas'

describe('Migalhas temáticas', () => {
  it('Mercado › Operadoras › Brisanet: o grupo leva ao 1º item, a lista tem link e a página atual não', () => {
    render(<MemoryRouter><Migalhas grupo="mercado" itens={[{ rotulo: 'Operadoras', to: '/operadoras' }, { rotulo: 'Brisanet' }]} /></MemoryRouter>)
    expect(screen.getByRole('link', { name: 'Mercado' })).toHaveAttribute('href', '/operadoras')
    expect(screen.getByRole('link', { name: 'Operadoras' })).toHaveAttribute('href', '/operadoras')
    expect(screen.queryByRole('link', { name: 'Brisanet' })).toBeNull()
    expect(screen.getByText('Brisanet').closest('li')).toHaveAttribute('aria-current', 'page')
  })
  it('Território › CE › Mossoró', () => {
    render(<MemoryRouter><Migalhas grupo="territorio" itens={[{ rotulo: 'CE', to: '/uf/CE' }, { rotulo: 'Mossoró' }]} /></MemoryRouter>)
    expect(screen.getByRole('link', { name: 'CE' })).toHaveAttribute('href', '/uf/CE')
    expect(screen.getByRole('navigation', { name: 'Você está em' })).toHaveTextContent('Território›CE›Mossoró')
  })
})
