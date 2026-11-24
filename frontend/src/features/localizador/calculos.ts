// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/**
 * Cálculos do Localizador de Redes: o que está dentro do raio, a lista de entidades deduplicada por CNPJ, agrupamento por coordenada,
 * contagens e participação em IXes. Funções puras (as `useMemo` da página só chamam estas); testadas em calculos.test.ts.
 */
import { distKm } from './geo'
import { MAJOR_IX, parseAsns } from './tipos'
import type {
  AsnDot, AsnFeature, AsnNaLista, Bubble, Entity, InfoAsn, MunicipioSici, PixFeature, PrefixFeature, ScmGeoFeature, TagIx,
} from './tipos'
import type { SiciMunicipiosMapaResponse } from '../../types/api'

export type Ponto = [number, number] // [lat, lon]

/** AS → nome/CNPJ/local, a partir das sedes geolocalizadas. */
export function mapaDeNomes(asnGeo?: { features: AsnFeature[] }): Map<number, InfoAsn> {
  const m = new Map<number, InfoAsn>()
  for (const f of asnGeo?.features ?? []) {
    m.set(f.properties.asn, {
      name: f.properties.name,
      cnpj: f.properties.cnpj || undefined,
      razao_social: f.properties.razao_social || undefined,
      nome_fantasia: f.properties.nome_fantasia || undefined,
      city: f.properties.city,
      uf: f.properties.uf,
    })
  }
  return m
}

/** Sedes de AS no raio, bolhas de prefixos (uma por AS+família+local) e a lista de ASes (sede e/ou prefixo na região). */
export function filtrarNoRaio(p: {
  markerPos: Ponto | null; radius: number; showAsns: boolean; showPrefixes: boolean
  asnGeo?: { features: AsnFeature[] }; prefixGeo?: { features: PrefixFeature[] }; asnNameMap: Map<number, InfoAsn>
}): { filteredAsns: AsnNaLista[]; asnDots: AsnDot[]; prefixBubbles: Bubble[] } {
  const { markerPos, radius, showAsns, showPrefixes, asnGeo, prefixGeo, asnNameMap } = p
  if (!markerPos) return { filteredAsns: [], asnDots: [], prefixBubbles: [] }
  const [lat, lon] = markerPos

  const asnDots: AsnDot[] = []
  const hqAsns = new Map<number, { name: string; city?: string; uf?: string }>()

  for (const f of asnGeo?.features ?? []) {
    const [flon, flat] = f.geometry.coordinates
    if (distKm(lat, lon, flat, flon) <= radius) {
      hqAsns.set(f.properties.asn, {
        name: f.properties.name,
        city: f.properties.city,
        uf: f.properties.uf,
      })
      asnDots.push({ lat: flat, lon: flon, asn: f.properties.asn, name: f.properties.name, cnpj: f.properties.cnpj || undefined, razao_social: f.properties.razao_social || undefined, nome_fantasia: f.properties.nome_fantasia || undefined, city: f.properties.city, uf: f.properties.uf })
    }
  }

  // Bolhas de prefixos: a API já entrega uma feição por (AS, versão, município) com `prefix_count` (não há posição por
  // prefixo); aqui só se somam as que caem no mesmo ponto. Dimensionadas pelo nº de prefixos (≈ block_count da página de ASN).
  const bubbleMap = new Map<string, Bubble>()
  // ASes que atuam na região via prefixo (origem dentro do raio), v4/v6
  const prefixAsns = new Map<number, { name: string; city?: string; uf?: string; v4: boolean; v6: boolean }>()

  if (showPrefixes) {
    for (const f of prefixGeo?.features ?? []) {
      const [flon, flat] = f.geometry.coordinates
      if (distKm(lat, lon, flat, flon) > radius) continue
      const asn = f.properties.origin_asn
      if (!asn) continue
      const afi = f.properties.ip_version === 6 ? 6 : 4
      const own = hqAsns.has(asn) // sede na região → "próprio"; senão "externo"
      const latR = flat.toFixed(3)
      const lonR = flon.toFixed(3)
      const key = `${asn}|${afi}|${latR}|${lonR}`
      const existing = bubbleMap.get(key)
      const n = f.properties.prefix_count ?? 1
      if (existing) {
        existing.count += n
      } else {
        bubbleMap.set(key, {
          lat: flat, lon: flon, asn, name: asnNameMap.get(asn)?.name ?? '',
          afi, own, city: f.properties.city, uf: f.properties.uf,
          count: n,
        })
      }
      const acc = prefixAsns.get(asn)
      if (acc) {
        if (afi === 4) acc.v4 = true; else acc.v6 = true
      } else {
        prefixAsns.set(asn, {
          ...(asnNameMap.get(asn) ?? { name: '' }),
          v4: afi === 4, v6: afi === 6,
        })
      }
    }
  }

  // Bolhas "externas" (sede fora) abaixo, "próprias" (sede na região) acima
  const prefixBubbles = [...bubbleMap.values()].sort((a, b) => Number(a.own) - Number(b.own))

  const all: AsnNaLista[] = []
  if (showAsns) {
    for (const [asn, info] of hqAsns) {
      const pfx = prefixAsns.get(asn)
      all.push({ asn, ...info, fromHq: true, v4: pfx?.v4 ?? false, v6: pfx?.v6 ?? false })
    }
  }
  if (showPrefixes) {
    for (const [asn, info] of prefixAsns) {
      if (showAsns && hqAsns.has(asn)) continue
      all.push({ asn, name: info.name, city: info.city, uf: info.uf, fromHq: false, v4: info.v4, v6: info.v6 })
    }
  }
  all.sort((a, b) => a.asn - b.asn)

  return { filteredAsns: all, asnDots, prefixBubbles }
}

