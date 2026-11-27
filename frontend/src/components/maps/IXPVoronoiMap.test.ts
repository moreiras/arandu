// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { buildStats } from './IXPVoronoiMap'
import { comGeometria } from '../../lib/geo'
import type { IXPIndexEntry } from '../../types/api'

const SP = { code: 'sp', name: 'IX.br São Paulo', uf: 'SP', status: 'ok' as const } as unknown as IXPIndexEntry
const ponto = (lon: number, lat: number) => ({ type: 'Point', coordinates: [lon, lat] as [number, number] })

describe('buildStats com geometria nula', () => {
  it('ignora feição de AS e de prefixo sem geometria (regra de pessoa natural, RFC 7946 seção 3.2)', () => {
    const asnGeo = {
      features: [
        { geometry: ponto(-46.63, -23.55), properties: { asn: 64496 } },
        { geometry: null, properties: { asn: 64497 } },
      ],
    }
    const prefixGeo = {
      features: [
        { geometry: ponto(-46.63, -23.55), properties: { origin_asn: 64498 } },
        { geometry: null, properties: { origin_asn: 64499 } },
      ],
    }
    let stats: ReturnType<typeof buildStats> = {}
    expect(() => { stats = buildStats([SP], asnGeo, prefixGeo, undefined, {}) }).not.toThrow()
    expect(stats.sp.hqN).toBe(1)
    expect(stats.sp.opN).toBe(2)
  })

  it('ignora geometria que não é Point', () => {
    const asnGeo = { features: [{ geometry: { type: 'Polygon', coordinates: [0, 0] as [number, number] }, properties: { asn: 64500 } }] }
    expect(buildStats([SP], asnGeo, undefined, undefined, {}).sp.hqN).toBe(0)
  })
})

describe('comGeometria', () => {
  it('descarta feições com geometria nula e mantém as demais', () => {
    const fs = [{ geometry: ponto(1, 2) }, { geometry: null }, { geometry: ponto(3, 4) }]
    expect(comGeometria(fs)).toHaveLength(2)
  })
})
