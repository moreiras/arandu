// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/**
 * Feições GeoJSON de cada camada do Localizador, com o HTML do balão (`tip`) e do modal de agregados (`modalHtml`) já montados.
 * Funções puras de dados → feições (as camadas do MapLibre só recebem o resultado); testadas em balloes.test.ts.
 */
import { SCM_HQ_COLOR, SCM_SELO, SCM_SEM_AS_COLOR, CNPJ_COLOR, HQ_COLOR, fmtBR, formatCnpj, parseAsns, prefixColor } from './tipos'
import type { AsnDot, Bubble, InfoAsn, MunicipioSici, ScmGeoFeature } from './tipos'
import type { GrupoCoord } from './calculos'
import { escapar } from '../../lib/html'

const SCM_TAG = `<span style="background:${escapar(SCM_SELO)};color:white;font-size:10px;padding:0 5px;border-radius:9999px">SCM</span>`

/** Bolhas de prefixos agrupadas por coordenada exata (evita sobreposição); grupos com vários ASes viram um modal. */
export function featuresBolhas(prefixBubbles: Bubble[], asnNameMap: Map<number, InfoAsn>, asnToCnpj: Map<number, string>): GeoJSON.Feature[] {
  const bubbleByCoord = new Map<string, Bubble[]>()
  for (const b of prefixBubbles) {
    const key = `${b.lon},${b.lat}`
    if (!bubbleByCoord.has(key)) bubbleByCoord.set(key, [])
    bubbleByCoord.get(key)!.push(b)
  }
  const bubbleFeatures: GeoJSON.Feature[] = []
  for (const group of bubbleByCoord.values()) {
    const [b0] = group
    const totalCount = group.reduce((s, b) => s + b.count, 0)
    const dominant = group.reduce((a, b) => b.count > a.count ? b : a, b0)
    const color = prefixColor(dominant.afi, dominant.own)
    const loc = [b0.city, b0.uf].filter(Boolean).join('/')
    let tip: string
    if (group.length === 1) {
      const asnInfo = asnNameMap.get(b0.asn)
      const cnpj = asnInfo?.cnpj ?? asnToCnpj.get(b0.asn)
      const blocks = `${b0.count.toLocaleString('pt-BR')} ${b0.count === 1 ? 'prefixo' : 'prefixos'}`
      tip =
        `<b>AS${escapar(b0.asn)}</b><br/>` +
        (b0.name ? `${escapar(b0.name)}<br/>` : '') +
        (cnpj ? `<a href="/operadora/${escapar(cnpj)}" style="color:${CNPJ_COLOR};font-family:monospace">${escapar(formatCnpj(cnpj))}</a><br/>` : '') +
        (asnInfo?.razao_social && asnInfo.razao_social !== b0.name ? `<span style="font-size:10px;color:#9ca3af">Anatel: ${escapar(asnInfo.razao_social)}</span><br/>` : '') +
        (asnInfo?.nome_fantasia && asnInfo.nome_fantasia !== b0.name && asnInfo.nome_fantasia !== asnInfo.razao_social ? `<span style="font-size:10px;color:#9ca3af">fantasia: ${escapar(asnInfo.nome_fantasia)}</span><br/>` : '') +
        (loc ? `<span style="font-size:10px;color:#9ca3af">${escapar(loc)}</span><br/>` : '') +
        `<span style="font-size:10px;color:#9ca3af">${escapar(blocks)} · ${escapar(b0.afi === 6 ? 'IPv6' : 'IPv4')} · ${escapar(b0.own ? 'sede na região' : 'sede fora')}</span>`
    } else {
      const modalTitle = `${group.length} ASes${loc ? ` · ${loc}` : ''}`
      const modalHtml = group.map(b => {
        const asnInfo = asnNameMap.get(b.asn)
        const cnpj = asnInfo?.cnpj ?? asnToCnpj.get(b.asn)
        const blocks = `${b.count.toLocaleString('pt-BR')} ${b.count === 1 ? 'prefixo' : 'prefixos'}`
        return `<div style="border-top:1px solid #374151;padding:4px 0 3px">` +
          `<b>AS${escapar(b.asn)}</b><br/>` +
          (b.name ? `${escapar(b.name)}<br/>` : '') +
          (cnpj ? `<a href="/operadora/${escapar(cnpj)}" style="color:${CNPJ_COLOR};font-family:monospace;font-size:10px">${escapar(formatCnpj(cnpj))}</a><br/>` : '') +
          `<span style="font-size:10px;color:#9ca3af">${escapar(blocks)} · ${escapar(b.afi === 6 ? 'IPv6' : 'IPv4')} · ${escapar(b.own ? 'sede na região' : 'sede fora')}</span>` +
          `</div>`
      }).join('')
      tip = `<b>${escapar(modalTitle)}</b><br/><span style="font-size:10px;color:#9ca3af">clique para ver todos</span>`
      bubbleFeatures.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [b0.lon, b0.lat] },
        properties: { count: totalCount, color, tip, entityCount: group.length, modalTitle, modalHtml },
      })
      continue
    }
    bubbleFeatures.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [b0.lon, b0.lat] },
      properties: { count: totalCount, color, tip, entityCount: 1, modalTitle: '', modalHtml: '' },
    })
  }
  return bubbleFeatures
}

