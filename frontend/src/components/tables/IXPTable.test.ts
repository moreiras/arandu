// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { foraDoRouteServer } from './IXPTable'

describe('"Fora do route server" (IXPS-E3)', () => {
  it('é a diferença sobre os participantes, não sobre os diretos', () => {
    expect(foraDoRouteServer({ ixbr_members_count: 2723, asn_direct_union_count: 2251 })).toEqual({ n: 472, pct: (472 / 2723) * 100 })
    expect(foraDoRouteServer({ ixbr_members_count: 2723, asn_direct_union_count: 2251 })!.pct.toFixed(1)).toBe('17.3')
    expect(foraDoRouteServer({ ixbr_members_count: 4, asn_direct_union_count: 2 })).toEqual({ n: 2, pct: 50 })
  })

  it('bordas: sem contagem ou sem participantes não inventa número; nunca negativo', () => {
    expect(foraDoRouteServer({ ixbr_members_count: undefined, asn_direct_union_count: 3 })).toBeNull()
    expect(foraDoRouteServer({ ixbr_members_count: 0, asn_direct_union_count: 0 })).toBeNull()
    expect(foraDoRouteServer({ ixbr_members_count: 3, asn_direct_union_count: 5 })).toEqual({ n: 0, pct: 0 })
  })
})
