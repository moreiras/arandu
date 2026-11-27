// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { V6_BLOCKS } from './hilbert'
import { LADO_FINO_PX, MAX_MARCADORES, celulasIsoladas, posicaoCelulaV6 } from './isoladas'

const lacnic = V6_BLOCKS.find((b) => b.id === 'lacnic')!
const legado = V6_BLOCKS.find((b) => b.id === 'legacy')!
const pos12 = posicaoCelulaV6(lacnic.gridSize)

describe('critério de célula IPv6 fina e isolada', () => {
  it('marca a célula sozinha e não marca as que formam mancha', () => {
    // 1000 e 1001 são vizinhas na curva (e na grade); 0 e 500000 estão sozinhas.
    const r = celulasIsoladas([0, 1000, 1001, 500000], pos12, lacnic.gridSize, 240)
    expect(r).toEqual([0, 500000])
  })

  it('duas células em pixels de tela vizinhos não são isoladas; em pixels afastados, são', () => {
    const lado = 240 / 1024
    const tam = Math.ceil(LADO_FINO_PX / lado)
    const acha = (dx: number) => { for (let d = 1; d < 5000; d++) { const [x, y] = pos12(d); if (y === 0 && x === dx) return d } return -1 }
    const perto = acha(tam)
    const longe = acha(tam * 4)
    expect(perto).toBeGreaterThan(0)
    expect(longe).toBeGreaterThan(0)
    expect(celulasIsoladas([0, perto], pos12, 1024, 240)).toEqual([])
    expect(celulasIsoladas([0, longe], pos12, 1024, 240).sort((a, b) => a - b)).toEqual([0, longe].sort((a, b) => a - b))
  })

  it('só vale para célula fina: com lado de 1 px ou mais na tela, nada é marcado', () => {
    expect(celulasIsoladas([0, 500000], pos12, 1024, 1024)).toEqual([])
    expect(celulasIsoladas([0, 500000], pos12, 1024, 1023)).toEqual([0, 500000])
  })

  it('no bloco legado (256), 220 px deixa a célula fina e 260 px não', () => {
    const pos = posicaoCelulaV6(legado.gridSize)
    expect(celulasIsoladas([0], pos, 256, 220)).toEqual([0])
    expect(celulasIsoladas([0], pos, 256, 260)).toEqual([])
  })

  it('sem células ou sem largura, nada; e respeita o teto de marcadores', () => {
    expect(celulasIsoladas([], pos12, 1024, 240)).toEqual([])
    expect(celulasIsoladas(null, pos12, 1024, 240)).toEqual([])
    expect(celulasIsoladas([0], pos12, 1024, 0)).toEqual([])
    // células a cada 64 colunas e 64 linhas da grade: nenhuma tem vizinha
    const muitas: number[] = []
    const mapa = new Map<string, number>()
    for (let d = 0; d < 1 << 20 && mapa.size < 16 * 16; d++) {
      const [x, y] = pos12(d)
      if (x % 64 === 0 && y % 64 === 0) { mapa.set(`${x},${y}`, d); muitas.push(d) }
    }
    expect(celulasIsoladas(muitas, pos12, 1024, 240)).toHaveLength(Math.min(muitas.length, MAX_MARCADORES))
  })
})