/** Sedes de AS agrupadas por coordenada exata. Coordenadas que têm SCMs saem daqui (vão para a camada de SCM). */
export function featuresSedes(asnDots: AsnDot[], showScms: boolean, coordGroups: Map<string, GrupoCoord>, asnToCnpj: Map<number, string>): GeoJSON.Feature[] {
  const filteredDots = showScms
    ? asnDots.filter(d => {
        const g = coordGroups.get(`${d.lon},${d.lat}`)
        return !g || g.scms.length === 0
      })
    : asnDots

  const asnByCoord = new Map<string, AsnDot[]>()
  for (const d of filteredDots) {
    const key = `${d.lon},${d.lat}`
    if (!asnByCoord.has(key)) asnByCoord.set(key, [])
    asnByCoord.get(key)!.push(d)
  }

  const asnFeatures: GeoJSON.Feature[] = []
  for (const group of asnByCoord.values()) {
    const [d0] = group
    const hasAnyScm = group.some(d => asnToCnpj.has(d.asn))
    const color = hasAnyScm ? SCM_HQ_COLOR : HQ_COLOR
    const count = group.length
    const loc = [d0.city, d0.uf].filter(Boolean).join(', ')
    let tip: string
    let modalTitle = ''
    let modalHtml = ''
    if (count === 1) {
      const hasScm = asnToCnpj.has(d0.asn)
      const cnpj = d0.cnpj ?? asnToCnpj.get(d0.asn)
      tip =
        `<b>AS${escapar(d0.asn)}</b>${hasScm ? ` ${SCM_TAG}` : ''}<br/>` +
        (d0.name ? `${escapar(d0.name)}<br/>` : '') +
        (cnpj ? `<a href="/operadora/${escapar(cnpj)}" style="color:${CNPJ_COLOR};font-family:monospace">${escapar(formatCnpj(cnpj))}</a><br/>` : '') +
        (d0.razao_social && d0.razao_social !== d0.name ? `<span style="font-size:10px;color:#9ca3af">Anatel: ${escapar(d0.razao_social)}</span><br/>` : '') +
        (d0.nome_fantasia && d0.nome_fantasia !== d0.name && d0.nome_fantasia !== d0.razao_social ? `<span style="font-size:10px;color:#9ca3af">fantasia: ${escapar(d0.nome_fantasia)}</span><br/>` : '') +
        (loc ? `<span style="font-size:10px;color:#9ca3af">${escapar(loc)}</span><br/>` : '') +
        `<span style="font-size:10px;color:#9ca3af">sede</span>`
    } else {
      modalTitle = `${count} sedes de AS${loc ? ` · ${loc}` : ''}`
      modalHtml = group.map(d => {
        const hasScm = asnToCnpj.has(d.asn)
        const cnpj = d.cnpj ?? asnToCnpj.get(d.asn)
        return `<div style="border-top:1px solid #374151;padding:4px 0 3px">` +
          `<b>AS${escapar(d.asn)}</b>${hasScm ? ` ${SCM_TAG}` : ''}<br/>` +
          (d.name ? `${escapar(d.name)}<br/>` : '') +
          (cnpj ? `<a href="/operadora/${escapar(cnpj)}" style="color:${CNPJ_COLOR};font-family:monospace;font-size:10px">${escapar(formatCnpj(cnpj))}</a>` : '') +
          (d.nome_fantasia && d.nome_fantasia !== d.name ? `<br/><span style="font-size:10px;color:#9ca3af">fantasia: ${escapar(d.nome_fantasia)}</span>` : '') +
          `</div>`
      }).join('')
      tip = `<b>${escapar(modalTitle)}</b><br/><span style="font-size:10px;color:#9ca3af">clique para ver todas</span>`
    }
    asnFeatures.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [d0.lon, d0.lat] },
      properties: { color, radius: count > 1 ? 8 : 6, tip, entityCount: count, modalTitle, modalHtml },
    })
  }
  return asnFeatures
}

