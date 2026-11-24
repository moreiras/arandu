// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import {
  agruparPorCoordenada, contagemEntidades, contagensIx, etiquetasIx, filtrarNoRaio, indicesScm, mapaDeNomes, montarEntidades,
  municipiosSiciNoRaio, operadoresSici, pixNoRaio, resumoDoRaio, scmsNoRaio,
} from './calculos'
import type { Ponto } from './calculos'
import { montarCsv } from './csv'
import { circlePolygon, distKm, nearestIxCode } from './geo'
import type { AsnFeature, PixFeature, PrefixFeature, ScmGeoFeature } from './tipos'
import { formatCnpj, parseAsns, prefixColor, V4_STRONG, V4_WEAK, V6_STRONG, V6_WEAK } from './tipos'

const SP: Ponto = [-23.55, -46.63]
const CNPJ_A = '12345678000190'
const CNPJ_B = '98765432000110'

const asn = (n: number, lat: number, lon: number, extra: Record<string, unknown> = {}): AsnFeature =>
  ({ geometry: { coordinates: [lon, lat] }, properties: { asn: n, name: `AS ${n}`, city: 'Cidade', uf: 'SP', ...extra } as AsnFeature['properties'] })
const prefixo = (origem: number, lat: number, lon: number, v6 = false, n = 1): PrefixFeature =>
  ({ geometry: { coordinates: [lon, lat] }, properties: { prefix_count: n, ip_version: v6 ? 6 : 4, origin_asn: origem, city: 'Cidade', uf: 'SP' } })
const scm = (cnpj: string, lat: number, lon: number, asns: number[] | string, nome = `Prov ${cnpj}`): ScmGeoFeature =>
  ({ geometry: { coordinates: [lon, lat] }, properties: { cnpj, razao_social: nome, municipio: 'Cidade', uf: 'SP', has_asn: parseAsns(asns).length > 0, asns } })

const asnGeo = { features: [
  asn(1, -23.55, -46.63, { cnpj: CNPJ_A }),         // no centro
  asn(2, -22.9, -47.06, { cnpj: CNPJ_A }),          // Campinas, ~85 km, mesmo CNPJ do 1
  asn(3, -3.1, -60.0),                              // Manaus, longe
  asn(4, -23.6, -46.7),                             // ~9 km, sem CNPJ
] }
const prefixGeo = { features: [
  prefixo(1, -23.55, -46.63, false, 1), prefixo(1, -23.55, -46.63, false, 1),       // duas feições no mesmo ponto: somam
  prefixo(9, -23.5, -46.6, true),  // AS 9 sem sede na região
  prefixo(3, -3.1, -60.0), prefixo(7, -23.5, -46.6),
  { geometry: { coordinates: [-46.6, -23.5] }, properties: { prefix_count: 1, ip_version: 4, city: 'Cidade' } } as PrefixFeature, // sem origem: ignorado
] }

describe('geografia', () => {
  it('distância de grande círculo e IX mais próximo', () => {
    expect(distKm(0, 0, 0, 0)).toBe(0)
    expect(distKm(-23.55, -46.63, -22.9, -47.06)).toBeGreaterThan(80)
    expect(distKm(-23.55, -46.63, -22.9, -47.06)).toBeLessThan(95)
    expect(nearestIxCode(-23.55, -46.63)).toBe('sp')
    expect(nearestIxCode(-3.7, -38.5)).toBe('ce')
  })

  it('círculo do raio: anel fechado, cada vértice a ~raio do centro', () => {
    const c = circlePolygon(-23.55, -46.63, 50, 36)
    const anel = c.geometry.coordinates[0]
    expect(anel).toHaveLength(37)
    expect(anel[0][0]).toBeCloseTo(anel[36][0], 9)
    for (const [lon, lat] of anel) expect(distKm(-23.55, -46.63, lat, lon)).toBeCloseTo(50, 0)
  })

  it('utilidades de formatação', () => {
    expect(formatCnpj('12345678000190')).toBe('12.345.678/0001-90')
    expect(formatCnpj('1')).toBe('1')
    expect(parseAsns('[1,2]')).toEqual([1, 2])
    expect(parseAsns([3])).toEqual([3])
    expect(parseAsns(undefined as never)).toEqual([])
    expect(prefixColor(6, true)).toBe(V6_STRONG)
    expect(prefixColor(6, false)).toBe(V6_WEAK)
    expect(prefixColor(4, true)).toBe(V4_STRONG)
    expect(prefixColor(4, false)).toBe(V4_WEAK)
  })
})

