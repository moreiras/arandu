// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { inicioDaFaixaKbps, ordenarPorFaixa } from './faixas'

describe('faixas de velocidade', () => {
  it('ordena pela faixa, não pelo valor, e deixa N/I por último', () => {
    const e: [string, number][] = [['> 34 Mbps', 900], ['0-512 kbps', 5], ['N/I', 3], ['2 a 12 Mbps', 70], ['512 kbps a 2 Mbps', 20], ['12 a 34 Mbps', 400]]
    expect(ordenarPorFaixa(e).map(([k]) => k)).toEqual(['0-512 kbps', '512 kbps a 2 Mbps', '2 a 12 Mbps', '12 a 34 Mbps', '> 34 Mbps', 'N/I'])
  })
  it('unidade depois do segundo número vale para o primeiro', () => {
    expect(inicioDaFaixaKbps('2 a 12 Mbps')).toBe(2000)
    expect(inicioDaFaixaKbps('512 kbps a 2 Mbps')).toBe(512)
  })
})