/** PIX (PTTs) dentro do círculo de interesse. */
export function pixNoRaio(markerPos: Ponto | null, radius: number, pixGeo?: { features: PixFeature[] }) {
  const out: Array<{ lat: number; lon: number; name: string; ixpName: string }> = []
  if (!markerPos) return out
  const [lat, lon] = markerPos
  for (const f of pixGeo?.features ?? []) {
    const [flon, flat] = f.geometry.coordinates
    if (distKm(lat, lon, flat, flon) <= radius) {
      out.push({ lat: flat, lon: flon, name: f.properties.name ?? '', ixpName: f.properties.ixp_name ?? '' })
    }
  }
  return out
}

/** SCMs dentro do raio. */
export function scmsNoRaio(markerPos: Ponto | null, radius: number, scmGeo?: { features: ScmGeoFeature[] }): ScmGeoFeature[] {
  if (!markerPos) return []
  const [lat, lon] = markerPos
  return (scmGeo?.features ?? []).filter(f => {
    const [flon, flat] = f.geometry.coordinates
    return distKm(lat, lon, flat, flon) <= radius
  })
}

/** Municípios com usuários declarados ao SICI dentro do raio (centróide do IBGE). */
export function municipiosSiciNoRaio(
  markerPos: Ponto | null, radius: number,
  siciMunData?: SiciMunicipiosMapaResponse, centroides?: Record<string, [number, number]>,
): MunicipioSici[] {
  const out: MunicipioSici[] = []
  if (!markerPos || !siciMunData || !centroides) return out
  const [lat, lon] = markerPos
  for (const [ibge, mun] of Object.entries(siciMunData.municipios)) {
    const c = centroides[ibge]
    if (!c) continue
    const [mlon, mlat] = c
    if (distKm(lat, lon, mlat, mlon) <= radius) {
      out.push({ ibge, nome: mun.nome, uf: mun.uf, lat: mlat, lon: mlon, acessos: mun.acessos, operadores: mun.operadores })
    }
  }
  return out
}

/** Um item por CNPJ, somando acessos entre os municípios do raio — entra na lista de entidades ("SCMs correspondentes"). */
export function operadoresSici(municipios: MunicipioSici[]) {
  const byCnpj = new Map<string, { cnpj: string; empresa: string; acessos: number; municipios: number }>()
  for (const mun of municipios) {
    for (const op of mun.operadores) {
      const acc = byCnpj.get(op.cnpj)
      if (acc) { acc.acessos += op.acessos; acc.municipios++ }
      else byCnpj.set(op.cnpj, { cnpj: op.cnpj, empresa: op.empresa, acessos: op.acessos, municipios: 1 })
    }
  }
  return [...byCnpj.values()].sort((a, b) => b.acessos - a.acessos)
}

/**
 * Índices de CNPJ ↔ ASN construídos sobre todos os features (não só os do raio), para que sedes de AS mostrem cor e badge SCM
 * mesmo com o overlay desativado.
 */
