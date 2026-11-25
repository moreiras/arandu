// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Síntese de CDNs (PT-22, cdns 5.2): catálogo incompleto dito na frase, sem recomendação, e os números batem com as colunas e linhas da matriz. */
import { describe, expect, it } from 'vitest'
import { PALAVRAS_PROIBIDAS } from '../../lib/sintese'
import { sinteseCdns } from './sinteseCdns'

const cdn = (ixbr: number, ext: number) => ({ name: 'x', asns: [], ixbr: [], external: [], ixbr_count: ixbr, external_count: ext })
const dados = (over: object = {}) => ({
  snapshot_date: '2026-11-22',
  cdns: [cdn(3, 0), cdn(0, 2), cdn(1, 1), cdn(0, 0)],
  ixbr_columns: [{ code: 'sp', name: 'SP', cdn_count: 2 }, { code: 'ac', name: 'AC', cdn_count: 0 }, { code: 'ap', name: 'AP', cdn_count: 0 }],
  external_columns: [{ code: 'e1', name: 'E1', cdn_count: 2 }, { code: 'e2', name: 'E2', cdn_count: 1 }],
  ...over,
}) as never

describe('sinteseCdns', () => {
  it('três frases: catálogo no IX.br, PTTs sem provedor do catálogo e IXPs de fora', () => {
    const f = sinteseCdns(dados())
    expect(f.map((x) => x.id)).toEqual(['catalogo', 'ptts-sem', 'fora'])
    expect(f[0].texto).toBe('O catálogo acompanha 4 provedores de CDN e de conteúdo; 2 constam do cadastro de participantes de ao menos um PTT do IX.br.')
    expect(f[1].texto).toContain('2 dos 3 PTTs do IX.br não têm nenhum provedor do catálogo')
    expect(f[1].texto).toContain('o catálogo é incompleto')
    expect(f[2].texto).toBe('Fora do IX.br, 2 provedores do catálogo declaram presença em 2 IXPs do PeeringDB.')
    expect(f[2].selo).toBe('fato')
    expect(f[0].selo).toBe('inferido')
    for (const x of f) { expect(x.dataRef).toBe('2026-11-22'); expect(x.fonte).not.toBe(''); expect(x.texto).not.toMatch(PALAVRAS_PROIBIDAS); expect(x.texto).not.toMatch(/instal|recomend|deveria/i) }
  })

  it('todos os PTTs com provedor: frase própria, sem "0"', () => {
    const f = sinteseCdns(dados({ ixbr_columns: [{ code: 'sp', name: 'SP', cdn_count: 2 }, { code: 'rj', name: 'RJ', cdn_count: 1 }] }))
    expect(f.find((x) => x.id === 'ptts-sem')!.texto).toBe('Todos os 2 PTTs do IX.br têm ao menos um provedor do catálogo no cadastro.')
    expect(sinteseCdns(dados({ ixbr_columns: [{ code: 'sp', name: 'SP', cdn_count: 2 }] })).find((x) => x.id === 'ptts-sem')!.texto).toMatch(/^O PTT do IX\.br tem/)
  })

  it('sem dados ou catálogo vazio a síntese some; sem IXPs de fora só restam duas frases', () => {
    expect(sinteseCdns(null)).toEqual([])
    expect(sinteseCdns(dados({ cdns: [] }))).toEqual([])
    expect(sinteseCdns(dados({ external_columns: [] })).map((x) => x.id)).toEqual(['catalogo', 'ptts-sem'])
  })
})
