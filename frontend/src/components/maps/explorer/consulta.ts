// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Estado do mapa → corpo das consultas por camada (lógica pura, sem React nem MapLibre; testada em consulta.test.ts). */
import type { QueryKey } from '@tanstack/react-query'
import { fetchMapQuery } from '../../../services/api'
import type { MapQueryBody, MapQueryResponse } from '../../../services/api'
import { LAYER_BY_ID, PTT_LAYERS } from './tipos'
import type { DataLayerId, FilterGroup, MapState, Predicate, PredicateKind } from './tipos'

export const NEEDS_VALUE = new Set<PredicateKind>([
  'ixps_direct_in', 'ixps_direct_nin', 'ixps_origin_in', 'ixps_origin_nin',
  'pct_v6_gte', 'porte',
])

export function isComplete(p: Predicate): boolean {
  return !NEEDS_VALUE.has(p.kind) || p.value.trim() !== ''
}

export function predicateToDsl(p: Predicate): Record<string, unknown> {
  switch (p.kind) {
    case 'is_br':          return { field: 'is_br',                      op: 'eq',       value: true }
    case 'has_rpki':       return { field: 'has_rpki',                   op: 'eq',       value: true }
    case 'no_rpki':        return { field: 'has_rpki',                   op: 'eq',       value: false }
    case 'has_aspa':       return { field: 'has_aspa',                   op: 'eq',       value: true }
    case 'no_aspa':        return { field: 'has_aspa',                   op: 'eq',       value: false }
    case 'v4_ft':          return { field: 'global_prefixes_v4_count',   op: 'gte',      value: 1 }
    case 'v6_ft':          return { field: 'global_prefixes_v6_count',   op: 'gte',      value: 1 }
    case 'ixps_direct_in':  return { field: 'ixps_direct',  op: 'contains',  value: p.value.trim().toLowerCase() }
    case 'ixps_direct_nin': return { field: 'ixps_direct',  op: 'ncontains', value: p.value.trim().toLowerCase() }
    case 'ixps_origin_in':  return { field: 'ixps_origin',  op: 'contains',  value: p.value.trim().toLowerCase() }
    case 'ixps_origin_nin': return { field: 'ixps_origin',  op: 'ncontains', value: p.value.trim().toLowerCase() }
    case 'pct_v6_gte':     return { field: 'pct_v6',        op: 'gte',       value: parseFloat(p.value) }
    case 'porte':          return { field: 'porte',          op: 'eq',        value: p.value }
    case 'has_scm':        return { field: 'has_scm',        op: 'eq',        value: true }
    case 'no_scm':         return { field: 'has_scm',        op: 'eq',        value: false }
    default:               return {}
  }
}

export function groupToDsl(g: FilterGroup): Record<string, unknown> | null {
  const dsls = g.predicates
    .filter(isComplete)
    .map(predicateToDsl)
    .filter(d => Object.keys(d).length > 0)
  if (dsls.length === 0) return null
  if (dsls.length === 1) return dsls[0]
  return { [g.op]: dsls }
}

// Parte do body comum a todas as camadas com recorte (filtro + proximidade).
export function recorteBody(s: MapState): MapQueryBody {
  const groupDsls = s.groups.map(groupToDsl).filter(Boolean) as Record<string, unknown>[]
  const body: MapQueryBody = {}
  if (groupDsls.length === 1) body.filter = groupDsls[0]
  else if (groupDsls.length > 1) body.filter = { [s.groupOp]: groupDsls }

  if (s.nearIxp.trim()) {
    const nearSpec = { ixp: s.nearIxp.trim().toLowerCase(), radius_km: s.nearRadiusKm }
    if (s.nearMode === 'sede') body.near = nearSpec
    else body.near_prefixes = nearSpec
  }
  return body
}

export function hasRecorte(s: MapState): boolean {
  const b = recorteBody(s)
  return b.filter !== undefined || b.near !== undefined || b.near_prefixes !== undefined
}

export const parseAsns = (txt: string) =>
  txt.split(',').map(t => parseInt(t.trim(), 10)).filter(n => !isNaN(n) && n > 0)

export function layerBody(id: DataLayerId, s: MapState): MapQueryBody {
  const body: MapQueryBody = { layers: [id] }
  if (!LAYER_BY_ID[id].recorte) return body
  Object.assign(body, recorteBody(s))
  if (id === 'asns_geo') body.color_by = s.colorBy
  if (id === 'outorgas_scm') body.scm_mode = s.scmMode
  if (PTT_LAYERS.has(id)) {
    body.ix_code = s.ixCode.trim().toLowerCase()
    body.ix_apply_filter = true
    if (s.ixExcludeAsns.trim()) body.ix_exclude_asns = parseAsns(s.ixExcludeAsns)
    if (s.ixIncludeAsns.trim()) body.ix_include_asns = parseAsns(s.ixIncludeAsns)
  }
  return body
}

export type LayerData = GeoJSON.FeatureCollection & Partial<Pick<MapQueryResponse, 'snapshot_date' | 'matched_asns'>>

// Chave + função de busca de cada camada de dados. Rodovias usam a rota GET
// filtrada no servidor (124 mil feições no total: grande demais para o POST /map/query).
export function layerQuery(id: DataLayerId, s: MapState, date?: string): { key: QueryKey; fn: (signal: AbortSignal) => Promise<LayerData> } {
  if (id === 'roads_federal' || id === 'roads_estadual') {
    const params = new URLSearchParams({ jurisdicao: id === 'roads_federal' ? 'Federal' : 'Estadual/Distrital' })
    if (id === 'roads_federal' ? s.roadsFederalPaved : s.roadsEstadualPaved) params.set('pavimentada', 'true')
    if (date) params.set('date', date)
    const url = `/api/v1/map/rodovias?${params}`
    return {
      key: ['map-layer', id, url],
      fn: async signal => {
        const res = await fetch(url, { credentials: 'include', signal })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      },
    }
  }
  if (id === 'erbs') {
    const params = new URLSearchParams()
    if (s.erbsGeracao) params.set('geracao', s.erbsGeracao)
    if (date) params.set('date', date)
    const url = `/api/v1/map/erbs${params.size ? `?${params}` : ''}`
    return {
      key: ['map-layer', id, url],
      fn: async signal => {
        const res = await fetch(url, { credentials: 'include', signal })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      },
    }
  }
  const body = layerBody(id, s)
  return {
    key: ['map-layer', id, date, body],
    fn: signal => fetchMapQuery(body, date, signal) as Promise<LayerData>,
  }
}

let _idSeq = 0
const nextId = () => String(++_idSeq)

export function makeGroup(): FilterGroup {
  return { id: nextId(), op: 'and', predicates: [] }
}

export function makePredicate(kind: PredicateKind = 'is_br'): Predicate {
  return { id: nextId(), kind, value: '' }
}
