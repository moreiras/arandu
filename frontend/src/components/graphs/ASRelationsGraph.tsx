/**
 * ASRelationsGraph — grafo hierárquico de relações BGP inferidas.
 *
 * Layout: Upstreams (topo) → ASN principal (centro) → Downstreams (base)
 * Upstreams = união IXP ∪ RouteViews, top-50 por espaço de endereçamento global
 * Downstreams = apenas RouteViews global (IXP-only é ruidoso para downstream)
 * Se houver mais que o limite, exibe nó "+N" com contagem total BR/internacional
 */
import { escapar } from '../../lib/html'
import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

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

const C = {
  main:           '#1d4ed8',
  up_br_v4:       '#93c5fd',   // upstream nacional IPv4
  up_br_v6:       '#fb923c',   // upstream nacional IPv6
  up_intl:        '#8b5cf6',   // upstream internacional
  dn_v4:          '#86efac',   // cliente IPv4
  dn_v6:          '#fbbf24',   // cliente IPv6
  e_up:           '#fca5a5',
  e_dn:           '#6ee7b7',
  overflow_dn_v4: '#bbf7d0',   // verde mais claro (overflow clientes IPv4)
  overflow_dn_v6: '#fef08a',   // amarelo mais claro (overflow clientes IPv6)
  overflow_up:    '#ddd6fe',   // violeta mais claro (overflow provedores)
}

function getNodeColor(d: GNode, afi: 'v4' | 'v6', nodeMeta: Record<string, NodeMeta>): string {
  if (d.type === 'main') return C.main
  if (d.type === 'overflow_dn') return afi === 'v6' ? C.overflow_dn_v6 : C.overflow_dn_v4
  if (d.type === 'overflow_up') return C.overflow_up
  if (d.type === 'downstream') return afi === 'v6' ? C.dn_v6 : C.dn_v4
  const isBr = nodeMeta[String(d.asn)]?.is_br === true
  if (isBr) return afi === 'v6' ? C.up_br_v6 : C.up_br_v4
  return C.up_intl
}

interface NodeMeta {
  name?: string
  is_br?: boolean
  space_v4?: number   // equivalentes /24
  space_v6?: number   // equivalentes /48
}

interface Props {
  mainAsn: number
  afi: 'v4' | 'v6'
  upsIxp: number[]
  dnsIxp: number[]
  upsGlobal: number[]
  dnsGlobal: number[]
  nodeMeta?: Record<string, NodeMeta>
  onAsnClick?: (asn: number) => void
  width?: number
  height?: number
  maxUp?: number
  maxDown?: number
  /** Texto quando não há vizinho nem relação para desenhar. */
  textoVazio?: string
}

