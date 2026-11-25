// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Síntese da lista de PTTs (PT-22, ixps 5.5): IX.br e externos em frases separadas, nunca somados; ausência não vira zero. */
import { describe, expect, it } from 'vitest'
import { PALAVRAS_PROIBIDAS } from '../../lib/sintese'
import { sinteseListaPtts } from './sinteseListaPtts'

const ixps = new Array(40).fill({ code: 'x' }) as never[]
const externos = [...new Array(45).fill({ br_member_count: 3 }), ...new Array(11).fill({ br_member_count: 0 })] as never[]
const summary = { snapshot_date: '2026-11-22', ixp_aggregate: { asn_direct_union_count: 3134 }, ixp_estimated_users_v4: 61900000, br_apnic_users_total: 161300000, external_ixps_br_asn_union_count: 179 } as never

describe('sinteseListaPtts', () => {
  it('três frases com os números dos KPIs: IX.br, usuários estimados e IXPs de fora, sem somar os dois universos', () => {
    const f = sinteseListaPtts(ixps, externos, summary, '2026-11-22')
    expect(f.map((x) => x.id)).toEqual(['sessoes', 'usuarios', 'externos'])
    expect(f[0].texto).toContain('3.134 ASNs distintos')
    expect(f[0].texto).toContain('dos 40 PTTs do IX.br')
    expect(f[1].selo).toBe('estimado')
    expect(f[1].texto).toContain('61,9 mi dos 161,3 mi')
    expect(f[2].texto).toBe('Fora do IX.br, 179 ASNs brasileiros declaram presença em 45 dos 56 IXPs do PeeringDB.')
    expect(f[2].fonte).toMatch(/autodeclarado/)
    expect(f.some((x) => /\b96\b|\b85\b/.test(x.texto))).toBe(false)
    for (const x of f) { expect(x.dataRef).toBe('2026-11-22'); expect(x.texto).not.toMatch(PALAVRAS_PROIBIDAS) }
  })

  it('snapshot sem summary mostra só o que existe; sem nada a síntese some', () => {
    expect(sinteseListaPtts(ixps, externos, { ...(summary as object), ixp_estimated_users_v4: undefined } as never, '2026-11-22').map((x) => x.id)).toEqual(['sessoes', 'externos'])
    expect(sinteseListaPtts([], [], null, null)).toEqual([])
    expect(sinteseListaPtts(ixps, [], { snapshot_date: 'x' } as never, null)).toEqual([])
  })
})