describe('o que está no raio', () => {
  const nomes = mapaDeNomes(asnGeo)

  it('sem ponto de referência não há nada', () => {
    expect(filtrarNoRaio({ markerPos: null, radius: 100, showAsns: true, showPrefixes: true, asnGeo, prefixGeo, asnNameMap: nomes }))
      .toEqual({ filteredAsns: [], asnDots: [], prefixBubbles: [] })
  })

  it('sedes dentro do raio, ordenadas por ASN; o raio manda', () => {
    const a = filtrarNoRaio({ markerPos: SP, radius: 100, showAsns: true, showPrefixes: false, asnGeo, prefixGeo, asnNameMap: nomes })
    expect(a.filteredAsns.map(x => x.asn)).toEqual([1, 2, 4])
    expect(a.asnDots.map(d => d.asn)).toEqual([1, 2, 4])
    expect(a.filteredAsns.every(x => x.fromHq && !x.v4 && !x.v6)).toBe(true)
    const b = filtrarNoRaio({ markerPos: SP, radius: 20, showAsns: true, showPrefixes: false, asnGeo, prefixGeo, asnNameMap: nomes })
    expect(b.filteredAsns.map(x => x.asn)).toEqual([1, 4])
    const c = filtrarNoRaio({ markerPos: SP, radius: 100, showAsns: false, showPrefixes: false, asnGeo, prefixGeo, asnNameMap: nomes })
    expect(c.filteredAsns).toEqual([])                                   // camada desligada: lista vazia, mas as sedes seguem para o mapa
    expect(c.asnDots).toHaveLength(3)
  })

  it('bolhas de prefixos: uma por AS+família+local; "próprio" só com sede na região; ASes só com prefixo entram na lista', () => {
    const r = filtrarNoRaio({ markerPos: SP, radius: 100, showAsns: true, showPrefixes: true, asnGeo, prefixGeo, asnNameMap: nomes })
    const b1 = r.prefixBubbles.find(b => b.asn === 1)!
    expect(b1).toMatchObject({ count: 2, afi: 4, own: true })
    expect(r.prefixBubbles.find(b => b.asn === 9)).toMatchObject({ afi: 6, own: false, count: 1 })
    expect(r.prefixBubbles.find(b => b.asn === 3)).toBeUndefined()      // longe
    expect(r.prefixBubbles.every(b => b.asn)).toBe(true)                // prefixo sem origem não vira bolha
    // externos primeiro (desenhados embaixo), próprios por cima
    expect(r.prefixBubbles.map(b => b.own)).toEqual([...r.prefixBubbles.map(b => b.own)].sort((x, y) => Number(x) - Number(y)))
    const lista = Object.fromEntries(r.filteredAsns.map(a => [a.asn, a]))
    expect(lista[1]).toMatchObject({ fromHq: true, v4: true, v6: false })
    expect(lista[9]).toMatchObject({ fromHq: false, v4: false, v6: true })
    expect(lista[7]).toMatchObject({ fromHq: false, v4: true })
    // só prefixo (sem sedes): AS 1 continua na lista pelo prefixo, mas não como sede
    const so = filtrarNoRaio({ markerPos: SP, radius: 100, showAsns: false, showPrefixes: true, asnGeo, prefixGeo, asnNameMap: nomes })
    expect(so.filteredAsns.find(a => a.asn === 1)).toMatchObject({ fromHq: false, v4: true })
    expect(so.filteredAsns.find(a => a.asn === 4)).toBeUndefined()
  })

  it('PIX e SCMs no raio', () => {
    const pixGeo = { features: [
      { geometry: { coordinates: [-46.63, -23.55] }, properties: { name: 'PIX A', ixp_name: 'São Paulo' } },
      { geometry: { coordinates: [-60, -3.1] }, properties: { name: 'PIX B' } },
    ] as PixFeature[] }
    expect(pixNoRaio(SP, 50, pixGeo)).toEqual([{ lat: -23.55, lon: -46.63, name: 'PIX A', ixpName: 'São Paulo' }])
    expect(pixNoRaio(null, 50, pixGeo)).toEqual([])
    const scmGeo = { features: [scm(CNPJ_A, -23.55, -46.63, [1, 2]), scm(CNPJ_B, -3.1, -60, [])] }
    expect(scmsNoRaio(SP, 50, scmGeo).map(f => f.properties.cnpj)).toEqual([CNPJ_A])
    expect(scmsNoRaio(null, 50, scmGeo)).toEqual([])
  })

  it('SICI: municípios pelo centróide e um item por CNPJ somando acessos', () => {
    const siciMun = { snapshot_date: 'x', municipios: {
      '1': { nome: 'Perto', uf: 'SP', acessos: 300, operadores: [{ cnpj: CNPJ_A, empresa: 'A', acessos: 200 }, { cnpj: CNPJ_B, empresa: 'B', acessos: 100 }] },
      '2': { nome: 'Também', uf: 'SP', acessos: 50, operadores: [{ cnpj: CNPJ_A, empresa: 'A', acessos: 50 }] },
      '3': { nome: 'Longe', uf: 'AM', acessos: 9, operadores: [{ cnpj: CNPJ_B, empresa: 'B', acessos: 9 }] },
      '4': { nome: 'Sem centróide', uf: 'SP', acessos: 1, operadores: [] },
    } } as never
    const centroides: Record<string, [number, number]> = { '1': [-46.7, -23.5], '2': [-46.5, -23.6], '3': [-60, -3.1] }
    const m = municipiosSiciNoRaio(SP, 50, siciMun, centroides)
    expect(m.map(x => x.ibge)).toEqual(['1', '2'])
    expect(municipiosSiciNoRaio(null, 50, siciMun, centroides)).toEqual([])
    expect(municipiosSiciNoRaio(SP, 50, siciMun, undefined)).toEqual([])
    expect(operadoresSici(m)).toEqual([
      { cnpj: CNPJ_A, empresa: 'A', acessos: 250, municipios: 2 },     // ordenado por acessos
      { cnpj: CNPJ_B, empresa: 'B', acessos: 100, municipios: 1 },
    ])
  })
})

