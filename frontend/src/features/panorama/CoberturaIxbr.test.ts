// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { textosAsnPtt } from './CoberturaIxbr'
import type { IXPIndexEntry } from '../../types/api'

const bases = { totalBrASNs: 9129, brAsnsInFt: 8732, totalGlobalASNs: 88866 }
const sp = { code: 'sp', name: 'São Paulo', uf: 'SP', status: 'ok', asn_direct_union_count: 2251, br_asns_direct_union_count: 2091,
  asn_origin_union_count: 28795, br_asns_origin_union_count: 7000, v4: { status: 'missing' }, v6: { status: 'missing' } } as IXPIndexEntry
const pcts = (linhas: string[]) => linhas.join(' ').match(/[\d.,]+%/g)!.map((x) => Number(x.replace('%', '')))

describe('balões de ASNs por PTT (IXPS-E2, PANT-E1)', () => {
  it('originadores de todos os países vão sobre a tabela global; os brasileiros sobre a base brasileira', () => {
    const t = textosAsnPtt('origem', sp, 28795, bases)
    expect(t.join(' ')).toContain('dos quais 7.000 brasileiros')
    expect(t.join(' ')).toContain('32.4% dos 88.866 ASNs da tabela global')
    expect(t.join(' ')).not.toMatch(/315/)
    expect(Math.max(...pcts(t))).toBeLessThanOrEqual(100)
  })

  it('diretos: total com estrangeiros sem percentual sobre base brasileira; os brasileiros sobre os brasileiros', () => {
    const t = textosAsnPtt('direto', sp, 2251, bases)
    expect(t[0]).toBe('2.251 ASNs com sessão em route server do IX.br São Paulo, SP, dos quais 2.091 brasileiros.')
    expect(t[1]).toContain('22.9% dos 9.129 ASNs brasileiros (LACNIC)')
    expect(Math.max(...pcts(t))).toBeLessThanOrEqual(100)
  })

  it('borda: sem a contagem brasileira não inventa a linha', () => {
    const t = textosAsnPtt('direto', { ...sp, br_asns_direct_union_count: undefined }, 10, bases)
    expect(t).toEqual(['10 ASNs com sessão em route server do IX.br São Paulo, SP.'])
  })
})
