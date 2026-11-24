// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { contrasteComBranco, contrasteComEscuro, corDaCelula, METRICAS } from './CartogramaUfs'
import { LEGENDA_SEQUENCIAL } from '../../lib/escalasMapa'

describe('cor do texto das células do cartograma', () => {
  it('em toda a escala o texto escolhido tem contraste de pelo menos 4,5:1 (WCAG AA)', () => {
    for (let t = 0; t <= 100; t++) {
      const { fundo, escuro } = corDaCelula(t, 100)
      const c = escuro ? contrasteComBranco(fundo) : contrasteComEscuro(fundo)
      expect(c, `t=${t} fundo=${fundo} ${escuro ? 'texto branco' : 'texto preto'}`).toBeGreaterThanOrEqual(4.5)
    }
  })
  it('célula sem dado fica cinza claro com texto escuro', () => {
    expect(corDaCelula(null, 100)).toEqual({ fundo: 'rgb(243 244 246)', escuro: false })
  })
})

describe('legenda da escala', () => {
  it('maior valor é a cor mais clara (amarelo), e nenhuma nota diz o contrário', () => {
    expect(contrasteComEscuro(corDaCelula(100, 100).fundo)).toBeGreaterThan(contrasteComEscuro(corDaCelula(0, 100).fundo))
    expect(LEGENDA_SEQUENCIAL).toMatch(/roxo \(menor valor\) ao amarelo \(maior valor\)/)
    for (const m of METRICAS) expect(m.nota ?? '', m.rotulo).not.toMatch(/mais escuro/i)
  })
})
