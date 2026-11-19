/**
 * Grafo de presença em IXPs — filtrado por AFI (v4 ou v6).
 *
 * Nós:
 *   main        — ASN principal (azul)
 *   ixp_direct  — IXP com peering direto E prefixos próprios (laranja=v6 / azul claro=v4)
 *   ixp_origin  — IXP só origem com prefixos (cinza alaranjado=v6 / cinza azulado=v4)
 *   path        — AS intermediário no AS_PATH (verde=BR, violeta=não-BR)
 *   ixp_member  — IXP onde o AS é membro mas sem prefixos anunciados (vermelho)
 *
 * Hover sobre nós path: tooltip mostrando prefixos do AS principal em cada PTT bridgeado.
 * Hover sobre nós IXP: tooltip com prefixos do AS principal naquele IXP e % do alocado.
 */
import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import type { IXPPresence, IXPPeerStats, PathNodeMeta } from '../../types/api'

interface GNode extends d3.SimulationNodeDatum {
  id: string
  type: 'main' | 'ixp_direct' | 'ixp_origin' | 'path' | 'ixp_member'
  label: string
  asnId?: number
  ixpCode?: string
  _r: number
  _isBr?: boolean
}

interface GLink extends d3.SimulationLinkDatum<GNode> {
  style: 'direct' | 'path-chain' | 'origin-unknown' | 'member'
}

// Colors per AFI
const CV6 = {
  ixp_direct:  '#f97316',   // amber-orange (clearly distinct from red)
  ixp_origin:  '#d4a76a',   // grayish amber-orange
  e_direct:    '#f97316',
}
const CV4 = {
  ixp_direct:  '#38bdf8',   // light blue
  ixp_origin:  '#7fb5d4',   // grayish-blue
  e_direct:    '#38bdf8',
}
const C = {
  main:       '#1d4ed8',
  path_br:    '#16a34a',
  path_nonbr: '#7c3aed',
  path_unk:   '#6b7280',
  ixp_member: '#dc2626',    // red
  e_path:     '#6b7280',
  e_unknown:  '#d1d5db',
  e_member:   '#dc2626',
}

interface Props {
  mainAsn: number
  afi: 'v4' | 'v6'
  mainAsnRirPrefixes: string[]
  ixpPresence: Record<string, IXPPresence>
  ixpPaths: Record<string, number[][]>
  pathNodeMeta: Record<string, PathNodeMeta>
  ixpMemberCodes?: string[]
  ixpPeerStats?: Record<string, { v4?: IXPPeerStats; v6?: IXPPeerStats }>
  onIxpClick?: (code: string) => void
  onBridgeClick?: (asn: number) => void
  width?: number
  height?: number
  maxOrigin?: number
}

function parseV4(p: string): { addr: number; len: number } | null {
  const [host, lenStr] = p.split('/')
  if (!host || !lenStr) return null
  const len = parseInt(lenStr, 10)
  if (isNaN(len) || len < 0 || len > 32) return null
  const parts = host.split('.').map(Number)
  if (parts.length !== 4 || parts.some(n => isNaN(n))) return null
  const addr = ((parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]) >>> 0
  return { addr, len }
}

function isV4Subnet(child: { addr: number; len: number }, parent: { addr: number; len: number }): boolean {
  if (child.len < parent.len) return false
  const mask = parent.len === 0 ? 0 : (~0 << (32 - parent.len)) >>> 0
  return (child.addr & mask) === (parent.addr & mask)
}

// Unique /24 blocks covered by ixpPrefixes that are subnets of rirPrefixes.
// Uses a Set of /24 base addresses to avoid double-counting when both a supernet
// and its more-specific subnets are announced at the same IXP.
function coveredSpace24(ixpPrefixes: string[], rirPrefixes: string[]): number {
  const rirNets = rirPrefixes.map(parseV4).filter(Boolean) as { addr: number; len: number }[]
  const covered = new Set<number>()
  for (const p of ixpPrefixes) {
    const net = parseV4(p)
    if (!net || !rirNets.some(r => isV4Subnet(net, r))) continue
    const numBlocks = net.len >= 24 ? 1 : 1 << (24 - net.len)
    const base = net.addr >>> 8
    for (let i = 0; i < numBlocks; i++) covered.add(base + i)
  }
  return covered.size
}

