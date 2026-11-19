// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { calcularQuebras, classeDe, DESCRICAO_METODO, rotulosDasClasses } from './quebras'

describe('quebras de classes', () => {
  const v = Array.from({ length: 101 }, (_, i) => i)       // 0..100
  it('quantis: classes com o mesmo número de valores', () => {
    const q = calcularQuebras(v, 4)
    expect(q).toEqual([25, 50, 75])
    const cont = [0, 0, 0, 0]
    for (const x of v) cont[classeDe(x, q)]++
    expect(Math.max(...cont) - Math.min(...cont)).toBeLessThanOrEqual(1)
  })
  it('intervalos iguais: largura igual entre o mínimo e o máximo', () => {
    expect(calcularQuebras([0, 10, 90, 100], 5, 'intervalos-iguais')).toEqual([20, 40, 60, 80])
  })
  it('ignora nulos e NaN; sem dado ou 1 classe devolve vazio', () => {
    expect(calcularQuebras([null, undefined, NaN, 1, 2, 3, 4], 2)).toEqual([2.5])
    expect(calcularQuebras([], 5)).toEqual([])
    expect(calcularQuebras([1, 2, 3], 1)).toEqual([])
  })
  it('dados muito repetidos não geram quebras iguais', () => {
    const q = calcularQuebras([1, 1, 1, 1, 1, 1, 1, 1, 9], 5)
    expect(q).toEqual([...new Set(q)].sort((a, b) => a - b))
  })
  it('classeDe: limite inferior inclusivo, extremos nas pontas', () => {
    expect([classeDe(-5, [10, 20]), classeDe(10, [10, 20]), classeDe(19.9, [10, 20]), classeDe(20, [10, 20]), classeDe(1e9, [10, 20])]).toEqual([0, 1, 1, 2, 2])
    expect(classeDe(3, [])).toBe(0)
  })
  it('rótulos da legenda: um por classe', () => {
    const f = (x: number) => String(x)
    expect(rotulosDasClasses([10, 20], f)).toEqual(['menos de 10', '10 a 20', '20 ou mais'])
    expect(rotulosDasClasses([], f)).toEqual(['todos os valores'])
  })
  it('os dois métodos têm descrição para a legenda', () => {
    expect(DESCRICAO_METODO.quantis).toMatch(/mesmo número/)
    expect(DESCRICAO_METODO['intervalos-iguais']).toMatch(/mesma largura/)
  })
})