export function indicesScm(scmGeo?: { features: ScmGeoFeature[] }, asnGeo?: { features: AsnFeature[] }) {
  const asnToCnpj = new Map<number, string>()
  const cnpjToAsns = new Map<string, number[]>()
  for (const f of scmGeo?.features ?? []) {
    const asns = parseAsns(f.properties.asns)
    for (const asn of asns) if (!asnToCnpj.has(asn)) asnToCnpj.set(asn, f.properties.cnpj)
    if (asns.length === 0) continue
    const existing = cnpjToAsns.get(f.properties.cnpj)
    if (existing) {
      for (const asn of asns) if (!existing.includes(asn)) existing.push(asn)
    } else {
      cnpjToAsns.set(f.properties.cnpj, [...asns])
    }
  }
  const scmCnpjs = new Set((scmGeo?.features ?? []).map(f => f.properties.cnpj))
  // ASNs por CNPJ combinando o cadastro dos ASes (asnGeo) e as outorgas SCM.
  const cnpjAllAsns = new Map<string, Set<number>>()
  const add = (cnpj: string, asn: number) => {
    const s = cnpjAllAsns.get(cnpj)
    if (s) s.add(asn); else cnpjAllAsns.set(cnpj, new Set([asn]))
  }
  for (const f of asnGeo?.features ?? []) if (f.properties.cnpj) add(f.properties.cnpj, f.properties.asn)
  for (const [cnpj, asns] of cnpjToAsns) for (const asn of asns) add(cnpj, asn)
  return { asnToCnpj, cnpjToAsns, scmCnpjs, cnpjAllAsns }
}

/**
 * Lista unificada de entidades: ASes (sede/prefixos) + SCMs (sede) + SICI (usuários), deduplicada por CNPJ. Um AS que também é SCM
 * (ou vice-versa) aparece uma única vez com os dois badges.
 */
export function montarEntidades(p: {
  filteredAsns: AsnNaLista[]; scmsInRadius: ScmGeoFeature[]; asnToCnpj: Map<number, string>; cnpjAllAsns: Map<string, Set<number>>
  scmCnpjs: Set<string>; asnNameMap: Map<number, InfoAsn>; showScms: boolean; showSici: boolean
  siciOperadores: ReturnType<typeof operadoresSici>
}): Entity[] {
  const { filteredAsns, scmsInRadius, asnToCnpj, cnpjAllAsns, scmCnpjs, asnNameMap, showScms, showSici, siciOperadores } = p
  const byKey = new Map<string, Entity>()
  const get = (cnpj: string | undefined, asn: number | undefined, name: string, city?: string, uf?: string): Entity => {
    const key = cnpj ? `cnpj:${cnpj}` : `asn:${asn}`
    let e = byKey.get(key)
    if (!e) {
      const asns = cnpj ? [...(cnpjAllAsns.get(cnpj) ?? [])] : []
      if (asn != null && !asns.includes(asn)) asns.push(asn)
      asns.sort((x, y) => x - y)
      e = {
        key, cnpj, asns, asnsNoRaio: [], name, city, uf,
        fromHq: false, v4: false, v6: false,
        scm: !!cnpj && scmCnpjs.has(cnpj), scmHq: false,
      }
      byKey.set(key, e)
    } else {
      if (!e.name) e.name = name
      if (!e.city && !e.uf) { e.city = city; e.uf = uf }
    }
    return e
  }

  for (const a of filteredAsns) {
    const cnpj = asnNameMap.get(a.asn)?.cnpj ?? asnToCnpj.get(a.asn)
    const e = get(cnpj, a.asn, a.name, a.city, a.uf)
    if (!e.asns.includes(a.asn)) { e.asns.push(a.asn); e.asns.sort((x, y) => x - y) }
    if (!e.asnsNoRaio.includes(a.asn)) { e.asnsNoRaio.push(a.asn); e.asnsNoRaio.sort((x, y) => x - y) }
    e.fromHq ||= a.fromHq
    e.v4 ||= a.v4
    e.v6 ||= a.v6
  }

  if (showScms) {
    for (const f of scmsInRadius) {
      const p = f.properties
      const e = get(p.cnpj, undefined, p.razao_social, p.municipio, p.uf)
      e.scm = true
      e.scmHq = true
    }
  }

  if (showSici) {
    for (const op of siciOperadores) {
      const e = get(op.cnpj, undefined, op.empresa)
      e.scm = true
      e.sici = { acessos: op.acessos, municipios: op.municipios }
    }
  }

  // Entidades com ASN primeiro (pelo menor ASN), depois as só-SCM na ordem
  // de inserção (sedes SCM e, em seguida, SICI por nº de acessos).
  const all = [...byKey.values()]
  const withAsn = all.filter(e => e.asns.length > 0).sort((x, y) => x.asns[0] - y.asns[0])
  const withoutAsn = all.filter(e => e.asns.length === 0)
  return [...withAsn, ...withoutAsn]
}

