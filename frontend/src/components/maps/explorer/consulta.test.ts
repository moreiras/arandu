// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it } from 'vitest'
import { groupToDsl, hasRecorte, isComplete, layerBody, layerQuery, makeGroup, makePredicate, parseAsns, predicateToDsl, recorteBody } from './consulta'
import { INITIAL } from './tipos'
import type { FilterGroup, MapState, Predicate, PredicateKind } from './tipos'

const pred = (kind: PredicateKind, value = ''): Predicate => ({ id: 'x', kind, value })
const estado = (p: Partial<MapState>): MapState => ({ ...INITIAL, ...p })

describe('predicados → DSL do motor de consulta', () => {
  it('traduz cada tipo para campo/operador/valor', () => {
    expect(predicateToDsl(pred('is_br'))).toEqual({ field: 'is_br', op: 'eq', value: true })
    expect(predicateToDsl(pred('no_rpki'))).toEqual({ field: 'has_rpki', op: 'eq', value: false })
    expect(predicateToDsl(pred('has_aspa'))).toEqual({ field: 'has_aspa', op: 'eq', value: true })
    expect(predicateToDsl(pred('v6_ft'))).toEqual({ field: 'global_prefixes_v6_count', op: 'gte', value: 1 })
    expect(predicateToDsl(pred('ixps_direct_in', '  SP '))).toEqual({ field: 'ixps_direct', op: 'contains', value: 'sp' })
    expect(predicateToDsl(pred('ixps_origin_nin', 'RJ'))).toEqual({ field: 'ixps_origin', op: 'ncontains', value: 'rj' })
    expect(predicateToDsl(pred('pct_v6_gte', '25.5'))).toEqual({ field: 'pct_v6', op: 'gte', value: 25.5 })
    expect(predicateToDsl(pred('porte', 'DEMAIS'))).toEqual({ field: 'porte', op: 'eq', value: 'DEMAIS' })
    expect(predicateToDsl(pred('no_scm'))).toEqual({ field: 'has_scm', op: 'eq', value: false })
  })

  it('predicado que exige valor só vale preenchido', () => {
    expect(isComplete(pred('ixps_direct_in', ' '))).toBe(false)
    expect(isComplete(pred('ixps_direct_in', 'sp'))).toBe(true)
    expect(isComplete(pred('has_rpki'))).toBe(true)
  })

  it('grupo: vazio → null, um predicado → ele mesmo, vários → E/OU', () => {
    const g = (op: 'and' | 'or', ps: Predicate[]): FilterGroup => ({ id: 'g', op, predicates: ps })
    expect(groupToDsl(g('and', []))).toBeNull()
    expect(groupToDsl(g('and', [pred('ixps_direct_in', '')]))).toBeNull()                 // incompleto não conta
    expect(groupToDsl(g('or', [pred('is_br')]))).toEqual({ field: 'is_br', op: 'eq', value: true })
    expect(groupToDsl(g('or', [pred('is_br'), pred('has_rpki')]))).toEqual({
      or: [{ field: 'is_br', op: 'eq', value: true }, { field: 'has_rpki', op: 'eq', value: true }],
    })
  })
})

describe('recorte e corpo por camada', () => {
  it('sem filtro nem proximidade não há recorte', () => {
    expect(recorteBody(INITIAL)).toEqual({})
    expect(hasRecorte(INITIAL)).toBe(false)
  })

  it('um grupo vira o filtro; vários combinam pelo operador dos grupos', () => {
    const g1: FilterGroup = { id: '1', op: 'and', predicates: [pred('is_br')] }
    const g2: FilterGroup = { id: '2', op: 'and', predicates: [pred('has_rpki')] }
    expect(recorteBody(estado({ groups: [g1] })).filter).toEqual({ field: 'is_br', op: 'eq', value: true })
    expect(recorteBody(estado({ groups: [g1, g2], groupOp: 'or' })).filter).toEqual({
      or: [{ field: 'is_br', op: 'eq', value: true }, { field: 'has_rpki', op: 'eq', value: true }],
    })
    expect(hasRecorte(estado({ groups: [g1] }))).toBe(true)
  })

  it('proximidade por sede usa near; por prefixos usa near_prefixes; PTT em minúsculas', () => {
    expect(recorteBody(estado({ nearIxp: ' SP ', nearRadiusKm: 80 })).near).toEqual({ ixp: 'sp', radius_km: 80 })
    const b = recorteBody(estado({ nearIxp: 'RJ', nearMode: 'prefixos' }))
    expect(b.near).toBeUndefined()
    expect(b.near_prefixes).toEqual({ ixp: 'rj', radius_km: 150 })
  })

  it('camada sem recorte (PIX, rodovias) ignora filtro; sedes levam color_by; SCM leva scm_mode', () => {
    const g: FilterGroup = { id: '1', op: 'and', predicates: [pred('is_br')] }
    const s = estado({ groups: [g], colorBy: 'rpki', scmMode: 'sem_asn' })
    expect(layerBody('pix', s)).toEqual({ layers: ['pix'] })
    expect(layerBody('asns_geo', s)).toMatchObject({ layers: ['asns_geo'], color_by: 'rpki', filter: { field: 'is_br', op: 'eq', value: true } })
    expect(layerBody('outorgas_scm', s).scm_mode).toBe('sem_asn')
  })

  it('camadas de prefixos do PTT levam ix_code e a lista de ASNs a excluir/incluir', () => {
    const b = layerBody('prefixos_ix_v4', estado({ ixCode: ' SP ', ixExcludeAsns: '6939, abc, 0, 15169', ixIncludeAsns: '' }))
    expect(b).toMatchObject({ ix_code: 'sp', ix_apply_filter: true, ix_exclude_asns: [6939, 15169] })
    expect(b.ix_include_asns).toBeUndefined()
    expect(parseAsns('1,x, -3 , 20')).toEqual([1, 20])
  })

  it('rodovias usam a rota GET filtrada no servidor, com a chave pela URL', () => {
    const q = layerQuery('roads_federal', estado({ roadsFederalPaved: true }), '2026-10-24')
    expect(q.key).toEqual(['map-layer', 'roads_federal', '/api/v1/map/rodovias?jurisdicao=Federal&pavimentada=true&date=2026-10-24'])
    const e = layerQuery('roads_estadual', INITIAL)
    expect(e.key[2]).toBe('/api/v1/map/rodovias?jurisdicao=Estadual%2FDistrital')
  })

  it('antenas do SMP usam a rota GET da grade, com a geração e a data na chave', () => {
    expect(layerQuery('erbs', INITIAL).key).toEqual(['map-layer', 'erbs', '/api/v1/map/erbs'])
    expect(layerQuery('erbs', estado({ erbsGeracao: '5G' }), '2026-11-01').key[2]).toBe('/api/v1/map/erbs?geracao=5G&date=2026-11-01')
  })

  it('a chave das demais camadas inclui a data e o corpo (mudar o filtro refaz a consulta)', () => {
    const a = layerQuery('asns_geo', INITIAL, '2026-10-24').key
    const b = layerQuery('asns_geo', estado({ colorBy: 'porte' }), '2026-10-24').key
    expect(a).not.toEqual(b)
    expect(a.slice(0, 3)).toEqual(['map-layer', 'asns_geo', '2026-10-24'])
  })

  it('ids de grupo e de predicado são únicos', () => {
    const ids = new Set([makeGroup().id, makeGroup().id, makePredicate().id, makePredicate('porte').id])
    expect(ids.size).toBe(4)
    expect(makePredicate('porte')).toMatchObject({ kind: 'porte', value: '' })
  })
})
