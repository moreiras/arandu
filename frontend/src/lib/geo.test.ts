// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { fmtKm, haversineKm, maisProximos, rotuloPix } from './geo'

describe('geo', () => {
  it('haversine: São Paulo–Rio ≈ 360 km; mesmo ponto = 0', () => {
    const sp: [number, number] = [-46.6333, -23.5505]
    const rj: [number, number] = [-43.1729, -22.9068]
    expect(haversineKm(sp, rj)).toBeGreaterThan(350)
    expect(haversineKm(sp, rj)).toBeLessThan(370)
    expect(haversineKm(sp, sp)).toBe(0)
  })

  it('maisProximos ordena por distância e respeita n; sem origem devolve vazio', () => {
    const origem: [number, number] = [-46.6, -23.5]
    const pts = [
      { codigo: 'rj', nome: 'RJ', lonlat: [-43.2, -22.9] as [number, number] },
      { codigo: 'sp', nome: 'SP', lonlat: [-46.63, -23.55] as [number, number] },
      { codigo: 'mao', nome: 'MAO', lonlat: [-60, -3.1] as [number, number] },
    ]
    expect(maisProximos(origem, pts, 2).map((p) => p.codigo)).toEqual(['sp', 'rj'])
    expect(maisProximos(null, pts, 2)).toEqual([])
    expect(maisProximos(origem, [], 1)).toEqual([])
  })

  it('fmtKm: uma casa abaixo de 10 km, inteiro acima; ausência vira traço', () => {
    expect(fmtKm(3.456)).toBe('3,5 km')
    expect(fmtKm(123.4)).toBe('123 km')
    expect(fmtKm(null)).toBe('—')
    expect(fmtKm(NaN)).toBe('—')
  })

  it('rotuloPix: tira os colchetes do cadastro e emenda o PTT; sem nome fica vazio', () => {
    expect(rotuloPix('[PIX BR.Digital]')).toBe('PIX BR.Digital, ')
    expect(rotuloPix('[PIX / Univates]')).toBe('PIX / Univates, ')
    expect(rotuloPix(null)).toBe('')
    expect(rotuloPix('  ')).toBe('')
  })
})
