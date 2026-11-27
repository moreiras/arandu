// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import '../asn'
import '../ptt'
import '../operadora'
import '../grupo'
import '../uf'
import '../municipio'
import '../prefixo'
import { abasDe, todosOsBlocos } from '../entidade/registry'
import type { Catalogo } from './catalogo'
import { UsoDasFontes } from './UsoDasFontes'
import { indiceFontePaginas, PAGINAS_ENTIDADE, porPagina } from './usoFontes'

const catalogo: Catalogo = JSON.parse(readFileSync(resolve(__dirname, '../../../public/catalogo.json'), 'utf-8'))
const ids = catalogo.fontes.map((f) => f.id)

describe('índice fonte para páginas (FONT 5.5)', () => {
  it('toda fonte declarada por algum bloco de qualquer entidade está no índice, com o bloco que a declara', () => {
    const indice = indiceFontePaginas(todosOsBlocos(), ids, abasDe)
    let pares = 0
    for (const b of todosOsBlocos()) {
      for (const f of new Set(b.fontes)) {
        pares++
        expect(indice.get(f), `${b.entidade}/${b.id}: fonte ${f} fora do índice`).toBeDefined()
        expect(indice.get(f)!.some((u) => u.entidade === b.entidade && u.blocoId === b.id), `${b.entidade}/${b.id} não consta em ${f}`).toBe(true)
      }
    }
    expect([...indice.values()].reduce((n, l) => n + l.length, 0)).toBe(pares)
  })

  it('toda entidade registrada tem nome de página no índice', () => {
    const nomes = new Set(PAGINAS_ENTIDADE.map(([e]) => e))
    for (const e of new Set(todosOsBlocos().map((b) => b.entidade))) expect(nomes.has(e), `entidade ${e} sem nome de página`).toBe(true)
  })

  it('o índice cobre todas as fontes do catálogo: ou lista blocos, ou fica explícita sem bloco', () => {
    const indice = indiceFontePaginas(todosOsBlocos(), ids, abasDe)
    expect([...indice.keys()].sort()).toEqual([...ids].sort())
  })

  it('agrupa por página e traz a aba do bloco quando a entidade tem abas', () => {
    const indice = indiceFontePaginas(todosOsBlocos(), ids, abasDe)
    const usos = indice.get('rpki_collector')!
    expect(usos.length).toBeGreaterThan(0)
    expect(porPagina(usos).map((g) => g.pagina)).toContain('Página de AS')
    expect(usos.some((u) => u.aba)).toBe(true)
  })
})

describe('UsoDasFontes', () => {
  it('recolhido por padrão; ao abrir, monta o índice e diz o que não cobre', async () => {
    render(<QueryClientProvider client={new QueryClient()}><UsoDasFontes fontes={catalogo.fontes} /></QueryClientProvider>)
    expect(screen.queryAllByTestId('uso-fonte')).toHaveLength(0)
    const det = screen.getByTestId('uso-das-fontes') as HTMLDetailsElement
    det.open = true
    fireEvent(det, new Event('toggle'))
    await waitFor(() => expect(screen.getAllByTestId('uso-fonte').length).toBeGreaterThan(0), { timeout: 20000 })
    expect(document.querySelector('[data-fonte="rpki_collector"]')?.textContent).toMatch(/Página de AS/)
    expect(screen.getByText(/Cada bloco combina várias fontes/)).toBeInTheDocument()
  }, 30000)
})