/** `asns` conta ASNs distintos no raio (não entidades: um CNPJ com 13 ASNs contava "1 AS", LOC-E3); `cnpjsComAsn`, as entidades com
 * algum ASN no raio; `scms`, as entidades com outorga SCM. */
export function contagemEntidades(entities: Entity[]) {
  return {
    asns: new Set(entities.flatMap(e => e.asnsNoRaio)).size,
    cnpjsComAsn: entities.filter(e => e.asnsNoRaio.length > 0).length,
    scms: entities.filter(e => e.scm).length,
  }
}

export interface GrupoCoord { lon: number; lat: number; asns: AsnDot[]; scms: ScmGeoFeature[] }

/**
 * Grupos de entidades por coordenada exata, unindo ASes e SCMs no mesmo ponto: com as duas camadas ativas, permite um único círculo
 * em vez de dois sobrepostos.
 */
export function agruparPorCoordenada(p: {
  asnDots: AsnDot[]; scmsInRadius: ScmGeoFeature[]; showAsns: boolean; showScms: boolean; markerPos: Ponto | null
}): Map<string, GrupoCoord> {
  const map = new Map<string, GrupoCoord>()
  if (p.showAsns) {
    for (const d of p.asnDots) {
      const key = `${d.lon},${d.lat}`
      if (!map.has(key)) map.set(key, { lon: d.lon, lat: d.lat, asns: [], scms: [] })
      map.get(key)!.asns.push(d)
    }
  }
  if (p.showScms && p.markerPos) {
    for (const f of p.scmsInRadius) {
      const [lon, lat] = f.geometry.coordinates
      const key = `${lon},${lat}`
      if (!map.has(key)) map.set(key, { lon, lat, asns: [], scms: [] })
      map.get(key)!.scms.push(f)
    }
  }
  return map
}

/** Contagens do resumo. Sedes/prefixos de AS ficam sempre visíveis; SCM/SICI só aparecem com a camada ativa. */
export function resumoDoRaio(p: {
  filteredAsns: AsnNaLista[]; scmsInRadius: ScmGeoFeature[]; siciOperadores: ReturnType<typeof operadoresSici>
  showScms: boolean; showSici: boolean
}) {
  return {
    sedesAsn: p.filteredAsns.filter(a => a.fromHq).length,
    asnsComPrefixo: p.filteredAsns.filter(a => a.v4 || a.v6).length,
    sedesScm: p.showScms ? new Set(p.scmsInRadius.map(f => f.properties.cnpj)).size : 0,
    scmsComUsuarios: p.showSici ? p.siciOperadores.length : 0,
  }
}

/** Participação de um AS em IXes: membro (`m`) e origina prefixos (`o`). */
export type PresencaIx = { m: string[]; o: string[] }

/**
 * Tags de participação por AS (membro), na ordem: mais próximo → principais → "algum outro IX" → "nenhum IX".
 */
export function etiquetasIx(membros: string[], nearestIx: string | null, ixLabel: (code: string) => string): TagIx[] {
  if (membros.length === 0) return [{ code: '', label: 'Nenhum IX', kind: 'none' }]
  const named = new Set<string>([...(nearestIx ? [nearestIx] : []), ...MAJOR_IX])
  const memberSet = new Set(membros)
  const tags: TagIx[] = []
  if (nearestIx && memberSet.has(nearestIx)) {
    tags.push({ code: nearestIx, label: ixLabel(nearestIx), kind: 'near' })
  }
  for (const code of MAJOR_IX) {
    if (code !== nearestIx && memberSet.has(code)) {
      tags.push({ code, label: ixLabel(code), kind: 'major' })
    }
  }
  if (membros.some(c => !named.has(c))) {
    tags.push({ code: '', label: 'Algum IX do IX.br', kind: 'other' })
  }
  return tags
}

/** Contagens gerais de participação em IXes sobre os ASes da lista atual. */
export function contagensIx(filteredAsns: AsnNaLista[], ixOf: (asn: number) => PresencaIx, nearestIx: string | null) {
  let nearMember = 0, nearOrigin = 0, anyMember = 0, otherNotNear = 0
  for (const a of filteredAsns) {
    const { m, o } = ixOf(a.asn)
    if (m.length > 0) anyMember++
    if (nearestIx) {
      if (m.includes(nearestIx)) nearMember++
      if (o.includes(nearestIx)) nearOrigin++
      if (m.length > 0 && !m.includes(nearestIx)) otherNotNear++
    }
  }
  return { nearMember, nearOrigin, anyMember, otherNotNear }
}