describe('lista de entidades', () => {
  const nomes = mapaDeNomes(asnGeo)
  const scmGeo = { features: [scm(CNPJ_A, -23.55, -46.63, [1, 2], 'Provedor A'), scm(CNPJ_B, -23.5, -46.6, [], 'Provedor B')] }
  const idx = indicesScm(scmGeo, asnGeo)

  it('índices CNPJ ↔ ASN usam todas as features e juntam o cadastro dos ASes com as outorgas', () => {
    expect(idx.asnToCnpj.get(1)).toBe(CNPJ_A)
    expect(idx.cnpjToAsns.get(CNPJ_A)).toEqual([1, 2])
    expect(idx.cnpjToAsns.has(CNPJ_B)).toBe(false)                       // sem ASN
    expect(idx.scmCnpjs).toEqual(new Set([CNPJ_A, CNPJ_B]))
    expect([...idx.cnpjAllAsns.get(CNPJ_A)!].sort()).toEqual([1, 2])
  })

  it('um CNPJ com vários ASNs vira uma só entidade (ASes primeiro, depois só-SCM)', () => {
    const r = filtrarNoRaio({ markerPos: SP, radius: 100, showAsns: true, showPrefixes: false, asnGeo, prefixGeo, asnNameMap: nomes })
    const sc = scmsNoRaio(SP, 100, scmGeo)
    const e = montarEntidades({ filteredAsns: r.filteredAsns, scmsInRadius: sc, asnToCnpj: idx.asnToCnpj, cnpjAllAsns: idx.cnpjAllAsns, scmCnpjs: idx.scmCnpjs,
      asnNameMap: nomes, showScms: true, showSici: false, siciOperadores: [] })
    expect(e.map(x => x.key)).toEqual([`cnpj:${CNPJ_A}`, 'asn:4', `cnpj:${CNPJ_B}`])
    expect(e[0]).toMatchObject({ asns: [1, 2], scm: true, scmHq: true, fromHq: true })
    expect(e[1]).toMatchObject({ asns: [4], scm: false, cnpj: undefined })
    expect(e[2]).toMatchObject({ asns: [], scm: true, scmHq: true, name: 'Provedor B' })
    expect(contagemEntidades(e)).toEqual({ asns: 3, cnpjsComAsn: 2, scms: 2 })     // ASNs no raio (1, 2, 4), não entidades (LOC-E3)
    // sem a camada SCM a outorga sem ASN não aparece, mas o AS ainda sabe que tem outorga
    const sem = montarEntidades({ filteredAsns: r.filteredAsns, scmsInRadius: sc, asnToCnpj: idx.asnToCnpj, cnpjAllAsns: idx.cnpjAllAsns, scmCnpjs: idx.scmCnpjs,
      asnNameMap: nomes, showScms: false, showSici: false, siciOperadores: [] })
    expect(sem.map(x => x.key)).toEqual([`cnpj:${CNPJ_A}`, 'asn:4'])
    expect(sem[0]).toMatchObject({ scm: true, scmHq: false })
  })

  it('ASN do mesmo CNPJ fora do raio não conta, não vira etiqueta nem entra no CSV (LOC-E3)', () => {
    const r = filtrarNoRaio({ markerPos: SP, radius: 50, showAsns: true, showPrefixes: false, asnGeo, prefixGeo, asnNameMap: nomes })
    const e = montarEntidades({ filteredAsns: r.filteredAsns, scmsInRadius: [], asnToCnpj: idx.asnToCnpj, cnpjAllAsns: idx.cnpjAllAsns, scmCnpjs: idx.scmCnpjs,
      asnNameMap: nomes, showScms: false, showSici: false, siciOperadores: [] })
    expect(e[0]).toMatchObject({ key: `cnpj:${CNPJ_A}`, asns: [1, 2], asnsNoRaio: [1] })      // AS2 (Campinas, ~85 km) fora do raio de 50 km
    expect(contagemEntidades(e)).toEqual({ asns: 2, cnpjsComAsn: 2, scms: 1 })
    const ixOf = (a: number) => ({ m: a === 2 ? ['rj'] : ['sp'], o: [] as string[] })
    const linha = montarCsv(e, ixOf as never, null, (c) => c).split('\n')[1]
    expect(linha.startsWith('1,')).toBe(true)                        // só o AS1 na coluna de ASNs
    expect(linha).not.toMatch(/rj/)                                  // a presença do AS2 (fora do raio) não entra
  })

  it('SICI acrescenta operadores com acessos e marca como SCM', () => {
    const e = montarEntidades({ filteredAsns: [], scmsInRadius: [], asnToCnpj: idx.asnToCnpj, cnpjAllAsns: idx.cnpjAllAsns, scmCnpjs: idx.scmCnpjs,
      asnNameMap: nomes, showScms: false, showSici: true, siciOperadores: [{ cnpj: CNPJ_B, empresa: 'B', acessos: 77, municipios: 3 }, { cnpj: '1', empresa: 'Outra', acessos: 5, municipios: 1 }] })
    expect(e[0]).toMatchObject({ cnpj: CNPJ_B, scm: true, sici: { acessos: 77, municipios: 3 } })
    expect(e[1]).toMatchObject({ cnpj: '1', scm: true })
  })

  it('agrupa por coordenada exata e conta o resumo do raio', () => {
    const r = filtrarNoRaio({ markerPos: SP, radius: 100, showAsns: true, showPrefixes: false, asnGeo, prefixGeo, asnNameMap: nomes })
    const sc = scmsNoRaio(SP, 100, scmGeo)
    const g = agruparPorCoordenada({ asnDots: r.asnDots, scmsInRadius: sc, showAsns: true, showScms: true, markerPos: SP })
    expect(g.get('-46.63,-23.55')).toMatchObject({ asns: [expect.objectContaining({ asn: 1 })], scms: [expect.objectContaining({ properties: expect.objectContaining({ cnpj: CNPJ_A }) })] })
    expect(g.size).toBe(4)
    expect(agruparPorCoordenada({ asnDots: r.asnDots, scmsInRadius: sc, showAsns: false, showScms: false, markerPos: SP }).size).toBe(0)
    expect(resumoDoRaio({ filteredAsns: r.filteredAsns, scmsInRadius: sc, siciOperadores: [], showScms: true, showSici: true }))
      .toEqual({ sedesAsn: 3, asnsComPrefixo: 0, sedesScm: 2, scmsComUsuarios: 0 })
    expect(resumoDoRaio({ filteredAsns: r.filteredAsns, scmsInRadius: sc, siciOperadores: [], showScms: false, showSici: false }).sedesScm).toBe(0)
  })
})

