// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Portas da Home por lente (PT-27, home 5.3): cinco lentes, pergunta em texto, três links em lista, todo destino existe e a persona não esconde página. */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { MemoryRouter } from 'react-router-dom'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { GRUPOS_MENU, ITENS_AVULSOS } from '../../components/layout/menu'
import { PORTAS, PortasPorPublico, TAMBEM } from './PortasPorPublico'

const main = readFileSync(resolve(__dirname, '../../main.tsx'), 'utf-8')
const rotas = new Set([...main.matchAll(/<Route path="([^"]+)"/g)].map((m) => '/' + m[1]))
const caminho = (to: string) => to.split('?')[0]
const noMenu = new Set([...GRUPOS_MENU.flatMap((g) => g.itens), ...ITENS_AVULSOS].map((i) => caminho(i.to)))

describe('portas por lente', () => {
  it('são as cinco lentes: técnico, regulação, jornalismo, política pública e empresa', () => {
    expect(PORTAS.map((p) => p.id)).toEqual(['tecnico', 'regulador', 'jornalista', 'politicas', 'empresa'])
  })

  it('cada porta tem h3, a pergunta em texto e três links em lista, sublinhados e com alvo de 24 px', () => {
    render(<MemoryRouter><PortasPorPublico /></MemoryRouter>)
    for (const p of PORTAS) {
      const card = screen.getByTestId(`porta-${p.id}`)
      expect(within(card).getByRole('heading', { level: 3, name: p.titulo })).toBeInTheDocument()
      expect(within(card).getByText(p.pergunta)).toBeInTheDocument()
      const links = within(within(card).getByRole('list')).getAllByRole('link')
      expect(links).toHaveLength(3)
      for (const a of links) { expect(a.className).toContain('underline'); expect(a.className).toContain('min-h-6') }
    }
  })

  it('todo link da Home existe como rota e como item do menu (ou da linha "Também")', () => {
    const todos = [...PORTAS.flatMap((p) => p.links), ...TAMBEM]
    for (const l of todos) {
      expect(rotas, l.to).toContain(caminho(l.to))
      expect(noMenu, l.to).toContain(caminho(l.to))
    }
  })

  it('as páginas antes só alcançáveis pelo menu ficam a um clique: Panorama técnico, API e MCP, Fontes', () => {
    const destinos = new Set([...PORTAS.flatMap((p) => p.links), ...TAMBEM].map((l) => caminho(l.to)))
    for (const d of ['/panorama/tecnico', '/dados', '/fontes']) expect(destinos.has(d), d).toBe(true)
  })

  it('o título não sugere vínculo institucional e nenhuma porta usa a cor do IPv4 como identidade', () => {
    for (const p of PORTAS) expect(p.titulo).not.toMatch(/fiscalizo|regulo\b|anatel/i)
    const fonte = readFileSync(resolve(__dirname, 'PortasPorPublico.tsx'), 'utf-8')
    expect(fonte).not.toMatch(/text-v4-|text-mercado-|text-primario-700 border/)
  })
})
