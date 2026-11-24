// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { useAppStore } from '../store/app'
import { RelatorioPage } from './RelatorioPage'

beforeEach(() => { useAppStore.setState({ activeDate: null, latestSnapshot: '2026-09-20' }) })

describe('relatório: selo além da cor (REL-E9)', () => {
  it('cada frase e cada linha do quadro têm o selo em texto visível', async () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/relatorio/asn/64496']}><Routes><Route path="/relatorio/:tipo/:id" element={<RelatorioPage />} /></Routes></MemoryRouter>
      </QueryClientProvider>,
    )
    await screen.findByTestId('relatorio')
    const linhas = within(screen.getByRole('region', { name: 'Indicadores' })).getAllByRole('row')
    expect(linhas.length).toBeGreaterThan(0)
    for (const tr of linhas) {
      const selo = tr.querySelector('[data-selo]')
      expect(selo, tr.textContent ?? '').not.toBeNull()
      expect(selo).toHaveTextContent(/^(Fato|Inferido|Estimado)$/)
      expect(selo).not.toHaveClass('sr-only')
    }
    const sintese = screen.queryByRole('region', { name: 'Síntese' })
    if (sintese) for (const li of within(sintese).getAllByRole('listitem')) expect(li.querySelector('[data-selo]')).toHaveTextContent(/^(Fato|Inferido|Estimado)$/)
  })

  it('a impressão mantém as cores do selo (print-color-adjust)', () => {
    const css = readFileSync(resolve(__dirname, '../index.css'), 'utf-8')
    expect(css).toMatch(/\[data-testid="relatorio"\] \{[^}]*print-color-adjust: exact/)
  })
})
