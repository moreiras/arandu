/**
 * CDNRelationsGraph — versão multi-ASN do ASRelationsGraph.
 *
 * Layout: Upstreams (topo) → ASNs da CDN (centro, fixos) → Downstreams (base)
 * Se a CDN tiver um único ASN, comportamento idêntico ao ASRelationsGraph.
 * Se tiver múltiplos, cada ASN fica fixo no centro numa fileira horizontal;
 * os upstreams/downstreams se conectam a um ou mais deles conforme a relação.
 */
import { escapar } from '../../lib/html'
import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import type { ASNDocument } from '../../types/api'

interface GNode extends d3.SimulationNodeDatum {
  id: string
  type: 'main' | 'upstream' | 'downstream' | 'overflow_dn' | 'overflow_up'
  label: string
  asn: number
  _r: number
  overflowTotal?: number
  overflowBr?: number
}

interface GLink extends d3.SimulationLinkDatum<GNode> {
  dir: 'up' | 'down'
}

interface NodeMeta {
  name?: string
  is_br?: boolean
  space_v4?: number
  space_v6?: number
}

const C = {
  main:           '#1d4ed8',
  up_br_v4:       '#93c5fd',
  up_br_v6:       '#fb923c',
  up_intl:        '#8b5cf6',
  dn_v4:          '#86efac',
  dn_v6:          '#fbbf24',
  e_up:           '#fca5a5',
  e_dn:           '#6ee7b7',
  overflow_dn_v4: '#bbf7d0',
  overflow_dn_v6: '#fef08a',
  overflow_up:    '#ddd6fe',
}

function nodeColor(d: GNode, afi: 'v4' | 'v6', meta: Record<string, NodeMeta>): string {
  if (d.type === 'main')         return C.main
  if (d.type === 'overflow_dn')  return afi === 'v6' ? C.overflow_dn_v6 : C.overflow_dn_v4
  if (d.type === 'overflow_up')  return C.overflow_up
  if (d.type === 'downstream')   return afi === 'v6' ? C.dn_v6 : C.dn_v4
  const isBr = meta[String(d.asn)]?.is_br === true
  return isBr ? (afi === 'v6' ? C.up_br_v6 : C.up_br_v4) : C.up_intl
}

interface Props {
  cdnAsns: number[]
  docs: ASNDocument[]
  afi: 'v4' | 'v6'
  onAsnClick?: (asn: number) => void
  width?: number
  height?: number
  maxUp?: number
  maxDown?: number
}

