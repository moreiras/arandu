// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PaginaNaoEncontrada } from './PaginaNaoEncontrada'

describe('página 404 (INST-E3)', () => {
  it('tem h1, busca e links úteis', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={['/nao-existe']}><PaginaNaoEncontrada /></MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Página não encontrada')
    expect(screen.getByRole('combobox', { name: 'Buscar no site' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Início' })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: 'Mapa do site' })).toHaveAttribute('href', '/mapa-do-site')
  })
})
