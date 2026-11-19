/**
 * CDNIXPPresenceGraph — versão multi-ASN do IXPPresenceGraph.
 *
 * Com um único ASN, comportamento e visual idênticos ao IXPPresenceGraph.
 * Com múltiplos, os ASNs da CDN ficam fixos no centro em fileira horizontal;
 * cada um se conecta aos seus IXPs (direto ou via AS intermediários).
 * IXP e path nodes são compartilhados quando o mesmo AS/IXP aparece para
 * mais de um ASN do grupo; links chegam de cada main node correspondente.
 */
import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import type { IXPPresence, PathNodeMeta } from '../../types/api'

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

const CV6 = { ixp_direct: '#f97316', ixp_origin: '#d4a76a', e_direct: '#f97316' }
const CV4 = { ixp_direct: '#38bdf8', ixp_origin: '#7fb5d4', e_direct: '#38bdf8' }
const C = {
  main: '#1d4ed8', path_br: '#16a34a', path_nonbr: '#7c3aed', path_unk: '#6b7280',
  ixp_member: '#dc2626', e_path: '#6b7280', e_unknown: '#d1d5db', e_member: '#dc2626',
}

export interface CDNAsnPresenceData {
  asn: number
  ixpPresence: Record<string, IXPPresence>
  ixpPaths: Record<string, number[][]>
  pathNodeMeta: Record<string, PathNodeMeta>
  ixpMemberCodes: string[]
  rirPrefixesV4: string[]
  rirPrefixesV6: string[]
}

interface Props {
  afi: 'v4' | 'v6'
  asnDataList: CDNAsnPresenceData[]
  onIxpClick?: (code: string) => void
  onBridgeClick?: (asn: number) => void
  width?: number
  height?: number
  maxOrigin?: number
}

// ── Tooltip helpers (mesmos do IXPPresenceGraph) ───────────────────────────

