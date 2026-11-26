// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import colors from 'tailwindcss/colors'
import { describe, expect, it } from 'vitest'
import { ROTULO_SELO, type Selo } from '../components/entidade/proveniencia'
import { contraste } from './contraste'
import { aspectoDoSelo, FUNDOS_NEUTROS, PALETA_SELOS, TEXTOS_CAIXA } from './paletaSelos'

const SELOS = Object.keys(ROTULO_SELO) as Selo[]
const ESCALA: Record<Selo, Record<number, string>> = { fato: colors.emerald, inferido: colors.amber, estimado: colors.violet }

describe('paleta dos selos (PT-30)', () => {
  it('cobre todo selo do vocabulário, com uma forma diferente por selo', () => {
    expect(Object.keys(PALETA_SELOS).sort()).toEqual([...SELOS].sort())
    expect(new Set(SELOS.map((s) => PALETA_SELOS[s].forma)).size).toBe(SELOS.length)
  })

  it('os hexadecimais e as classes descrevem as cores da escala do tailwind.config', () => {
    for (const s of SELOS) {
      const a = PALETA_SELOS[s]
      expect(a.hex.simbolo).toBe(ESCALA[s][a.passos.simbolo])
      expect(a.hex.faixa).toBe(ESCALA[s][a.passos.faixa])
      expect(a.hex.tinta).toBe(ESCALA[s][a.passos.tinta])
      expect(a.classes.simbolo).toBe(`text-${s}-${a.passos.simbolo}`)
      expect(a.classes.faixa).toBe(`border-l-${s}-${a.passos.faixa}`)
      expect(a.classes.fundoCiclo).toContain(`[&:nth-child(3n+1)]:bg-${s}-${a.passos.tinta}`)
      expect(a.classes.fundoCiclo).toContain('[&:nth-child(3n+2)]:bg-white')
      expect(a.classes.fundoCiclo).toContain('[&:nth-child(3n)]:bg-gray-100')
    }
    expect(FUNDOS_NEUTROS.cinza).toBe(colors.gray[100])
    expect(TEXTOS_CAIXA.valor).toBe(colors.gray[900])
    expect(TEXTOS_CAIXA.rotulo).toBe(colors.gray[600])
  })

  it('texto da caixa tem 4,5:1 ou mais sobre cada fundo (valor, rótulo e referência)', () => {
    let pares = 0
    for (const s of SELOS) {
      const fundos = { tinta: PALETA_SELOS[s].hex.tinta, ...FUNDOS_NEUTROS }
      for (const [fn, f] of Object.entries(fundos)) {
        for (const [tn, t] of Object.entries(TEXTOS_CAIXA)) {
          expect(contraste(t, f), `${s} ${fn} ${tn}`).toBeGreaterThanOrEqual(4.5)
          pares++
        }
      }
    }
    expect(pares).toBe(SELOS.length * 3 * 3)
  })

  it('a forma do selo tem 4,5:1 sobre cada fundo (acima dos 3:1 do WCAG 1.4.11) e a faixa tem 3:1 sobre o branco', () => {
    for (const s of SELOS) {
      const a = PALETA_SELOS[s]
      for (const f of [a.hex.tinta, ...Object.values(FUNDOS_NEUTROS)]) expect(contraste(a.hex.simbolo, f), `${s} sobre ${f}`).toBeGreaterThanOrEqual(4.5)
      expect(contraste(a.hex.faixa, '#ffffff')).toBeGreaterThanOrEqual(3)
    }
  })

  it('selo fora do vocabulário cai no aspecto neutro', () => {
    expect(aspectoDoSelo('desconhecido' as Selo).classes.simbolo).toBe('text-gray-700')
  })
})
