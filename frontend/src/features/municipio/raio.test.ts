// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { haversineKm, type LonLat } from '../../lib/geo'
import { MAX_MUNICIPIOS_RAIO, circuloGeoJSON, conjuntoNoRaio } from './raio'

// pontos em fila no equador: 1° de longitude ≈ 111,2 km
const fila = (n: number, passo = 0.1): Record<string, LonLat> => Object.fromEntries(Array.from({ length: n }, (_, i) => [String(1000 + i), [i * passo, 0] as LonLat]))

describe('conjuntoNoRaio', () => {
  it('raio 0 é só o município central', () => {
    const c = conjuntoNoRaio('1000', fila(10), 0)!
    expect(c.selecionados).toEqual([{ ibge: '1000', km: 0 }])
    expect(c.cortado).toBe(false)
    expect(c.dentroDoRaio).toBe(1)
  })

  it('inclui quem tem o centróide dentro do raio, do mais próximo ao mais distante', () => {
    const c = conjuntoNoRaio('1000', fila(10), 25)!      // 0,1° ≈ 11,1 km; 0,2° ≈ 22,2 km; 0,3° ≈ 33,4 km
    expect(c.selecionados.map((v) => v.ibge)).toEqual(['1000', '1001', '1002'])
    expect(c.selecionados[2].km).toBeCloseTo(haversineKm([0, 0], [0.2, 0]), 5)
    expect(c.cortado).toBe(false)
    expect(c.raioEfetivoKm).toBe(25)
  })

  it('o teto corta os mais distantes, guarda os cortados e o raio efetivo é o do último que coube', () => {
    const c = conjuntoNoRaio('1000', fila(200, 0.03), 500)!
    expect(c.selecionados).toHaveLength(MAX_MUNICIPIOS_RAIO)
    expect(c.selecionados[0].ibge).toBe('1000')
    expect(c.cortado).toBe(true)
    expect(c.dentroDoRaio).toBe(c.selecionados.length + c.foraDoLimite.length)
    expect(c.raioEfetivoKm).toBeCloseTo(c.selecionados[MAX_MUNICIPIOS_RAIO - 1].km, 9)
    expect(c.raioEfetivoKm).toBeLessThan(500)
    expect(c.foraDoLimite.every((v) => v.km >= c.raioEfetivoKm)).toBe(true)
  })

  it('exatamente no teto não corta; empate de distância desempata pelo IBGE', () => {
    const exato = conjuntoNoRaio('1000', fila(MAX_MUNICIPIOS_RAIO, 0.03), 500)!
    expect(exato.cortado).toBe(false)
    expect(exato.selecionados).toHaveLength(MAX_MUNICIPIOS_RAIO)
    const par: Record<string, LonLat> = { '1': [0, 0], '3': [0.1, 0], '2': [-0.1, 0] }
    expect(conjuntoNoRaio('1', par, 50, 2)!.selecionados.map((v) => v.ibge)).toEqual(['1', '2'])
  })

  it('sem centróide do município central não há conjunto; raio fora da faixa é limitado', () => {
    expect(conjuntoNoRaio('9999', fila(3), 100)).toBeNull()
    expect(conjuntoNoRaio('1000', fila(3), -5)!.raioKm).toBe(0)
    expect(conjuntoNoRaio('1000', fila(3), 9999)!.raioKm).toBe(500)
  })
})

describe('circuloGeoJSON', () => {
  it('todos os pontos ficam à distância pedida do centro', () => {
    const centro: LonLat = [-46.6, -23.5]
    const anel = circuloGeoJSON(centro, 120).geometry.coordinates[0]
    expect(anel.length).toBeGreaterThan(60)
    for (const p of anel) expect(haversineKm(centro, p as LonLat)).toBeCloseTo(120, 1)
  })
})