function parseV4(p: string) {
  const [host, lenStr] = p.split('/')
  if (!host || !lenStr) return null
  const len = parseInt(lenStr, 10)
  if (isNaN(len) || len < 0 || len > 32) return null
  const parts = host.split('.').map(Number)
  if (parts.length !== 4 || parts.some(n => isNaN(n))) return null
  const addr = ((parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]) >>> 0
  return { addr, len }
}
function isV4Sub(c: { addr: number; len: number }, p: { addr: number; len: number }) {
  if (c.len < p.len) return false
  const mask = p.len === 0 ? 0 : (~0 << (32 - p.len)) >>> 0
  return (c.addr & mask) === (p.addr & mask)
}
function space24(prefixes: string[]) {
  return prefixes.reduce((s, p) => s + Math.pow(2, Math.max(0, 24 - parseInt(p.split('/')[1] ?? '32', 10))), 0)
}
function covered24(ixpPfx: string[], rirPfx: string[]) {
  const nets = rirPfx.map(parseV4).filter(Boolean) as ReturnType<typeof parseV4>[]
  const set = new Set<number>()
  for (const p of ixpPfx) {
    const n = parseV4(p)
    if (!n || !nets.some(r => isV4Sub(n, r!))) continue
    const blocks = n.len >= 24 ? 1 : 1 << (24 - n.len)
    const base = n.addr >>> 8
    for (let i = 0; i < blocks; i++) set.add(base + i)
  }
  return set.size
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
function parseV6(p: string) {
  const [host, lenStr] = p.split('/')
  if (!host || !lenStr) return null
  const len = parseInt(lenStr, 10)
  if (isNaN(len) || len < 0 || len > 128) return null
  try {
    const groups = expandV6(host)
    if (!groups) return null
    let addr = 0n
    for (const g of groups) addr = (addr << 16n) | BigInt(parseInt(g, 16))
    return { addr, len }
  } catch { return null }
}
function isV6Sub(c: { addr: bigint; len: number }, p: { addr: bigint; len: number }) {
  if (c.len < p.len) return false
  if (p.len === 0) return true
  const mask = ~0n << BigInt(128 - p.len)
  return (c.addr & mask) === (p.addr & mask)
}
function space48(prefixes: string[]) {
  return prefixes.reduce((s, p) => s + Math.pow(2, Math.max(0, 48 - parseInt(p.split('/')[1] ?? '128', 10))), 0)
}
function covered48(ixpPfx: string[], rirPfx: string[]) {
  const nets = rirPfx.map(parseV6).filter(Boolean) as ReturnType<typeof parseV6>[]
  const set = new Set<bigint>()
  let direct = 0
  for (const p of ixpPfx) {
    const n = parseV6(p)
    if (!n || !nets.some(r => isV6Sub(n, r!))) continue
    if (n.len >= 32) {
      const blocks = n.len >= 48 ? 1 : 1 << (48 - n.len)
      const base = n.addr >> BigInt(128 - 48)
      for (let i = 0; i < blocks; i++) set.add(base + BigInt(i))
    } else { direct += Math.pow(2, 48 - n.len) }
  }
  return set.size + direct
}

function buildIxpTip(code: string, ixpPfx: string[], rirPfx: string[], afi: 'v4' | 'v6'): string {
  const rirSp = afi === 'v4' ? space24(rirPfx) : space48(rirPfx)
  const cov   = afi === 'v4' ? covered24(ixpPfx, rirPfx) : covered48(ixpPfx, rirPfx)
  const pct   = rirSp > 0 ? (cov / rirSp * 100).toFixed(1) : null
  const label = afi === 'v6' ? 'IPv6' : 'IPv4'
  let html = `<div style="font-weight:600;margin-bottom:4px">${code.toUpperCase()}</div>`
  if (ixpPfx.length === 0) {
    html += `<div style="opacity:.5">sem prefixos ${label} deste grupo</div>`
  } else {
    html += `<div style="margin-top:4px;border-top:1px solid #f3f4f6;padding-top:4px">${label}: `
    if (ixpPfx.length <= 10) {
      html += ixpPfx.map(p => `<code style="background:#f3f4f6;padding:0 2px;border-radius:2px">${p}</code>`).join(', ')
    } else { html += `${ixpPfx.length} prefixos` }
    html += `</div>`
    if (pct != null) html += `<div style="opacity:.65;margin-top:3px">${pct}% do espaço alocado</div>`
  }
  return html
}

function buildPathTip(asnId: number, meta: PathNodeMeta | undefined, bridged: string[]): string {
  const name = meta?.name ?? ''
  const brLabel = meta?.is_br ? 'BR' : 'não-BR'
  let html = `<div style="font-weight:600;margin-bottom:4px">AS${asnId}${name ? ` — ${name}` : ''} <span style="opacity:.7;font-weight:400">(${brLabel})</span></div>`
  const sorted = [...bridged].sort()
  for (const code of sorted) {
    html += `<div style="margin-top:5px;border-top:1px solid #e5e7eb;padding-top:4px"><strong>${code.toUpperCase()}</strong></div>`
  }
  return html
}

// ── Componente ────────────────────────────────────────────────────────────────

export function CDNIXPPresenceGraph({
  afi,
  asnDataList,
  onIxpClick,
  onBridgeClick,
  width = 560,
  height = 420,
  maxOrigin = 30,
}: Props) {
  const svgRef      = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const svg = svgRef.current
    const container = containerRef.current
    if (!svg || !container || asnDataList.length === 0) return
    d3.select(svg).selectAll('*').remove()

    const PAD = 30
    const AC  = afi === 'v6' ? CV6 : CV4
    const cdnAsnSet = new Set(asnDataList.map(d => d.asn))

    // Merge pathNodeMeta across all docs
    const mergedPathMeta: Record<string, PathNodeMeta> = {}
    for (const d of asnDataList) Object.assign(mergedPathMeta, d.pathNodeMeta)

    // Tooltip
    const tip = d3.select(container)
      .selectAll<HTMLDivElement, unknown>('.cdn-ixp-tip')
      .data([null]).join('div').attr('class', 'cdn-ixp-tip')
      .style('position', 'absolute').style('pointer-events', 'none').style('display', 'none')
      .style('background', 'white').style('border', '1px solid #e5e7eb')
      .style('border-radius', '6px').style('padding', '8px 10px')
      .style('font-size', '11px').style('line-height', '1.5').style('color', '#374151')
      .style('box-shadow', '0 2px 8px rgba(0,0,0,.12)').style('max-width', '300px').style('z-index', '10')

    // Mapa: bridge ASN → IXPs que ele conecta (para tooltip de path nodes)
    const pathAsnIxps: Record<number, Set<string>> = {}
    for (const d of asnDataList) {
      for (const [code, paths] of Object.entries(d.ixpPaths)) {
        for (const path of paths) {
          for (const asnId of path) {
            ;(pathAsnIxps[asnId] ??= new Set()).add(code)
          }
        }
      }
    }

    // Acumula prefixos de todos os ASNs do grupo por IXP (para tooltip)
    const ixpGroupPrefixes: Record<string, string[]> = {}
    const rirPfxUnion: string[] = [...new Set(
      asnDataList.flatMap(d => afi === 'v4' ? d.rirPrefixesV4 : d.rirPrefixesV6)
    )]
    for (const d of asnDataList) {
      for (const [code, pres] of Object.entries(d.ixpPresence)) {
        const pfx = pres[afi]?.prefixes ?? []
        const arr = ixpGroupPrefixes[code] ?? []
        for (const p of pfx) if (!arr.includes(p)) arr.push(p)
        ixpGroupPrefixes[code] = arr
      }
    }

    // ── Main nodes ─────────────────────────────────────────────────────────
    const nMain   = asnDataList.length
    const spacing = Math.min(90, (width - 2 * PAD) / Math.max(nMain, 1))
    const startX  = width / 2 - ((nMain - 1) * spacing) / 2

    const nodes: GNode[] = asnDataList.map((d, i) => ({
      id: `main-${d.asn}`, type: 'main', label: `AS${d.asn}`, _r: 14,
      fx: nMain === 1 ? width / 2 : startX + i * spacing,
      fy: height / 2,
    }))
    const links: GLink[] = []
    const seenNodes = new Set<string>(nodes.map(n => n.id))
    // Global para evitar links duplicados entre todos os ASNs do grupo.
    // Quando um CDN ASN aparece como bridge de outro CDN ASN, roteamos pelo
    // main node existente em vez de pular — o seenLinks impede duplicatas.
    const seenLinks = new Set<string>()

    // Tipo final de cada IXP node (pode ser promovido de member → origin → direct)
    const ixpNodeType: Record<string, 'ixp_direct' | 'ixp_origin' | 'ixp_member'> = {}
    let originSeen = 0

    // Percorre cada ASN do grupo
    for (const d of asnDataList) {
      const mainId = `main-${d.asn}`
      const memberSet = new Set<string>(d.ixpMemberCodes)
      const entries = Object.entries(d.ixpPresence)
        .sort(([, a], [, b]) => ((b[afi]?.direct ? 1 : 0) - (a[afi]?.direct ? 1 : 0)))

      for (const [code, pres] of entries) {
        const afiPres = pres[afi]
        if (!afiPres || (afiPres.prefixes?.length ?? 0) === 0) continue

        const isDirect = afiPres.direct
        const isOrigin = afiPres.origin && !isDirect
        if (!isDirect && !isOrigin) continue
        if (isOrigin && originSeen++ >= maxOrigin) continue

        const ixpId = `ixp-${code}`

        // Determinar / atualizar tipo do nó IXP
        if (!ixpNodeType[code]) {
          ixpNodeType[code] = isDirect ? 'ixp_direct' : (memberSet.has(code) ? 'ixp_member' : 'ixp_origin')
        } else if (isDirect) {
          ixpNodeType[code] = 'ixp_direct'  // promoção
        }

        if (!seenNodes.has(ixpId)) {
          seenNodes.add(ixpId)
          nodes.push({
            id: ixpId, type: ixpNodeType[code], label: code.toUpperCase(),
            ixpCode: code, _r: isDirect ? 10 : 8,
          })
        }

        if (isDirect) {
          const ek = `${mainId}→${ixpId}`
          if (!seenLinks.has(ek)) { seenLinks.add(ek); links.push({ source: mainId, target: ixpId, style: 'direct' }) }
        } else {
          const paths = d.ixpPaths[code]
          if (paths?.length) {
            for (const path of paths) {
              let prevId = mainId
              for (const bridgeAsn of path) {
                // Se o bridge é outro CDN ASN, roteamos pelo seu main node (em vez
                // de pular), mostrando a dependência entre os ASNs do grupo.
                const nodeId = cdnAsnSet.has(bridgeAsn)
                  ? `main-${bridgeAsn}`
                  : `path-${bridgeAsn}`

                if (!seenNodes.has(nodeId)) {
                  seenNodes.add(nodeId)
                  const meta = mergedPathMeta[String(bridgeAsn)]
                  nodes.push({ id: nodeId, type: 'path', label: `AS${bridgeAsn}`, asnId: bridgeAsn, _r: 8, _isBr: meta?.is_br })
                }
                const ek = `${prevId}→${nodeId}`
                if (!seenLinks.has(ek)) { seenLinks.add(ek); links.push({ source: prevId, target: nodeId, style: 'path-chain' }) }
                prevId = nodeId
              }
              const ek = `${prevId}→${ixpId}`
              if (!seenLinks.has(ek)) { seenLinks.add(ek); links.push({ source: prevId, target: ixpId, style: 'path-chain' }) }
            }
          } else {
            const ek = `${mainId}→${ixpId}`
            if (!seenLinks.has(ek)) { seenLinks.add(ek); links.push({ source: mainId, target: ixpId, style: 'origin-unknown' }) }
          }
        }
      }

      // Member-only (sem prefixos no AFI)
      for (const code of d.ixpMemberCodes) {
        const afiPres = d.ixpPresence[code]?.[afi]
        if ((afiPres?.prefixes?.length ?? 0) > 0) continue  // já tem presença de roteamento
        const ixpId = `ixp-${code}`
        if (!seenNodes.has(ixpId)) {
          seenNodes.add(ixpId)
          ixpNodeType[code] = 'ixp_member'
          nodes.push({ id: ixpId, type: 'ixp_member', label: code.toUpperCase(), ixpCode: code, _r: 8 })
        }
        const ek = `${mainId}→${ixpId}`
        if (!seenLinks.has(ek)) { seenLinks.add(ek); links.push({ source: mainId, target: ixpId, style: 'member' }) }
      }
    }

    // Atualiza tipos dos nós IXP já criados (promoções)
    for (const n of nodes) {
      if (n.ixpCode && ixpNodeType[n.ixpCode]) n.type = ixpNodeType[n.ixpCode]
    }

    if (nodes.length === nMain) {
      d3.select(svg).append('text')
        .attr('x', width / 2).attr('y', height / 2)
        .attr('text-anchor', 'middle').attr('fill', '#94a3b8').attr('font-size', 13)
        .text(`Nenhuma presença ${afi === 'v6' ? 'IPv6' : 'IPv4'} em IXP observada`)
      return
    }

    // ── SVG/defs ──────────────────────────────────────────────────────────
    const root = d3.select(svg)
    const defs = root.append('defs')
    ;(['direct', 'path', 'unknown', 'member'] as const).forEach((t) => {
      const color = t === 'direct' ? AC.e_direct : t === 'path' ? C.e_path : t === 'member' ? C.e_member : C.e_unknown
      defs.append('marker').attr('id', `cdn-ixp-arr-${afi}-${t}`)
        .attr('viewBox', '0 -5 10 10').attr('refX', 16).attr('refY', 0)
        .attr('markerWidth', 5).attr('markerHeight', 5).attr('orient', 'auto')
        .append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', color)
    })

    const g = root.append('g')

    // ── Força ─────────────────────────────────────────────────────────────
    const chargeStr = Math.min(-84, -140 + nodes.length * 2.1)
    const SECTOR_X: Record<string, number> = { ixp_direct: width * .50, ixp_origin: width * .76, ixp_member: width * .24, path: width * .50 }
    const SECTOR_Y: Record<string, number> = { ixp_direct: height * .12, ixp_origin: height * .80, ixp_member: height * .80, path: height * .50 }

    const simulation = d3.forceSimulation<GNode>(nodes)
      .force('link', d3.forceLink<GNode, GLink>(links).id(d => d.id)
        .distance(d => { const t = (d.target as GNode).type; return t === 'ixp_direct' ? 91 : t === 'ixp_origin' ? 70 : t === 'ixp_member' ? 77 : 56 }))
      .force('charge', d3.forceManyBody().strength(chargeStr))
      .force('collision', d3.forceCollide<GNode>(d => d._r + 10))
      .force('sx', d3.forceX<GNode>(d => SECTOR_X[d.type] ?? width / 2)
        .strength(d => d.type === 'main' ? 0 : d.type.startsWith('ixp') ? 0.04 : 0.02))
      .force('sy', d3.forceY<GNode>(d => SECTOR_Y[d.type] ?? height / 2)
        .strength(d => d.type === 'main' ? 0 : d.type.startsWith('ixp') ? 0.04 : 0.02))

    // ── Links ─────────────────────────────────────────────────────────────
    const link = g.append('g').selectAll<SVGLineElement, GLink>('line')
      .data(links).join('line')
      .attr('stroke', d => d.style === 'direct' ? AC.e_direct : d.style === 'path-chain' ? C.e_path : d.style === 'member' ? C.e_member : C.e_unknown)
      .attr('stroke-width', d => d.style === 'direct' ? 2 : 1.5)
      .attr('stroke-opacity', d => d.style === 'origin-unknown' ? 0.3 : 0.6)
      .attr('stroke-dasharray', d => d.style === 'direct' ? null : '5,3')
      .attr('marker-end', d =>
        d.style === 'direct'     ? `url(#cdn-ixp-arr-${afi}-direct)` :
        d.style === 'path-chain' ? `url(#cdn-ixp-arr-${afi}-path)` :
        d.style === 'member'     ? `url(#cdn-ixp-arr-${afi}-member)` :
        `url(#cdn-ixp-arr-${afi}-unknown)`)

    // ── Drag ─────────────────────────────────────────────────────────────
    const drag = d3.drag<SVGGElement, GNode>()
      .on('start', (ev, d) => { if (!ev.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; tip.style('display', 'none') })
      .on('drag',  (ev, d) => { d.fx = ev.x; d.fy = ev.y })
      .on('end',   (ev, d) => { if (!ev.active) simulation.alphaTarget(0); if (d.type !== 'main') { d.fx = null; d.fy = null } })

    // ── Nodes ─────────────────────────────────────────────────────────────
    const node = g.append('g').selectAll<SVGGElement, GNode>('g')
      .data(nodes).join('g').style('cursor', 'grab').call(drag)

    node.append('circle')
      .attr('r', d => d._r)
      .attr('fill', d => {
        if (d.type === 'main')       return C.main
        if (d.type === 'ixp_direct') return AC.ixp_direct
        if (d.type === 'ixp_origin') return AC.ixp_origin
        if (d.type === 'ixp_member') return C.ixp_member
        return d._isBr === true ? C.path_br : d._isBr === false ? C.path_nonbr : C.path_unk
      })
      .attr('stroke', 'white').attr('stroke-width', 2)

    node.filter(d => d.type === 'path').append('circle')
      .attr('r', d => d._r + 4).attr('fill', 'none')
      .attr('stroke', d => d._isBr === false ? C.path_nonbr : C.path_br)
      .attr('stroke-width', 1).attr('stroke-dasharray', '3,2')

    node.append('text')
      .attr('dy', d => d._r + 11).attr('text-anchor', 'middle')
      .attr('font-size', d => d.type === 'main' ? 11 : 9)
      .attr('font-weight', d => d.type === 'path' ? '600' : 'normal')
      .attr('fill', d => d.type === 'path' ? (d._isBr === false ? C.path_nonbr : C.path_br) : d.type === 'ixp_member' ? C.ixp_member : '#374151')
      .text(d => d.label)

    // ── Click ─────────────────────────────────────────────────────────────
    node.on('click', (_e, d) => {
      if (d.type.startsWith('ixp') && d.ixpCode) onIxpClick?.(d.ixpCode)
      if (d.type === 'path' && d.asnId != null) onBridgeClick?.(d.asnId)
    })

    // ── Tooltips IXP ──────────────────────────────────────────────────────
    node.filter(d => d.type === 'ixp_direct' || d.type === 'ixp_origin' || d.type === 'ixp_member')
      .on('mouseover', function(event, d) {
        if (!d.ixpCode) return
        const ixpPfx = ixpGroupPrefixes[d.ixpCode] ?? []
        tip.html(buildIxpTip(d.ixpCode, ixpPfx, rirPfxUnion, afi)).style('display', 'block')
        const cr = container.getBoundingClientRect()
        tip.style('left', `${event.clientX - cr.left + 12}px`).style('top', `${event.clientY - cr.top - 10}px`)
      })
      .on('mousemove', function(event) {
        const cr = container.getBoundingClientRect()
        tip.style('left', `${event.clientX - cr.left + 12}px`).style('top', `${event.clientY - cr.top - 10}px`)
      })
      .on('mouseout', () => tip.style('display', 'none'))

    // ── Tooltips path ─────────────────────────────────────────────────────
    node.filter(d => d.type === 'path')
      .on('mouseover', function(event, d) {
        if (d.asnId == null) return
        const bridged = [...(pathAsnIxps[d.asnId] ?? [])]
        tip.html(buildPathTip(d.asnId, mergedPathMeta[String(d.asnId)], bridged)).style('display', 'block')
        const cr = container.getBoundingClientRect()
        tip.style('left', `${event.clientX - cr.left + 12}px`).style('top', `${event.clientY - cr.top - 10}px`)
      })
      .on('mousemove', function(event) {
        const cr = container.getBoundingClientRect()
        tip.style('left', `${event.clientX - cr.left + 12}px`).style('top', `${event.clientY - cr.top - 10}px`)
      })
      .on('mouseout', () => tip.style('display', 'none'))

    // ── Tick ──────────────────────────────────────────────────────────────
    simulation.on('tick', () => {
      for (const d of nodes) {
        if (d.type !== 'main') {
          d.x = Math.max(PAD + d._r, Math.min(width  - PAD - d._r, d.x ?? width  / 2))
          d.y = Math.max(PAD + d._r, Math.min(height - PAD - d._r, d.y ?? height / 2))
        }
      }
      link
        .attr('x1', d => (d.source as GNode).x!).attr('y1', d => (d.source as GNode).y!)
        .attr('x2', d => (d.target as GNode).x!).attr('y2', d => (d.target as GNode).y!)
      node.attr('transform', d => `translate(${d.x},${d.y})`)
    })

    return () => { simulation.stop() }
  }, [afi, asnDataList, width, height, maxOrigin, onIxpClick, onBridgeClick])

  const AC = afi === 'v6' ? CV6 : CV4

  return (
    <div ref={containerRef} style={{ position: 'relative', display: 'inline-block' }}>
      <svg ref={svgRef} width={width} height={height} className="rounded border border-gray-100 w-full" />
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-gray-500 justify-center">
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: AC.ixp_direct }} />Peering direto</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: AC.ixp_origin }} />Só origem</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: C.ixp_member }} />Membro registrado</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: C.path_br }} />AS intermediário (BR)</span>
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: C.path_nonbr }} />AS intermediário (não-BR)</span>
      </div>
    </div>
  )
}
