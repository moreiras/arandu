// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../test/server'
import { SITE } from '../lib/site'
import { Snapshots } from './Snapshots'
import { Sobre } from './Sobre'

// D8: sem promessa de imutabilidade absoluta. Lê o código das páginas e do menu como texto.
const fontes = import.meta.glob(['./Snapshots.tsx', './Sobre.tsx', './DadosPage.tsx', '../components/layout/menu.ts'], { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const PROIBIDAS = [/snapshot\s+imutável/i, /imutável após publicação/i, /nenhum dado é sobrescrito/i, /coletados semanalmente/i, /datad[oa]s e imutáveis/i]
const FRASE = /Snapshots publicados não mudam, salvo correção registrada no CHANGELOG do projeto; quando a correção altera um número publicado, as páginas afetadas trazem uma nota datada\./

const montar = (el: JSX.Element) => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>{el}</MemoryRouter></QueryClientProvider>,
)

describe('D8: imutabilidade e correções', () => {
  it('as frases antigas não voltam ao código das páginas', () => {
    expect(Object.keys(fontes).length).toBe(4)
    for (const [arq, texto] of Object.entries(fontes)) for (const re of PROIBIDAS) expect(texto, `${arq} ${re}`).not.toMatch(re)
  })

  it('/snapshots traz a frase factual e o link do CHANGELOG no código-fonte da instância', async () => {
    server.use(http.get('*/api/v1/brasil/snapshots', () => HttpResponse.json({ count: 0, latest: null, snapshots: [] })))
    montar(<Snapshots />)
    const link = (await screen.findAllByRole('link', { name: 'CHANGELOG' }))[0]
    expect(link.getAttribute('href')).toBe(`${SITE.codigoFonte}/blob/main/CHANGELOG.md`)
    expect(document.body.textContent).toMatch(FRASE)
    expect(document.body.textContent).not.toMatch(/imutável/i)
  })

  it('/sobre diz publicados semanalmente, fonte no próprio calendário, e traz a frase e o link', () => {
    montar(<Sobre />)
    const texto = document.body.textContent ?? ''
    expect(texto).toMatch(/publicados\s+semanalmente; cada fonte é coletada no seu próprio calendário/)
    expect(texto).toMatch(FRASE)
    expect(texto).not.toMatch(/imutável|sobrescrito|coletados semanalmente/i)
    const link = screen.getByRole('link', { name: 'CHANGELOG' })
    expect(link.getAttribute('href')).toBe(`${SITE.codigoFonte}/blob/main/CHANGELOG.md`)
  })
})
