// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DESCRICAO_SELO, ROTULO_SELO, type Selo } from '../components/entidade/proveniencia'
import { Sobre } from './Sobre'

describe('Sobre: definição pública dos selos', () => {
  it('traz exatamente os selos de proveniencia.ts, com rótulo e descrição idênticos às constantes', () => {
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><Sobre /></MemoryRouter></QueryClientProvider>)
    const secao = screen.getByTestId('sobre-selos')
    const chaves = Object.keys(ROTULO_SELO) as Selo[]
    expect(Object.keys(DESCRICAO_SELO).sort()).toEqual([...chaves].sort())
    expect(secao.querySelectorAll('[data-selo-def]')).toHaveLength(chaves.length)
    for (const k of chaves) {
      const def = secao.querySelector(`[data-selo-def="${k}"]`) as HTMLElement
      expect(def.textContent).toBe(DESCRICAO_SELO[k])
      expect(within(secao).getByText(`${ROTULO_SELO[k]}:`)).toBeInTheDocument()
    }
  })
})