describe('participação em IXes', () => {
  const rotulo = (c: string) => `IX ${c.toUpperCase()}`

  it('etiquetas: mais próximo, principais, "algum outro" ou "nenhum"', () => {
    expect(etiquetasIx([], 'sp', rotulo)).toEqual([{ code: '', label: 'Nenhum IX', kind: 'none' }])
    expect(etiquetasIx(['sp', 'rj', 'ce'], 'sp', rotulo)).toEqual([
      { code: 'sp', label: 'IX SP', kind: 'near' }, { code: 'ce', label: 'IX CE', kind: 'major' }, { code: 'rj', label: 'IX RJ', kind: 'major' },
    ])
    expect(etiquetasIx(['mg'], 'sp', rotulo)).toEqual([{ code: '', label: 'Algum IX do IX.br', kind: 'other' }])
    expect(etiquetasIx(['rs'], null, rotulo).map(t => t.kind)).toEqual(['major'])
  })

  it('contagens sobre a lista atual', () => {
    const lista = [1, 2, 3, 4].map(a => ({ asn: a, name: '', fromHq: true, v4: false, v6: false }))
    const pres: Record<number, { m: string[]; o: string[] }> = { 1: { m: ['sp'], o: ['sp'] }, 2: { m: ['rj'], o: [] }, 3: { m: [], o: ['sp'] }, 4: { m: ['sp', 'rj'], o: [] } }
    expect(contagensIx(lista, a => pres[a], 'sp')).toEqual({ nearMember: 2, nearOrigin: 2, anyMember: 3, otherNotNear: 1 })
    expect(contagensIx(lista, a => pres[a], null)).toEqual({ nearMember: 0, nearOrigin: 0, anyMember: 3, otherNotNear: 0 })
  })
})