// Unique /48 blocks covered — uses BigInt for correct 128-bit IPv6 parsing.
function parseV6(p: string): { addr: bigint; len: number } | null {
  const [host, lenStr] = p.split('/')
  if (!host || !lenStr) return null
  const len = parseInt(lenStr, 10)
  if (isNaN(len) || len < 0 || len > 128) return null
  try {
    // Expand IPv6 address to 128-bit integer via a canonical trick
    const groups = expandV6(host)
    if (!groups) return null
    let addr = 0n
    for (const g of groups) addr = (addr << 16n) | BigInt(parseInt(g, 16))
    return { addr, len }
  } catch { return null }
}

function expandV6(host: string): string[] | null {
  const halves = host.split('::')
  if (halves.length > 2) return null
  const left = halves[0] ? halves[0].split(':') : []
  const right = halves[1] ? halves[1].split(':') : []
  const missing = 8 - left.length - right.length
  if (missing < 0) return null
  return [...left, ...Array(missing).fill('0'), ...right]
}

function isV6Subnet(child: { addr: bigint; len: number }, parent: { addr: bigint; len: number }): boolean {
  if (child.len < parent.len) return false
  if (parent.len === 0) return true
  const mask = (~0n) << BigInt(128 - parent.len)
  return (child.addr & mask) === (parent.addr & mask)
}

function coveredSpace48(ixpPrefixes: string[], rirPrefixes: string[]): number {
  const rirNets = rirPrefixes.map(parseV6).filter(Boolean) as { addr: bigint; len: number }[]
  const covered = new Set<bigint>()  // /48 base addresses
  let directSum = 0                  // for prefixes shorter than /32 (>65536 blocks)
  for (const p of ixpPrefixes) {
    const net = parseV6(p)
    if (!net || !rirNets.some(r => isV6Subnet(net, r))) continue
    if (net.len >= 32) {
      // Enumerate /48 blocks — max 65536 per prefix
      const numBlocks = net.len >= 48 ? 1 : 1 << (48 - net.len)
      const base = net.addr >> BigInt(128 - 48)
      for (let i = 0; i < numBlocks; i++) covered.add(base + BigInt(i))
    } else {
      // Large block: too many /48s to enumerate; count directly.
      // Overlaps at this scale are extremely unlikely for a single ASN.
      directSum += Math.pow(2, 48 - net.len)
    }
  }
  return covered.size + directSum
}

function space24(prefixes: string[]): number {
  return prefixes.reduce((sum, p) => {
    const len = parseInt(p.split('/')[1] ?? '32', 10)
    return sum + Math.pow(2, Math.max(0, 24 - len))
  }, 0)
}

function space48(prefixes: string[]): number {
  return prefixes.reduce((sum, p) => {
    const len = parseInt(p.split('/')[1] ?? '128', 10)
    return sum + Math.pow(2, Math.max(0, 48 - len))
  }, 0)
}

function buildIxpTooltipHtml(
  code: string,
  ixpPrefixes: string[],
  rirPrefixes: string[],
  afi: 'v4' | 'v6',
  peerStat?: IXPPeerStats,
  isMember?: boolean,
): string {
  const rirSpace = afi === 'v4' ? space24(rirPrefixes) : space48(rirPrefixes)
  const covered  = afi === 'v4' ? coveredSpace24(ixpPrefixes, rirPrefixes)
                                 : coveredSpace48(ixpPrefixes, rirPrefixes)
  const pct = rirSpace > 0 ? (covered / rirSpace * 100).toFixed(1) : null
  const label = afi === 'v6' ? 'IPv6' : 'IPv4'
  const unit  = afi === 'v4' ? '/24' : '/48'

  let html = `<div style="font-weight:600;margin-bottom:4px">${code.toUpperCase()}`
  if (isMember) html += ` <span style="font-size:10px;font-weight:400;background:#fee2e2;color:#dc2626;border-radius:3px;padding:1px 4px">membro registrado</span>`
  html += `</div>`

  if (peerStat) {
    const totalSpace = (peerStat.own_space_24 ?? 0) + (peerStat.third_space_24 ?? 0)
    const origins    = peerStat.origin_asns ?? 0
    if (origins > 0 || totalSpace > 0) {
      html += `<div style="margin-top:3px;color:#374151;font-size:10px">`
      if (origins > 0) html += `${origins} AS originadores ${label}`
      if (origins > 0 && totalSpace > 0) html += ` · `
      if (totalSpace > 0) html += `${Math.round(totalSpace).toLocaleString()} ${unit}s`
      html += `</div>`
    }
  }

  if (ixpPrefixes.length === 0) {
    html += `<div style="opacity:.5;margin-top:4px">sem prefixos ${label} deste AS</div>`
  } else {
    html += `<div style="margin-top:4px;border-top:1px solid #f3f4f6;padding-top:4px">${label} deste AS: `
    if (ixpPrefixes.length <= 10) {
      html += ixpPrefixes.map(p => `<code style="background:#f3f4f6;padding:0 2px;border-radius:2px">${p}</code>`).join(', ')
    } else {
      html += `${ixpPrefixes.length} prefixos`
    }
    html += `</div>`
    if (pct != null) {
      html += `<div style="opacity:.65;margin-top:3px">${pct}% do espaço alocado</div>`
    }
  }
  return html
}

