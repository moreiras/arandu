// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { resumirScm } from './scmSici'

const f = (p: Record<string, unknown>): GeoJSON.Feature => ({ type: 'Feature', properties: p, geometry: { type: 'Point', coordinates: [0, 0] } })
const fc = (...fs: GeoJSON.Feature[]): GeoJSON.FeatureCollection => ({ type: 'FeatureCollection', features: fs })

describe('resumirScm', () => {
  it('conta com e sem declaração e com ASN, por UF em ordem alfabética', () => {
    const r = resumirScm(fc(
      f({ uf: 'SP', sici_ativo: true, sici_mes_referencia: '2026-09', has_asn: true }),
      f({ uf: 'AC', sici_ativo: false, sici_mes_referencia: '2026-09', has_asn: false }),
      f({ uf: 'SP', sici_ativo: 'false', has_asn: true }),
      f({ uf: 'SP', sici_ativo: 'true', has_asn: false }),
    ))!
    expect([r.total, r.com, r.sem, r.semInformacao, r.comAsn, r.mes]).toEqual([4, 2, 2, 0, 2, '2026-09'])
    expect(r.porUf).toEqual([{ uf: 'AC', total: 1, com: 0, sem: 1, comAsn: 0 }, { uf: 'SP', total: 3, com: 2, sem: 1, comAsn: 2 }])
  })
  it('snapshot sem o campo não afirma nada sobre a declaração', () => {
    const r = resumirScm(fc(f({ uf: 'SP', has_asn: false })))!
    expect([r.com, r.sem, r.semInformacao]).toEqual([0, 0, 1])
  })
  it('sem feições, nada', () => {
    expect(resumirScm(fc())).toBeNull()
    expect(resumirScm(null)).toBeNull()
  })
})