/** PIX (PTTs) — amarelo, mesma cor do mapa da página de IXP. */
export function featuresPix(pixDots: Array<{ lat: number; lon: number; name: string; ixpName: string }>): GeoJSON.Feature[] {
  return pixDots.map((p): GeoJSON.Feature => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
    properties: { tip: `<b>${escapar(p.name)}</b>${p.ixpName ? `<br/>IX ${escapar(p.ixpName)}` : ''}` },
  }))
}

/**
 * Camada de SCMs: usa os grupos por coordenada para unificar ASes e SCMs no mesmo ponto num único círculo. Sem `showAsns`, os grupos
 * têm `asns` vazio e o comportamento é o de SCMs agrupados por coordenada.
 */
export function featuresScm(coordGroups: Map<string, GrupoCoord>, asnToCnpj: Map<number, string>, asnNameMap: Map<number, InfoAsn>): GeoJSON.Feature[] {
  // Tooltip de um único SCM sem AS correspondente no grupo.
  const scmTip = (p: ScmGeoFeature['properties'], asns: number[]): string => {
    const hasAsn = asns.length > 0
    const fantasia = p.nome_fantasia && p.nome_fantasia !== 'N/I' && p.nome_fantasia !== p.razao_social
      ? p.nome_fantasia : null
    const loc = `${p.municipio ?? ''}${p.uf ? `/${p.uf}` : ''}`
    return hasAsn
      ? asns.map(a => {
          const nm = asnNameMap.get(a)?.name
          return `<b>AS${escapar(a)}</b>${nm ? ` · ${escapar(nm)}` : ''}`
        }).join('<br/>') + '<br/>' +
        `<a href="/operadora/${escapar(p.cnpj)}" style="color:${CNPJ_COLOR};font-family:monospace">${escapar(formatCnpj(p.cnpj))}</a><br/>` +
        `<span style="font-size:10px;color:#9ca3af">Anatel: </span>${escapar(p.razao_social)}<br/>` +
        (fantasia ? `<span style="font-size:10px;color:#9ca3af">fantasia: ${escapar(fantasia)}</span><br/>` : '') +
        (loc ? `<span style="font-size:10px;color:#9ca3af">${escapar(loc)}</span><br/>` : '') +
        SCM_TAG
      : `${escapar(p.razao_social)}<br/>` +
        `<a href="/operadora/${escapar(p.cnpj)}" style="color:${CNPJ_COLOR};font-family:monospace">${escapar(formatCnpj(p.cnpj))}</a><br/>` +
        (fantasia ? `<span style="font-size:10px;color:#9ca3af">fantasia: ${escapar(fantasia)}</span><br/>` : '') +
        (loc ? `<span style="font-size:10px;color:#9ca3af">${escapar(loc)}</span><br/>` : '') +
        SCM_TAG
  }

  // Tooltip de uma sede de AS (com badge SCM quando há outorga correspondente no grupo).
  const asnTip = (d: AsnDot, hasScm: boolean): string => {
    const cnpj = d.cnpj ?? asnToCnpj.get(d.asn)
    const loc = [d.city, d.uf].filter(Boolean).join(', ')
    return `<b>AS${escapar(d.asn)}</b>${hasScm ? ` ${SCM_TAG}` : ''}<br/>` +
      (d.name ? `${escapar(d.name)}<br/>` : '') +
      (cnpj ? `<a href="/operadora/${escapar(cnpj)}" style="color:${CNPJ_COLOR};font-family:monospace">${escapar(formatCnpj(cnpj))}</a><br/>` : '') +
      (d.razao_social && d.razao_social !== d.name ? `<span style="font-size:10px;color:#9ca3af">Anatel: ${escapar(d.razao_social)}</span><br/>` : '') +
      (d.nome_fantasia && d.nome_fantasia !== d.name && d.nome_fantasia !== d.razao_social ? `<span style="font-size:10px;color:#9ca3af">fantasia: ${escapar(d.nome_fantasia)}</span><br/>` : '') +
      (loc ? `<span style="font-size:10px;color:#9ca3af">${escapar(loc)}</span><br/>` : '') +
      `<span style="font-size:10px;color:#9ca3af">sede</span>`
  }

  // Todos os grupos que têm ao menos um SCM (coordGroups já une ASes e SCMs
  // por coordenada exata quando showAsns=true).
  const groupsToRender = [...coordGroups.values()].filter(g => g.scms.length > 0)

  const features: GeoJSON.Feature[] = []
  for (const { lon, lat, asns: groupAsns, scms: groupScms } of groupsToRender) {
    // CNPJs cobertos por ASes no grupo: SCM do mesmo CNPJ não conta separado.
    const asnCnpjs = new Set(
      groupAsns.map(d => d.cnpj ?? asnToCnpj.get(d.asn)).filter((c): c is string => !!c)
    )
    const pureScms = groupScms.filter(f => !asnCnpjs.has(f.properties.cnpj))

    // Total de operadores únicos neste ponto.
    const totalCount = groupAsns.length + pureScms.length

    // Cinza = qualquer AS presente; roxo = apenas SCMs sem AS.
    const hasAnyAs = groupAsns.length > 0 || groupScms.some(f => f.properties.has_asn)
    const color = hasAnyAs ? SCM_HQ_COLOR : SCM_SEM_AS_COLOR
    const strokeWidth = hasAnyAs ? 2 : 1

    let tip: string
    let modalTitle = ''
    let modalHtml = ''

    if (groupAsns.length === 0 && groupScms.length === 1) {
      // Único SCM sem AS na coordenada.
      tip = scmTip(groupScms[0].properties, parseAsns(groupScms[0].properties.asns))
    } else if (totalCount === 1 && groupAsns.length === 1 && pureScms.length === 0) {
      // Único operador: AS com sua própria outorga SCM (ou AS sozinho).
      const matchedScm = groupScms.find(f => asnCnpjs.has(f.properties.cnpj))
      tip = asnTip(groupAsns[0], !!matchedScm)
    } else {
      // Múltiplos operadores — tooltip resumido; lista completa no modal (ao clicar).
      const loc = groupScms[0]
        ? `${groupScms[0].properties.municipio ?? ''}${groupScms[0].properties.uf ? `/${groupScms[0].properties.uf}` : ''}`
        : [groupAsns[0]?.city, groupAsns[0]?.uf].filter(Boolean).join('/')

      const items: string[] = []

      for (const d of groupAsns) {
        const cnpj = d.cnpj ?? asnToCnpj.get(d.asn)
        const hasScm = !!cnpj && groupScms.some(f => f.properties.cnpj === cnpj)
        items.push(
          `<div style="border-top:1px solid #374151;padding:4px 0 3px">` +
          `<b>AS${escapar(d.asn)}</b>${hasScm ? ` ${SCM_TAG}` : ''}<br/>` +
          (d.name ? `${escapar(d.name)}<br/>` : '') +
          (cnpj ? `<a href="/operadora/${escapar(cnpj)}" style="color:${CNPJ_COLOR};font-family:monospace;font-size:10px">${escapar(formatCnpj(cnpj))}</a>` : '') +
          (d.nome_fantasia && d.nome_fantasia !== d.name ? `<br/><span style="font-size:10px;color:#9ca3af">fantasia: ${escapar(d.nome_fantasia)}</span>` : '') +
          `</div>`
        )
      }

      for (const f of pureScms) {
        const p = f.properties
        const scmAsns = parseAsns(p.asns)
        const fantasia = p.nome_fantasia && p.nome_fantasia !== 'N/I' && p.nome_fantasia !== p.razao_social
          ? p.nome_fantasia : null
        items.push(
          `<div style="border-top:1px solid #374151;padding:4px 0 3px">` +
          (scmAsns.length > 0 ? scmAsns.map(a => {
            const nm = asnNameMap.get(a)?.name
            return `<b>AS${escapar(a)}</b>${nm ? ` · ${escapar(nm)}` : ''}`
          }).join('<br/>') + '<br/>' : '') +
          `${escapar(p.razao_social)}<br/>` +
          `<a href="/operadora/${escapar(p.cnpj)}" style="color:${CNPJ_COLOR};font-family:monospace;font-size:10px">${escapar(formatCnpj(p.cnpj))}</a> ${SCM_TAG}` +
          (fantasia ? `<br/><span style="font-size:10px;color:#9ca3af">fantasia: ${escapar(fantasia)}</span>` : '') +
          `</div>`
        )
      }

      modalTitle = `${totalCount} operadores${loc ? ` · ${loc}` : ''}`
      modalHtml = items.join('')
      tip = `<b>${escapar(modalTitle)}</b><br/><span style="font-size:10px;color:#9ca3af">clique para ver todos</span>`
    }

    features.push({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [lon, lat] },
      properties: { color, strokeWidth, radius: totalCount > 1 ? 8 : 6, tip,
        entityCount: totalCount, modalTitle, modalHtml },
    })
  }
  return features
}