export function ASRelationsGraph({
  mainAsn,
  afi,
  upsIxp,
  dnsIxp,
  upsGlobal,
  dnsGlobal,
  nodeMeta = {},
  onAsnClick,
  width = 520,
  height = 380,
  maxUp = 50,
  maxDown = 20,
  textoVazio,
}: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const svg = svgRef.current
    const container = containerRef.current
    if (!svg || !container) return
    d3.select(svg).selectAll('*').remove()

    const spaceOf = (asn: number) =>
      afi === 'v4'
        ? (nodeMeta[String(asn)]?.space_v4 ?? 0)
        : (nodeMeta[String(asn)]?.space_v6 ?? 0)

    // Upstreams = união IXP ∪ RV (excluindo self-loops), ordenado por espaço desc
    const allUpsArr = Array.from(
      new Set([...upsIxp, ...upsGlobal].filter(a => a !== mainAsn))
    ).sort((a, b) => spaceOf(b) - spaceOf(a))

    // Downstreams = apenas tabela global (RouteViews). IXP-only é ruidoso para
    // downstream: aparência no AS_PATH do IXP pode ser peering, não cliente.
    const allDnsArr = Array.from(
      new Set(dnsGlobal.filter(a => a !== mainAsn))
    ).sort((a, b) => spaceOf(b) - spaceOf(a))

    if (allUpsArr.length === 0 && allDnsArr.length === 0) {
      d3.select(svg).append('text')
        .attr('x', width / 2).attr('y', height / 2)
        .attr('text-anchor', 'middle').attr('fill', '#94a3b8').attr('font-size', 13)
        .text(textoVazio ?? `Nenhum vizinho ${afi === 'v6' ? 'IPv6' : 'IPv4'} observado`)
      return
    }

    // Overflow downstream
    const displayDns = allDnsArr.slice(0, maxDown)
    const dnOverflow = allDnsArr.length - displayDns.length
    const dnTotalBr = allDnsArr.filter(a => nodeMeta[String(a)]?.is_br === true).length

    // Overflow upstream
    const displayUps = allUpsArr.slice(0, maxUp)
    const upOverflow = allUpsArr.length - displayUps.length
    const upTotalBr = allUpsArr.filter(a => nodeMeta[String(a)]?.is_br === true).length

    const PAD = 36

    const nodes: GNode[] = [{
      id: 'main', type: 'main', label: `AS${mainAsn}`, asn: mainAsn,
      _r: 14, fx: width / 2, fy: height / 2,
    }]
    const links: GLink[] = []

    for (const asn of displayUps) {
      const id = `up-${asn}`
      nodes.push({ id, type: 'upstream', label: `AS${asn}`, asn, _r: 9 })
      links.push({ source: id, target: 'main', dir: 'up' })
    }
    if (upOverflow > 0) {
      nodes.push({
        id: 'overflow-up',
        type: 'overflow_up',
        label: `+${upOverflow} a montante`,
        asn: -1,
        _r: 16,
        overflowTotal: allUpsArr.length,
        overflowBr: upTotalBr,
      })
      links.push({ source: 'overflow-up', target: 'main', dir: 'up' })
    }

    for (const asn of displayDns) {
      const id = `dn-${asn}`
      nodes.push({ id, type: 'downstream', label: `AS${asn}`, asn, _r: 9 })
      links.push({ source: 'main', target: id, dir: 'down' })
    }
    if (dnOverflow > 0) {
      nodes.push({
        id: 'overflow-dn',
        type: 'overflow_dn',
        label: `+${dnOverflow} a jusante`,
        asn: -2,
        _r: 16,
        overflowTotal: allDnsArr.length,
        overflowBr: dnTotalBr,
      })
      links.push({ source: 'main', target: 'overflow-dn', dir: 'down' })
    }

    // ── Tooltip (DOM puro — evita incompatibilidade de tipos d3.Selection) ──
    let tip = document.getElementById('asrel-tooltip') as HTMLDivElement | null
    if (!tip) {
      tip = document.createElement('div')
      tip.id = 'asrel-tooltip'
      document.body.appendChild(tip)
    }
    Object.assign(tip.style, {
      position: 'fixed',
      pointerEvents: 'none',
      display: 'none',
      background: 'white',
      border: '1px solid #e5e7eb',
      borderRadius: '6px',
      padding: '6px 10px',
      fontSize: '11px',
      lineHeight: '1.5',
      color: '#374151',
      boxShadow: '0 2px 8px rgba(0,0,0,.12)',
      maxWidth: '240px',
      zIndex: '9999',
    })

    const root = d3.select(svg)
    const defs = root.append('defs')
    ;(['up', 'down'] as const).forEach(t => {
      defs.append('marker').attr('id', `rel-arr-${t}`)
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
        if (d.type === 'upstream' || d.type === 'overflow_up')   return height * 0.17
        if (d.type === 'main')                                    return height * 0.5
        return height * 0.83
      }).strength(0.14))
      .force('x', d3.forceX(width / 2).strength(0.02))

    const link = g.append('g').selectAll<SVGLineElement, GLink>('line')
      .data(links).join('line')
      .attr('stroke', d => d.dir === 'up' ? C.e_up : C.e_dn)
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.45)
      .attr('marker-end', d => `url(#rel-arr-${d.dir})`)

    const drag = d3.drag<SVGGElement, GNode>()
      .on('start', (ev, d) => {
        if (!ev.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x; d.fy = d.y
      })
      .on('drag', (ev, d) => { d.fx = ev.x; d.fy = ev.y })
      .on('end', (ev, d) => {
        if (!ev.active) simulation.alphaTarget(0)
        if (d.type !== 'main') { d.fx = null; d.fy = null }
      })

    const node = g.append('g').selectAll<SVGGElement, GNode>('g')
      .data(nodes).join('g')
      .style('cursor', d => (d.type === 'upstream' || d.type === 'downstream') ? 'pointer' : 'default')
      .call(drag)

    node.append('circle')
      .attr('r', d => d._r)
      .attr('fill', d => getNodeColor(d, afi, nodeMeta))
      .attr('stroke', 'white')
      .attr('stroke-width', 2)

    // Label: overflow nodes usam fonte menor e texto em duas linhas via tspan
    node.each(function (d) {
      const sel = d3.select(this)
      if (d.type === 'overflow_dn' || d.type === 'overflow_up') {
        const parts = d.label.split(' ')
        const t = sel.append('text')
          .attr('text-anchor', 'middle')
          .attr('font-size', 8)
          .attr('fill', '#374151')
        t.append('tspan')
          .attr('x', 0).attr('dy', d._r + 10)
          .text(parts[0])          // "+N"
        t.append('tspan')
          .attr('x', 0).attr('dy', 11)
          .text(parts.slice(1).join(' ')) // "a montante" / "a jusante"
      } else {
        sel.append('text')
          .attr('dy', d._r + 11)
          .attr('text-anchor', 'middle')
          .attr('font-size', d.type === 'main' ? 11 : 9)
          .attr('font-weight', d.type === 'main' ? '700' : 'normal')
          .attr('fill', '#374151')
          .text(d.label)
      }
    })

    // ── Click: navegar para AS (só nós regulares) ─────────────────────────
    node.on('click', (_e, d) => {
      if (d.type === 'upstream' || d.type === 'downstream') onAsnClick?.(d.asn)
    })

    // ── Tooltip ───────────────────────────────────────────────────────────
    node.filter(d => d.type !== 'main')
      .on('mouseover', function (event, d) {
        let html = ''
        if (d.type === 'overflow_dn') {
          const total = d.overflowTotal ?? 0
          const br = d.overflowBr ?? 0
          const intl = total - br
          html = `<div style="font-weight:600">Demais clientes</div>`
          html += `<div style="margin-top:3px">Total de <b>${escapar(total)}</b> ${escapar(afi === 'v6' ? 'IPv6' : 'IPv4')}</div>`
          html += `<div>${escapar(br)} nacionais &nbsp;·&nbsp; ${escapar(intl)} internacionais</div>`
        } else if (d.type === 'overflow_up') {
          const total = d.overflowTotal ?? 0
          const br = d.overflowBr ?? 0
          const intl = total - br
          html = `<div style="font-weight:600">Demais provedores</div>`
          html += `<div style="margin-top:3px">Total de <b>${escapar(total)}</b> upstream${escapar(total !== 1 ? 's' : '')}</div>`
          html += `<div>${escapar(br)} nacionais &nbsp;·&nbsp; ${escapar(intl)} internacionais</div>`
        } else {
          const meta = nodeMeta[String(d.asn)]
          html = `<div style="font-weight:600">AS${escapar(d.asn)}</div>`
          if (meta?.name) html += `<div>${escapar(meta.name)}</div>`
          if (meta?.is_br === false) {
            html += `<div style="color:#8b5cf6;font-size:10px">internacional</div>`
          } else if (meta?.is_br === true) {
            html += `<div style="color:#374151;font-size:10px">nacional</div>`
          }
          html += `<div style="color:#6b7280;font-size:10px">${escapar(d.type === 'downstream' ? 'cliente' : 'upstream')}</div>`
          const sp = afi === 'v4' ? meta?.space_v4 : meta?.space_v6
          if (sp) {
            html += `<div style="color:#6b7280;font-size:10px">${escapar(sp.toLocaleString('pt-BR'))} /${escapar(afi === 'v4' ? '24' : '48')}s</div>`
          }
        }
        tip.innerHTML = html
        tip.style.display = 'block'
        tip.style.left = `${event.clientX + 14}px`
        tip.style.top  = `${event.clientY - 10}px`
      })
      .on('mousemove', function (event) {
        tip.style.left = `${event.clientX + 14}px`
        tip.style.top  = `${event.clientY - 10}px`
      })
      .on('mouseout', () => { tip.style.display = 'none' })

    // ── Tick ──────────────────────────────────────────────────────────────
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
      tip.style.display = 'none'
    }
  }, [mainAsn, afi, upsIxp, dnsIxp, upsGlobal, dnsGlobal, nodeMeta, width, height, maxUp, maxDown, onAsnClick, textoVazio])

  const legendItems = afi === 'v4'
    ? [
        { color: C.up_br_v4,       label: 'Upstream nacional IPv4' },
        { color: C.up_intl,        label: 'Upstream internacional' },
        { color: C.dn_v4,          label: 'Clientes IPv4' },
        { color: C.overflow_dn_v4, label: `+N clientes` },
      ]
    : [
        { color: C.up_br_v6,       label: 'Upstream nacional IPv6' },
        { color: C.up_intl,        label: 'Upstream internacional' },
        { color: C.dn_v6,          label: 'Clientes IPv6' },
        { color: C.overflow_dn_v6, label: `+N clientes` },
      ]

  return (
    <div ref={containerRef} style={{ position: 'relative', display: 'inline-block' }}>
      <svg ref={svgRef} width={width} height={height} className="rounded border border-gray-100" />
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
