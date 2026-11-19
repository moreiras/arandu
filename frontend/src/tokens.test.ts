// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import colors from 'tailwindcss/colors'
import { describe, expect, it } from 'vitest'
import { CATEGORIAS_SEGURAS, corDaEscala, ESCALA_SEQUENCIAL } from './lib/escalasMapa'

function arquivos(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n)
    return statSync(p).isDirectory() ? arquivos(p) : /\.(ts|tsx)$/.test(n) ? [p] : []
  })
}
const FONTES = arquivos(__dirname).filter((p) => !p.endsWith('tokens.test.ts'))

describe('sistema visual: tokens', () => {
  it('nenhuma família de cor da paleta crua do Tailwind fora dos papéis semânticos', () => {
    const rx = /(?<![\w-])(?:bg|text|border|ring|from|to|via|divide|fill|stroke|outline|accent|decoration|shadow)-(?:red|green|blue|amber|yellow|purple|indigo|emerald|orange|teal|cyan|rose|pink|sky|violet|lime|fuchsia)-\d{2,3}/
    const achados = FONTES.filter((p) => rx.test(readFileSync(p, 'utf8')))
    expect(achados).toEqual([])
  })
  it('nenhum texto abaixo de 12 px (9, 10 e 11 px)', () => {
    const achados = FONTES.filter((p) => /text-\[(?:[0-9]|1[01])px\]/.test(readFileSync(p, 'utf8')))
    expect(achados).toEqual([])
  })
})

function luminancia(hex: string): number {
  const v = [0, 2, 4].map((i) => parseInt(hex.slice(1 + i, 3 + i), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
}
const contraste = (a: string, b: string) => {
  const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p)
  return (x + 0.05) / (y + 0.05)
}

describe('sistema visual: contraste (WCAG AA = 4,5:1 para texto)', () => {
  // pares usados pelos componentes: texto 700 sobre fundo 50 (selos) e texto 700/800 sobre branco
  const papeis = { fato: colors.emerald, inferido: colors.amber, estimado: colors.violet, primario: colors.blue, ok: colors.green, aviso: colors.amber, perigo: colors.red, alerta: colors.orange, v6: colors.purple, mercado: colors.emerald, tecnico: colors.sky }
  for (const [nome, escala] of Object.entries(papeis)) {
    it(`${nome}: 700 sobre 50 e sobre branco`, () => {
      expect(contraste(escala[700], escala[50])).toBeGreaterThanOrEqual(4.5)
      expect(contraste(escala[700], '#ffffff')).toBeGreaterThanOrEqual(4.5)
    })
  }
  it('escalas de mapa: a sequencial é monótona em luminosidade (legível em cinza)', () => {
    const l = ESCALA_SEQUENCIAL.map(luminancia)
    expect([...l].sort((a, b) => a - b)).toEqual(l)
    expect(corDaEscala(ESCALA_SEQUENCIAL, 0)).toBe('#440154')
    expect(corDaEscala(ESCALA_SEQUENCIAL, 1)).toBe('#fde725')
    expect(corDaEscala(ESCALA_SEQUENCIAL, Number.NaN)).toBe('#440154')
  })
  it('categorias seguras: 8 cores distintas', () => {
    expect(new Set(CATEGORIAS_SEGURAS).size).toBe(8)
  })
})