describe('CSV da lista', () => {
  it('uma linha por entidade, com sim/não e participação em IXes; vírgula e aspas escapadas', () => {
    const entities = [
      { key: 'a', cnpj: CNPJ_A, asns: [1, 2], asnsNoRaio: [1, 2], name: 'Prov, "A"', city: 'Cidade', uf: 'SP', fromHq: true, v4: true, v6: false, scm: true, scmHq: false },
      { key: 'b', cnpj: CNPJ_B, asns: [], asnsNoRaio: [], name: 'Só SCM', fromHq: false, v4: false, v6: false, scm: true, scmHq: true, sici: { acessos: 50, municipios: 2 } },
    ]
    const pres: Record<number, { m: string[]; o: string[] }> = { 1: { m: ['sp', 'mg'], o: ['sp'] }, 2: { m: ['sp'], o: [] } }
    const csv = montarCsv(entities, a => pres[a] ?? { m: [], o: [] }, 'sp', c => `IX ${c}`)
    const linhas = csv.replace('﻿', '').split('\n')
    expect(linhas).toHaveLength(3)
    expect(linhas[0].startsWith('asns,cnpj,nome,')).toBe(true)
    expect(linhas[1]).toBe(`1 2,${CNPJ_A},"Prov, ""A""",SP,Cidade,sim,sim,sim,não,sim,não,,,IX sp,sim,sim,não,não,não,não,sim,sp mg,sp`)
    expect(linhas[2]).toBe(`,${CNPJ_B},Só SCM,,,não,sim,não,sim,não,não,50,2,,,,,,,,,,`)
  })
})