function buildPathNodeTooltipHtml(
  asnId: number,
  meta: PathNodeMeta | undefined,
  bridgedIxps: string[],
  ixpPresence: Record<string, IXPPresence>,
  afi: 'v4' | 'v6',
): string {
  const name = meta?.name ?? ''
  const brLabel = meta?.is_br ? 'BR' : 'não-BR'
  let html = `<div style="font-weight:600;margin-bottom:4px">AS${asnId}${name ? ` — ${name}` : ''} <span style="opacity:.7;font-weight:400">(${brLabel})</span></div>`

  const sorted = [...bridgedIxps].sort()
  for (const code of sorted) {
    const prefixes = ixpPresence[code]?.[afi]?.prefixes ?? []
    html += `<div style="margin-top:5px;border-top:1px solid #e5e7eb;padding-top:4px"><strong>${code.toUpperCase()}</strong>: `
    if (prefixes.length === 0) {
      html += `<span style="opacity:.5">sem prefixos</span>`
    } else if (prefixes.length <= 10) {
      html += prefixes.map(p =>
        `<code style="background:#f3f4f6;padding:0 2px;border-radius:2px">${p}</code>`
      ).join(', ')
    } else {
      html += `${prefixes.length} prefixos`
    }
    html += `</div>`
  }
  return html
}