export function CDNRelationsGraph({
  cdnAsns,
  docs,
  afi,
  onAsnClick,
  width = 620,
  height = 420,
  maxUp = 50,
  maxDown = 20,
}: Props) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return
    d3.select(svg).selectAll('*').remove()

    const cdnSet = new Set(cdnAsns)

    // Mescla nodeMeta de todos os docs
    const meta: Record<string, NodeMeta> = {}
    for (const d of docs) {
      if (d.path_node_meta) Object.assign(meta, d.path_node_meta)
      meta[String(d.asn)] = { name: d.name, is_br: d.is_br }
    }

    const spaceOf = (asn: number) =>
      afi === 'v4' ? (meta[String(asn)]?.space_v4 ?? 0) : (meta[String(asn)]?.space_v6 ?? 0)

    // Para cada vizinho não-CDN, registra em quais main ASNs ele se conecta
    const upLinks  = new Map<number, Set<number>>() // vizinhoASN → Set<mainASN>
    const dnLinks  = new Map<number, Set<number>>()

    for (const d of docs) {
      const upsIxp    = (afi === 'v4' ? d.upstreams_v4        : d.upstreams_v6)        ?? []
      const upsGlobal = (afi === 'v4' ? d.upstreams_global_v4 : d.upstreams_global_v6) ?? []
      const dnsGlobal = (afi === 'v4' ? d.downstreams_global_v4: d.downstreams_global_v6) ?? []

      const allUps = new Set([...upsIxp, ...upsGlobal].filter(a => !cdnSet.has(a)))
      const allDns = new Set(dnsGlobal.filter(a => !cdnSet.has(a)))

      for (const asn of allUps) {
        const s = upLinks.get(asn) ?? new Set<number>(); s.add(d.asn); upLinks.set(asn, s)
      }
      for (const asn of allDns) {
        const s = dnLinks.get(asn) ?? new Set<number>(); s.add(d.asn); dnLinks.set(asn, s)
      }
    }

    const allUpsArr = [...upLinks.keys()].sort((a, b) => spaceOf(b) - spaceOf(a))
    const allDnsArr = [...dnLinks.keys()].sort((a, b) => spaceOf(b) - spaceOf(a))

    if (allUpsArr.length === 0 && allDnsArr.length === 0) {
      d3.select(svg).append('text')
        .attr('x', width / 2).attr('y', height / 2)
        .attr('text-anchor', 'middle').attr('fill', '#94a3b8').attr('font-size', 13)
        .text(`Nenhuma relação ${afi === 'v6' ? 'IPv6' : 'IPv4'} inferida`)
      return
    }

    const displayDns = allDnsArr.slice(0, maxDown)
    const dnOverflow = allDnsArr.length - displayDns.length
    const dnTotalBr  = allDnsArr.filter(a => meta[String(a)]?.is_br === true).length

    const displayUps = allUpsArr.slice(0, maxUp)
    const upOverflow = allUpsArr.length - displayUps.length
    const upTotalBr  = allUpsArr.filter(a => meta[String(a)]?.is_br === true).length

    const PAD = 36
    const nMain = cdnAsns.length
    const spacing = Math.min(90, (width - 2 * PAD) / Math.max(nMain, 1))
    const startX  = width / 2 - ((nMain - 1) * spacing) / 2

    const nodes: GNode[] = cdnAsns.map((asn, i) => ({
      id: `main-${asn}`, type: 'main', label: `AS${asn}`, asn, _r: 14,
      fx: nMain === 1 ? width / 2 : startX + i * spacing,
      fy: height / 2,
    }))
    const links: GLink[] = []

    for (const asn of displayUps) {
      const id = `up-${asn}`
      nodes.push({ id, type: 'upstream', label: `AS${asn}`, asn, _r: 9 })
      for (const mainAsn of (upLinks.get(asn) ?? [])) {
        links.push({ source: id, target: `main-${mainAsn}`, dir: 'up' })
      }
    }
    if (upOverflow > 0) {
      nodes.push({
        id: 'overflow-up', type: 'overflow_up', label: `+${upOverflow} provedores`,
        asn: -1, _r: 16, overflowTotal: allUpsArr.length, overflowBr: upTotalBr,
      })
      links.push({ source: 'overflow-up', target: `main-${cdnAsns[0]}`, dir: 'up' })
    }

    for (const asn of displayDns) {
      const id = `dn-${asn}`
      nodes.push({ id, type: 'downstream', label: `AS${asn}`, asn, _r: 9 })
      for (const mainAsn of (dnLinks.get(asn) ?? [])) {
        links.push({ source: `main-${mainAsn}`, target: id, dir: 'down' })
      }
    }
    if (dnOverflow > 0) {
      nodes.push({
        id: 'overflow-dn', type: 'overflow_dn', label: `+${dnOverflow} clientes`,
        asn: -2, _r: 16, overflowTotal: allDnsArr.length, overflowBr: dnTotalBr,
      })
      links.push({ source: `main-${cdnAsns[0]}`, target: 'overflow-dn', dir: 'down' })
    }

    // Tooltip DOM
    let tip = document.getElementById('cdn-rel-tip') as HTMLDivElement | null
    if (!tip) {
      tip = document.createElement('div')
      tip.id = 'cdn-rel-tip'
      document.body.appendChild(tip)
    }
    Object.assign(tip.style, {
      position: 'fixed', pointerEvents: 'none', display: 'none',
      background: 'white', border: '1px solid #e5e7eb', borderRadius: '6px',
      padding: '6px 10px', fontSize: '11px', lineHeight: '1.5', color: '#374151',
      boxShadow: '0 2px 8px rgba(0,0,0,.12)', maxWidth: '240px', zIndex: '9999',
    })

    const root = d3.select(svg)
    const defs = root.append('defs')
    ;(['up', 'down'] as const).forEach(t => {
      defs.append('marker').attr('id', `cdnr-arr-${t}`)
        .attr('viewBox', '0 -5 10 10').attr('refX', 18).attr('refY', 0)
        .attr('markerWidth', 5).attr('markerHeight', 5).attr('orient', 'auto')
        .append('path').attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', t === 'up' ? C.e_up : C.e_dn)
    })

    const g = root.append('g')

    const simulation = d3.forceSimulation<GNode>(nodes)
      .force('link', d3.forceLink<GNode, GLink>(links).id(d => d.id).distance(60))
      .force('charge', d3.forceManyBody().strength(-49))
      .force('collision', d3.forceCollide<GNode>(d => d._r + 11))
      .force('y', d3.forceY<GNode>(d => {
        if (d.type === 'upstream'   || d.type === 'overflow_up') return height * 0.17
        if (d.type === 'main')                                    return height * 0.5
        return height * 0.83
      }).strength(0.14))
      .force('x', d3.forceX(width / 2).strength(0.02))

    const link = g.append('g').selectAll<SVGLineElement, GLink>('line')
      .data(links).join('line')
      .attr('stroke', d => d.dir === 'up' ? C.e_up : C.e_dn)
      .attr('stroke-width', 1.5).attr('stroke-opacity', 0.45)
      .attr('marker-end', d => `url(#cdnr-arr-${d.dir})`)

    const drag = d3.drag<SVGGElement, GNode>()
      .on('start', (ev, d) => { if (!ev.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
      .on('drag',  (ev, d) => { d.fx = ev.x; d.fy = ev.y })
      .on('end',   (ev, d) => {
        if (!ev.active) simulation.alphaTarget(0)
        if (d.type !== 'main') { d.fx = null; d.fy = null }
      })

    const node = g.append('g').selectAll<SVGGElement, GNode>('g')
      .data(nodes).join('g')
      .style('cursor', d => (d.type === 'upstream' || d.type === 'downstream') ? 'pointer' : 'default')
      .call(drag)

    node.append('circle')
      .attr('r', d => d._r)
      .attr('fill', d => nodeColor(d, afi, meta))
      .attr('stroke', 'white').attr('stroke-width', 2)

    node.each(function(d) {
      const sel = d3.select(this)
      if (d.type === 'overflow_dn' || d.type === 'overflow_up') {
        const parts = d.label.split(' ')
        const t = sel.append('text').attr('text-anchor', 'middle').attr('font-size', 8).attr('fill', '#374151')
        t.append('tspan').attr('x', 0).attr('dy', d._r + 10).text(parts[0])
        t.append('tspan').attr('x', 0).attr('dy', 11).text(parts.slice(1).join(' '))
      } else {
        sel.append('text')
          .attr('dy', d._r + 11).attr('text-anchor', 'middle')
          .attr('font-size', d.type === 'main' ? 11 : 9)
          .attr('font-weight', d.type === 'main' ? '700' : 'normal')
          .attr('fill', '#374151').text(d.label)
      }
    })

    node.on('click', (_e, d) => {
      if (d.type === 'upstream' || d.type === 'downstream') onAsnClick?.(d.asn)
    })

    node.filter(d => d.type !== 'main')
      .on('mouseover', function(event, d) {
        let html = ''
        if (d.type === 'overflow_dn') {
          const total = d.overflowTotal ?? 0, br = d.overflowBr ?? 0
          html = `<div style="font-weight:600">Demais clientes</div>`
          html += `<div style="margin-top:3px">Total de <b>${escapar(total)}</b> ${escapar(afi === 'v6' ? 'IPv6' : 'IPv4')}</div>`
          html += `<div>${escapar(br)} nacionais &nbsp;·&nbsp; ${escapar(total - br)} internacionais</div>`
        } else if (d.type === 'overflow_up') {
          const total = d.overflowTotal ?? 0, br = d.overflowBr ?? 0
          html = `<div style="font-weight:600">Demais provedores</div>`
          html += `<div style="margin-top:3px">Total de <b>${escapar(total)}</b> upstream${escapar(total !== 1 ? 's' : '')}</div>`
          html += `<div>${escapar(br)} nacionais &nbsp;·&nbsp; ${escapar(total - br)} internacionais</div>`
        } else {
          const m = meta[String(d.asn)]
          html = `<div style="font-weight:600">AS${escapar(d.asn)}</div>`
          if (m?.name) html += `<div>${escapar(m.name)}</div>`
          if (m?.is_br === false) html += `<div style="color:#8b5cf6;font-size:10px">internacional</div>`
          else if (m?.is_br === true) html += `<div style="color:#374151;font-size:10px">nacional</div>`
          html += `<div style="color:#6b7280;font-size:10px">${escapar(d.type === 'downstream' ? 'cliente' : 'upstream')}</div>`
          const sp = afi === 'v4' ? m?.space_v4 : m?.space_v6
          if (sp) html += `<div style="color:#6b7280;font-size:10px">${escapar(sp.toLocaleString('pt-BR'))} /${escapar(afi === 'v4' ? '24' : '48')}s</div>`
        }
        tip!.innerHTML = html
        tip!.style.display = 'block'
        tip!.style.left = `${event.clientX + 14}px`
        tip!.style.top  = `${event.clientY - 10}px`
      })
      .on('mousemove', function(event) {
        tip!.style.left = `${event.clientX + 14}px`
        tip!.style.top  = `${event.clientY - 10}px`
      })
      .on('mouseout', () => { tip!.style.display = 'none' })

    simulation.on('tick', () => {
      for (const d of nodes) {
        if (d.type !== 'main') {
          d.x = Math.max(PAD + d._r, Math.min(width  - PAD - d._r, d.x ?? width / 2))
          d.y = Math.max(PAD + d._r, Math.min(height - PAD - d._r, d.y ?? height / 2))
        }
      }
      link
        .attr('x1', d => (d.source as GNode).x!)
        .attr('y1', d => (d.source as GNode).y!)
        .attr('x2', d => (d.target as GNode).x!)
        .attr('y2', d => (d.target as GNode).y!)
      node.attr('transform', d => `translate(${d.x},${d.y})`)
    })

    return () => {
      simulation.stop()
      tip!.style.display = 'none'
    }
  }, [cdnAsns, docs, afi, width, height, maxUp, maxDown, onAsnClick])

  const legendItems = afi === 'v4'
    ? [
        { color: C.up_br_v4,       label: 'Upstream nacional IPv4' },
        { color: C.up_intl,        label: 'Upstream internacional' },
        { color: C.dn_v4,          label: 'Clientes IPv4' },
        { color: C.overflow_dn_v4, label: '+N clientes' },
      ]
    : [
        { color: C.up_br_v6,       label: 'Upstream nacional IPv6' },
        { color: C.up_intl,        label: 'Upstream internacional' },
        { color: C.dn_v6,          label: 'Clientes IPv6' },
        { color: C.overflow_dn_v6, label: '+N clientes' },
      ]

  return (
    <div style={{ position: 'relative' }}>
      <svg ref={svgRef} width={width} height={height} className="rounded border border-gray-100 w-full" />
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-gray-500 justify-center">
        {legendItems.map(({ color, label }) => (
          <span key={label} className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full inline-block flex-shrink-0" style={{ background: color }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}
