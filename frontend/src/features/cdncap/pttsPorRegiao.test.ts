// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** "Por PTT" agrupado por região e UF (PT-22 / cdns 5.2): contas das linhas de presença, ordem fixa, UF sem provedor do catálogo, PTT sem UF. */
import { describe, expect, it } from 'vitest'
import { pttsPorRegiao } from './pttsPorRegiao'

const d = {
  snapshot_date: '2026-11-22',
  ixbr_columns: [{ code: 'ce', name: 'Fortaleza', cdn_count: 2 }, { code: 'se', name: 'Aracaju', cdn_count: 0 }, { code: 'sp', name: 'Sao Paulo', cdn_count: 2 }, { code: 'ro', name: 'Porto Velho', cdn_count: 0 }, { code: 'zz', name: 'Novo', cdn_count: 0 }],
  external_columns: [],
  cdns: [
    { name: 'A', asns: [], ixbr: ['ce', 'sp'], external: [], ixbr_count: 2, external_count: 0, ixbr_rs: ['ce', 'sp'], ixbr_origem: ['se'] },
    { name: 'B', asns: [], ixbr: ['ce', 'sp'], external: [], ixbr_count: 2, external_count: 0, ixbr_rs: ['sp'], ixbr_origem: ['se', 'ro'] },
  ],
} as never
const ixps = [
  { code: 'ce', name: 'Fortaleza', uf: 'CE', ixbr_members_count: 900 }, { code: 'se', name: 'Aracaju', uf: 'SE', ixbr_members_count: 59 },
  { code: 'sp', name: 'São Paulo', uf: 'SP', ixbr_members_count: 2400 }, { code: 'ro', name: 'Porto Velho', uf: 'RO', ixbr_members_count: 27 },
] as never

describe('pttsPorRegiao', () => {
  it('agrupa pela região do IBGE na ordem N, NE, CO, SE, S, com UF e participantes da lista de PTTs', () => {
    const g = pttsPorRegiao(d, ixps)
    expect(g.map((x) => x.id)).toEqual(['N', 'NE', 'SE', 'sem-uf'])
    expect(g[1].ptts.map((p) => p.code)).toEqual(['ce', 'se'])
    expect(g[1].ptts[0]).toMatchObject({ uf: 'CE', membros: 900, cdnsMembro: 2, comRouteServer: 1, soViaOutroAs: 0 })
    expect(g[1].ptts[1]).toMatchObject({ uf: 'SE', membros: 59, cdnsMembro: 0, comRouteServer: 0, soViaOutroAs: 2 })
  })

  it('UFs sem provedor do catálogo em PTT local ficam no subtotal da região', () => {
    const g = pttsPorRegiao(d, ixps)
    expect(g[0].ufsSemCdn).toEqual(['RO'])
    expect(g[1].ufsSemCdn).toEqual(['SE'])
    expect(g[2].ufsSemCdn).toEqual([])
  })

  it('PTT fora da lista de PTTs vai para "UF não informada" e sem a lista a página não quebra', () => {
    const g = pttsPorRegiao(d, ixps)
    expect(g[3]).toMatchObject({ nome: 'UF não informada', ufsSemCdn: [] })
    expect(g[3].ptts[0]).toMatchObject({ code: 'zz', uf: null, membros: null })
    expect(pttsPorRegiao(d, undefined).map((x) => x.id)).toEqual(['sem-uf'])
    expect(pttsPorRegiao(null, ixps)).toEqual([])
  })

  it('a soma dos provedores membro por PTT confere com as linhas do catálogo', () => {
    const total = pttsPorRegiao(d, ixps).flatMap((x) => x.ptts).reduce((t, p) => t + p.cdnsMembro, 0)
    expect(total).toBe(4)
  })
})
