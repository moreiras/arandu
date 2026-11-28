// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { contrasteComBranco, contrasteComEscuro, corDaCelula, METRICAS, METRICAS_ESTADOS, METRICAS_NORMALIZADAS } from './CartogramaUfs'
import { ESCALA_UM_TOM, LEGENDA_SEQUENCIAL } from '../../lib/escalasMapa'

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

describe('indicadores de rede (estados 5.4)', () => {
  it('a escala de um tom mantém contraste de 4,5:1 com o texto da célula', () => {
    for (let t = 0; t <= 100; t++) {
      const { fundo, escuro } = corDaCelula(t, 100, ESCALA_UM_TOM)
      const c = escuro ? contrasteComBranco(fundo) : contrasteComEscuro(fundo)
      expect(c, `t=${t} fundo=${fundo}`).toBeGreaterThanOrEqual(4.5)
    }
  })
  it('todo botão de /estados existe, prontidão e HHI declaram o n e o aviso, e nenhum rótulo estimado ou inferido perde o selo', () => {
    for (const id of METRICAS_ESTADOS) expect(METRICAS.some((m) => m.id === id), id).toBe(true)
    for (const id of ['prontidao', 'hhi_transito']) {
      const m = METRICAS.find((x) => x.id === id)!
      expect(m.n, id).toBeTypeOf('function')
      expect(m.aviso, id).toBe(true)
      expect(m.umTom, id).toBe(true)
    }
    expect(METRICAS.find((m) => m.id === 'ipv6')!.rotulo).toBe('% de acessos em IPv6 (estimado)')
    expect(METRICAS.find((m) => m.id === 'transito_unico')!.rotulo).toMatch(/\(inferido\)$/)
    expect(METRICAS.find((m) => m.id === 'rov')!.rotulo).toMatch(/\(estimado\)$/)
    expect(METRICAS.find((m) => m.id === 'nao_visto')!.rotulo).toMatch(/\(estimado\)$/)
  })
  it('os indicadores sensíveis ficam fora da lista de comparação normalizada com posição (home e página da UF)', () => {
    for (const id of ['prontidao', 'hhi_transito', 'transito_unico', 'ipv6', 'rov', 'nao_visto']) expect(METRICAS_NORMALIZADAS).not.toContain(id)
  })
})