export function IXPPresenceGraph({
  mainAsn,
  afi,
  mainAsnRirPrefixes,
  ixpPresence,
  ixpPaths,
  pathNodeMeta,
  ixpMemberCodes = [],
  ixpPeerStats,
  onIxpClick,
  onBridgeClick,
  width = 560,
  height = 420,
  maxOrigin = 30,
}: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const svg = svgRef.current
    const container = containerRef.current
    if (!svg || !container) return
    d3.select(svg).selectAll('*').remove()

    const PAD = 30
    const AC = afi === 'v6' ? CV6 : CV4

    // ── Tooltip div ──────────────────────────────────────────────────────
    const tip = d3.select(container)
      .selectAll<HTMLDivElement, unknown>('.ixp-tooltip')
      .data([null])
      .join('div')
      .attr('class', 'ixp-tooltip')
      .style('position', 'absolute')
      .style('pointer-events', 'none')
      .style('display', 'none')
      .style('background', 'white')
      .style('border', '1px solid #e5e7eb')
      .style('border-radius', '6px')
      .style('padding', '8px 10px')
      .style('font-size', '11px')
      .style('line-height', '1.5')
      .style('color', '#374151')
      .style('box-shadow', '0 2px 8px rgba(0,0,0,.12)')
      .style('max-width', '300px')
      .style('z-index', '10')

    // ── Track which IXPs each path ASN bridges (for tooltip) ─────────────
    const pathAsnIxps: Record<number, string[]> = {}
    for (const [code, paths] of Object.entries(ixpPaths)) {
      for (const path of paths) {
        for (const asnId of path) {
          ;(pathAsnIxps[asnId] ??= []).push(code)
        }
      }
    }
    for (const k of Object.keys(pathAsnIxps)) {
      pathAsnIxps[+k] = [...new Set(pathAsnIxps[+k])]
    }

    // ── Build nodes and links ─────────────────────────────────────────────
    const nodes: GNode[] = [{ id: 'main', type: 'main', label: `AS${mainAsn}`, _r: 14 }]
    const links: GLink[] = []
    const seenNodes = new Set<string>(['main'])
    const shownIxps = new Set<string>()  // IXPs shown as direct/origin/member
    const memberSet = new Set<string>(ixpMemberCodes)
    let originSeen = 0

    const entries = Object.entries(ixpPresence)
    entries.sort(([, a], [, b]) => {
      const ad = a[afi]?.direct ? 1 : 0
      const bd = b[afi]?.direct ? 1 : 0
      return bd - ad
    })

    for (const [code, presence] of entries) {
      const afiPres = presence[afi]
      if (!afiPres) continue
      // Only show routing presence if there are actual prefixes announced
      if ((afiPres.prefixes?.length ?? 0) === 0) continue

      const isDirect = afiPres.direct
      const isOrigin = afiPres.origin && !isDirect
      const isMember = memberSet.has(code)

      if (!isDirect && !isOrigin) continue
      if (isOrigin && originSeen++ >= maxOrigin) continue

      shownIxps.add(code)
      const ixpId = `ixp-${code}`

      if (!seenNodes.has(ixpId)) {
        seenNodes.add(ixpId)
        nodes.push({
          id: ixpId,
          type: isDirect ? 'ixp_direct' : (isMember ? 'ixp_member' : 'ixp_origin'),
          label: code.toUpperCase(),
          ixpCode: code,
          _r: isDirect ? 10 : 8,
        })
      }

      if (isDirect) {
        links.push({ source: 'main', target: ixpId, style: 'direct' })
      } else {
        const paths = ixpPaths[code]
        if (paths?.length) {
          const seenLinks = new Set<string>()
          for (const path of paths) {
            let prevId = 'main'
            for (const asnId of path) {
              const nodeId = `path-${asnId}`
              if (!seenNodes.has(nodeId)) {
                seenNodes.add(nodeId)
                const metaEntry = pathNodeMeta[String(asnId)]
                nodes.push({
                  id: nodeId,
                  type: 'path',
                  label: `AS${asnId}`,
                  asnId,
                  _r: 8,
                  _isBr: metaEntry?.is_br,
                })
              }
              const ek = `${prevId}→${nodeId}`
              if (!seenLinks.has(ek)) { seenLinks.add(ek); links.push({ source: prevId, target: nodeId, style: 'path-chain' }) }
              prevId = nodeId
            }
            const ek = `${prevId}→${ixpId}`
            if (!seenLinks.has(ek)) { seenLinks.add(ek); links.push({ source: prevId, target: ixpId, style: 'path-chain' }) }
          }
        } else {
          links.push({ source: 'main', target: ixpId, style: 'origin-unknown' })
        }
      }
    }

    // ── Member-only nodes (registered but no prefixes for this AFI) ───────
    for (const code of ixpMemberCodes) {
      if (shownIxps.has(code)) continue  // already shown as routing presence
      const afiPres = ixpPresence[code]?.[afi]
      if ((afiPres?.prefixes?.length ?? 0) > 0) continue  // has prefixes, shown above
      const ixpId = `ixp-${code}`
      if (!seenNodes.has(ixpId)) {
        seenNodes.add(ixpId)
        nodes.push({
          id: ixpId,
          type: 'ixp_member',
          label: code.toUpperCase(),
          ixpCode: code,
          _r: 8,
        })
        links.push({ source: 'main', target: ixpId, style: 'member' })
      }
    }

    if (nodes.length === 1) {
      d3.select(svg).append('text')
        .attr('x', width / 2).attr('y', height / 2)
        .attr('text-anchor', 'middle').attr('fill', '#94a3b8').attr('font-size', 13)
        .text(`Nenhuma presença ${afi === 'v6' ? 'IPv6' : 'IPv4'} em IXP observada`)
      return
    }

    // ── SVG / defs ─────────────────────────────────────────────────────────
    const root = d3.select(svg)
    const defs = root.append('defs')
    ;(['direct', 'path', 'unknown', 'member'] as const).forEach((t) => {
      const color = t === 'direct' ? AC.e_direct
                  : t === 'path'   ? C.e_path
                  : t === 'member' ? C.e_member
                  : C.e_unknown
      defs.append('marker').attr('id', `ixp-arr-${afi}-${t}`)
        .attr('viewBox', '0 -5 10 10').attr('refX', 16).attr('refY', 0)
        .attr('markerWidth', 5).attr('markerHeight', 5).attr('orient', 'auto')
        .append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', color)
    })

    const g = root.append('g')

    // ── Force simulation ──────────────────────────────────────────────────
    const chargeStr = Math.min(-84, -140 + nodes.length * 2.1)

    // Fix main node at center; IXP nodes pulled to type-based sectors (outward);
    // path nodes pulled toward center so they stay between main and their IXP.
    const mainNode = nodes.find(d => d.id === 'main')
    if (mainNode) { mainNode.fx = width / 2; mainNode.fy = height / 2 }

    // Sector targets: ixp_direct = top, ixp_origin = bottom-right, ixp_member = bottom-left
    const SECTOR_X: Record<string, number> = {
      ixp_direct: width  * 0.50,
      ixp_origin: width  * 0.76,
      ixp_member: width  * 0.24,
      path:       width  * 0.50,
    }
    const SECTOR_Y: Record<string, number> = {
      ixp_direct: height * 0.12,
      ixp_origin: height * 0.80,
      ixp_member: height * 0.80,
      path:       height * 0.50,
    }

    const simulation = d3.forceSimulation<GNode>(nodes)
      .force('link', d3.forceLink<GNode, GLink>(links).id(d => d.id)
        .distance(d => {
          const t = (d.target as GNode).type
          return t === 'ixp_direct' ? 91 : t === 'ixp_origin' ? 70 : t === 'ixp_member' ? 77 : 56
        }))
      .force('charge', d3.forceManyBody().strength(chargeStr))
      .force('collision', d3.forceCollide<GNode>(d => d._r + 10))
      .force('sx', d3.forceX<GNode>(d => SECTOR_X[d.type] ?? width  / 2)
        .strength(d => d.type === 'main' ? 0 : d.type.startsWith('ixp') ? 0.04 : 0.02))
      .force('sy', d3.forceY<GNode>(d => SECTOR_Y[d.type] ?? height / 2)
        .strength(d => d.type === 'main' ? 0 : d.type.startsWith('ixp') ? 0.04 : 0.02))

    // ── Links ─────────────────────────────────────────────────────────────
    const link = g.append('g').selectAll<SVGLineElement, GLink>('line')
      .data(links).join('line')
      .attr('stroke', d =>
        d.style === 'direct'     ? AC.e_direct :
        d.style === 'path-chain' ? C.e_path :
        d.style === 'member'     ? C.e_member :
        C.e_unknown
      )
      .attr('stroke-width', d => d.style === 'direct' ? 2 : 1.5)
      .attr('stroke-opacity', d => d.style === 'origin-unknown' ? 0.3 : 0.6)
      .attr('stroke-dasharray', d => d.style === 'direct' ? null : '5,3')
      .attr('marker-end', d =>
        d.style === 'direct'     ? `url(#ixp-arr-${afi}-direct)` :
        d.style === 'path-chain' ? `url(#ixp-arr-${afi}-path)` :
        d.style === 'member'     ? `url(#ixp-arr-${afi}-member)` :
        `url(#ixp-arr-${afi}-unknown)`
      )

    // ── Drag ──────────────────────────────────────────────────────────────
    const drag = d3.drag<SVGGElement, GNode>()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x; d.fy = d.y
        tip.style('display', 'none')
      })
      .on('drag', (event, d) => {
        d.fx = event.x; d.fy = event.y
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0)
        if (d.type !== 'main') { d.fx = null; d.fy = null }
      })

    // ── Nodes ─────────────────────────────────────────────────────────────
    const node = g.append('g').selectAll<SVGGElement, GNode>('g')
      .data(nodes).join('g')
      .style('cursor', 'grab')
      .call(drag)

    node.append('circle')
      .attr('r', d => d._r)
      .attr('fill', d => {
        if (d.type === 'main')       return C.main
        if (d.type === 'ixp_direct') return AC.ixp_direct
        if (d.type === 'ixp_origin') return AC.ixp_origin
        if (d.type === 'ixp_member') return C.ixp_member
        return d._isBr === true ? C.path_br : d._isBr === false ? C.path_nonbr : C.path_unk
      })
      .attr('stroke', 'white')
      .attr('stroke-width', 2)

    // Outer dashed ring on path nodes
    node.filter(d => d.type === 'path')
      .append('circle')
      .attr('r', d => d._r + 4)
      .attr('fill', 'none')
      .attr('stroke', d => d._isBr === false ? C.path_nonbr : C.path_br)
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '3,2')

    node.append('text')
      .attr('dy', d => d._r + 11)
      .attr('text-anchor', 'middle')
      .attr('font-size', d => d.type === 'main' ? 11 : 9)
      .attr('font-weight', d => d.type === 'path' ? '600' : 'normal')
      .attr('fill', d =>
        d.type === 'path'       ? (d._isBr === false ? C.path_nonbr : C.path_br) :
        d.type === 'ixp_member' ? C.ixp_member :
        '#374151'
      )
      .text(d => d.label)

    // ── Click ─────────────────────────────────────────────────────────────
    node.on('click', (_e, d) => {
      if (d.type.startsWith('ixp') && d.ixpCode) onIxpClick?.(d.ixpCode)
      if (d.type === 'path' && d.asnId != null) onBridgeClick?.(d.asnId)
    })

    // ── Tooltip on IXP nodes (direct/origin/member) ────────────────────────
    node.filter(d => d.type === 'ixp_direct' || d.type === 'ixp_origin' || d.type === 'ixp_member')
      .on('mouseover', function (event, d) {
        if (!d.ixpCode) return
        const ixpPrefixes = ixpPresence[d.ixpCode]?.[afi]?.prefixes ?? []
        const isMemberNode = d.type === 'ixp_member'
        tip
          .html(buildIxpTooltipHtml(d.ixpCode, ixpPrefixes, mainAsnRirPrefixes, afi, ixpPeerStats?.[d.ixpCode]?.[afi], isMemberNode))
          .style('display', 'block')
        const cr = container.getBoundingClientRect()
        tip
          .style('left', `${event.clientX - cr.left + 12}px`)
          .style('top', `${event.clientY - cr.top - 10}px`)
      })
      .on('mousemove', function (event) {
        const cr = container.getBoundingClientRect()
        tip
          .style('left', `${event.clientX - cr.left + 12}px`)
          .style('top', `${event.clientY - cr.top - 10}px`)
      })
      .on('mouseout', () => tip.style('display', 'none'))

    // ── Tooltip on path nodes ──────────────────────────────────────────────
    node.filter(d => d.type === 'path')
      .on('mouseover', function (event, d) {
        const asnId = d.asnId
        if (asnId == null) return
        const meta = pathNodeMeta[String(asnId)]
        const bridged = pathAsnIxps[asnId] ?? []
        tip
          .html(buildPathNodeTooltipHtml(asnId, meta, bridged, ixpPresence, afi))
          .style('display', 'block')
        const cr = container.getBoundingClientRect()
        tip
          .style('left', `${event.clientX - cr.left + 12}px`)
          .style('top', `${event.clientY - cr.top - 10}px`)
      })
      .on('mousemove', function (event) {
        const cr = container.getBoundingClientRect()
        tip
          .style('left', `${event.clientX - cr.left + 12}px`)
          .style('top', `${event.clientY - cr.top - 10}px`)
      })
      .on('mouseout', () => tip.style('display', 'none'))

    // ── Tick ──────────────────────────────────────────────────────────────
    simulation.on('tick', () => {
      for (const d of nodes) {
        d.x = Math.max(PAD + d._r, Math.min(width  - PAD - d._r, d.x ?? width  / 2))
        d.y = Math.max(PAD + d._r, Math.min(height - PAD - d._r, d.y ?? height / 2))
      }
      link
        .attr('x1', d => (d.source as GNode).x!)
        .attr('y1', d => (d.source as GNode).y!)
        .attr('x2', d => (d.target as GNode).x!)
        .attr('y2', d => (d.target as GNode).y!)
      node.attr('transform', d => `translate(${d.x},${d.y})`)
    })

    return () => { simulation.stop() }
  }, [mainAsn, afi, mainAsnRirPrefixes, ixpPresence, ixpPaths, pathNodeMeta, ixpMemberCodes, ixpPeerStats, width, height, maxOrigin, onIxpClick, onBridgeClick])

  const AC = afi === 'v6' ? CV6 : CV4

  return (
    <div ref={containerRef} style={{ position: 'relative', display: 'inline-block' }}>
      <svg ref={svgRef} width={width} height={height} className="rounded border border-gray-100" />
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-gray-500 justify-center">
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: AC.ixp_direct }} />
          Peering direto
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: AC.ixp_origin }} />
          Só origem
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: C.ixp_member }} />
          Membro registrado
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: C.path_br }} />
          AS intermediário (BR)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: C.path_nonbr }} />
          AS intermediário (não-BR)
        </span>
      </div>
    </div>
  )
}