/** Um ponto por município no raio (centróide do IBGE); com vários operadores abre modal ao clicar. */
export function featuresSici(siciMunInRadius: MunicipioSici[]): GeoJSON.Feature[] {
  return siciMunInRadius.map(mun => {
    const loc = `${mun.nome}${mun.uf ? `/${mun.uf}` : ''}`
    let tip: string
    let modalTitle = ''
    let modalHtml = ''

    if (mun.operadores.length <= 1) {
      const op = mun.operadores[0]
      tip = op
        ? `<b>${escapar(loc)}</b><br/>` +
          `<a href="/operadora/${escapar(op.cnpj)}" style="color:${CNPJ_COLOR};font-family:monospace">${escapar(formatCnpj(op.cnpj))}</a> ${escapar(op.empresa)}<br/>` +
          `<span style="font-size:10px;color:#9ca3af">${escapar(fmtBR(op.acessos))} acessos declarados ao SICI</span>`
        : `<b>${escapar(loc)}</b><br/><span style="font-size:10px;color:#9ca3af">${escapar(fmtBR(mun.acessos))} acessos declarados ao SICI</span>`
    } else {
      modalTitle = `${mun.operadores.length} operadores · ${loc}`
      modalHtml = mun.operadores.map(op =>
        `<div style="border-top:1px solid #374151;padding:4px 0 3px">` +
        `<a href="/operadora/${escapar(op.cnpj)}" style="color:${CNPJ_COLOR};font-family:monospace;font-size:10px">${escapar(formatCnpj(op.cnpj))}</a><br/>` +
        `${escapar(op.empresa)}<br/>` +
        `<span style="font-size:10px;color:#9ca3af">${escapar(fmtBR(op.acessos))} acessos</span>` +
        `</div>`
      ).join('')
      tip = `<b>${escapar(modalTitle)}</b><br/><span style="font-size:10px;color:#9ca3af">${escapar(fmtBR(mun.acessos))} acessos declarados no total · clique para ver todos</span>`
    }

    return {
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [mun.lon, mun.lat] },
      properties: {
        radius: mun.operadores.length > 1 ? 8 : 6, tip,
        entityCount: mun.operadores.length, modalTitle, modalHtml,
      },
    }
  })
}
