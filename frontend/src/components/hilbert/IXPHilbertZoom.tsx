/**
 * Modais de zoom para os Hilbert maps da página de IXP.
 *
 * ZoomModalV4  — amplia um /8 com granularidade /24 (256×256 Hilbert), grade /16, tooltip /24.
 * ZoomModalV6  — amplia um /20 (64×64 de /32), grade /28, tooltip /32.
 */
import { useRef, useEffect, useId, useMemo, useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  d2xy,
  GRID16, getGrid1024, POS_TO_D16,
  ianaColorRGB, block16ToPrefix, block16ToSlash8,
  cellIndexToV6Prefix, hexToRGB, opacidadeDensidade,
  type V6BlockConfig,
} from './hilbert'
import { fetchIXPHilbertV4Detail, fetchHilbertV4Detail } from '../../services/api'
import type { LayerKey } from './HilbertMap16'
import { ModalAcessivel } from '../ui/ModalAcessivel'
import { palavra } from '../../lib/sintese'

const ZOOM_CANVAS = 512
const ZOOM_CSS    = 440

const COLOR_ALL   = '#6366f1'
const COLOR_OWN   = '#3b82f6'
const COLOR_THIRD = '#f97316'

// ---------------------------------------------------------------------------
// Lookup tables para /24 sub-Hilbert (n=16, 256 /24 por /16)
// ---------------------------------------------------------------------------

const V4_CELL      = ZOOM_CANVAS / 16   // 32px por bloco /16
const V4_CELL_24   = V4_CELL / 16       // 2px por bloco /24

// SUB_POS_FROM_C[c] = y*16+x para a posição Hilbert do c-ésimo /24 dentro do /16
const SUB_POS_FROM_C: Uint16Array = (() => {
  const arr = new Uint16Array(256)
  for (let c = 0; c < 256; c++) {
    const { x, y } = d2xy(16, c)
    arr[c] = y * 16 + x
  }
  return arr
})()

// SUB_C_FROM_POS[y*16+x] = c — inverso do anterior (mouse→/24)
const SUB_C_FROM_POS: Uint8Array = (() => {
  const arr = new Uint8Array(256)
  for (let c = 0; c < 256; c++) {
    const { x, y } = d2xy(16, c)
    arr[y * 16 + x] = c
  }
  return arr
})()

// ============================================================
// IPv4 /8 → /24  zoom modal
// ============================================================

interface ZoomV4Props {
  sx: number
  sy: number
  slashEight: number
  code: string
  date?: string
  selectedPeer: number | null
  densityAll: number[] | null
  densityOwn: number[] | null
  densityThird: number[] | null
  isPeerMode: boolean
  onClose: () => void
}

interface Tooltip4 {
  cssX: number
  cssY: number
  prefix: string        // /24 ou /16
  is24: boolean
  ownCount?: number
  thirdCount?: number
  totalCount?: number
  present?: boolean
}

export function ZoomModalV4({
  sx, sy, slashEight,
  code, date, selectedPeer,
  densityAll, densityOwn, densityThird,
  isPeerMode, onClose,
}: ZoomV4Props) {
  const idTitulo = useId()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [tooltip, setTooltip] = useState<Tooltip4 | null>(null)

  // Detalhe /24 — fetch ao abrir o modal
  const { data: detailData, isLoading: loadingDetail } = useQuery({
    queryKey: ['ixp-hilbert-v4-detail', code, slashEight, selectedPeer, date],
    queryFn: () => fetchIXPHilbertV4Detail(code, slashEight, selectedPeer ?? undefined, date),
    staleTime: Infinity, gcTime: Infinity,
  })

  const hasDetail = !!detailData

  // Índices dos 256 blocos /16 dentro do /8 com suas posições locais
  const blockIndices = useMemo(() => {
    const arr: { dx: number; dy: number; blockIdx: number; b: number }[] = []
    for (let dy = 0; dy < 16; dy++) {
      for (let dx = 0; dx < 16; dx++) {
        const blockIdx = POS_TO_D16[(sy * 16 + dy) * 256 + (sx * 16 + dx)]
        arr.push({ dx, dy, blockIdx, b: blockIdx & 0xFF })
      }
    }
    return arr
  }, [sx, sy])

  // Canvas: /24 quando detail carregado, /16 enquanto aguarda
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const [ar, ag, ab] = hexToRGB(COLOR_ALL)
    const [or, og, ob] = hexToRGB(COLOR_OWN)
    const [tr, tg, tb] = hexToRGB(COLOR_THIRD)
    const [br, bg, bb] = ianaColorRGB(slashEight)

    const pixels = new Uint8ClampedArray(ZOOM_CANVAS * ZOOM_CANVAS * 4)
    for (let i = 0; i < pixels.length; i += 4) {
      pixels[i] = br; pixels[i+1] = bg; pixels[i+2] = bb; pixels[i+3] = 255
    }

    if (hasDetail) {
      // Modo /24: cada /24 = V4_CELL_24×V4_CELL_24 pixels (2×2)
      const detail_all   = detailData?.all
      const detail_own   = detailData?.own
      const detail_third = detailData?.third

      const paint24 = (px: number, py: number, r: number, g: number, b: number) => {
        for (let cy = 0; cy < V4_CELL_24; cy++) {
          for (let cx = 0; cx < V4_CELL_24; cx++) {
            const i = ((py + cy) * ZOOM_CANVAS + (px + cx)) * 4
            pixels[i] = r; pixels[i+1] = g; pixels[i+2] = b; pixels[i+3] = 255
          }
        }
      }

      for (const { dx, dy, b } of blockIndices) {
        const bk = String(b)
        const ownCs   = detail_own?.[bk]
        const thirdCs = detail_third?.[bk]
        const allCs   = detail_all?.[bk]

        const ox2 = dx * V4_CELL
        const oy2 = dy * V4_CELL

        if (isPeerMode && (ownCs || thirdCs)) {
          const ownSet   = new Set(ownCs ?? [])
          const thirdSet = new Set(thirdCs ?? [])
          const combined = new Set([...(ownCs ?? []), ...(thirdCs ?? [])])
          for (const c of combined) {
            const sp  = SUB_POS_FROM_C[c]
            const qx  = sp % 16
            const qy  = Math.floor(sp / 16)
            const px  = ox2 + qx * V4_CELL_24
            const py  = oy2 + qy * V4_CELL_24
            const inO = ownSet.has(c)
            const inT = thirdSet.has(c)
            if (inO && inT)    paint24(px, py, Math.round((or+tr)/2), Math.round((og+tg)/2), Math.round((ob+tb)/2))
            else if (inO)      paint24(px, py, or, og, ob)
            else               paint24(px, py, tr, tg, tb)
          }
        } else if (allCs) {
          for (const c of allCs) {
            const sp = SUB_POS_FROM_C[c]
            const qx = sp % 16
            const qy = Math.floor(sp / 16)
            paint24(ox2 + qx * V4_CELL_24, oy2 + qy * V4_CELL_24, ar, ag, ab)
          }
        }
      }
    } else {
      // Modo /16 (fallback enquanto carrega)
      const paint16 = (dx: number, dy: number, r: number, g: number, b: number, opacity: number) => {
        for (let cy = 0; cy < V4_CELL; cy++) {
          for (let cx = 0; cx < V4_CELL; cx++) {
            const i = ((dy * V4_CELL + cy) * ZOOM_CANVAS + (dx * V4_CELL + cx)) * 4
            pixels[i]   = Math.round(pixels[i]   * (1-opacity) + r * opacity)
            pixels[i+1] = Math.round(pixels[i+1] * (1-opacity) + g * opacity)
            pixels[i+2] = Math.round(pixels[i+2] * (1-opacity) + b * opacity)
          }
        }
      }
      for (const { dx, dy, blockIdx } of blockIndices) {
        if (isPeerMode && densityOwn && densityThird) {
          const oc = densityOwn[blockIdx]  ?? 0
          const tc = densityThird[blockIdx] ?? 0
          const total = oc + tc
          if (!total) continue
          const opacity = opacidadeDensidade(total)
          const p = oc / total
          paint16(dx, dy, Math.round(or*p+tr*(1-p)), Math.round(og*p+tg*(1-p)), Math.round(ob*p+tb*(1-p)), opacity)
        } else if (densityAll) {
          const count = densityAll[blockIdx]
          if (!count) continue
          paint16(dx, dy, ar, ag, ab, opacidadeDensidade(count))
        }
      }
    }

    ctx.putImageData(new ImageData(pixels, ZOOM_CANVAS, ZOOM_CANVAS), 0, 0)
  }, [blockIndices, slashEight, densityAll, densityOwn, densityThird, isPeerMode, hasDetail, detailData])

  // Mouse over
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const scaleX = ZOOM_CANVAS / rect.width
    const scaleY = ZOOM_CANVAS / rect.height
    const cx = (e.clientX - rect.left) * scaleX
    const cy = (e.clientY - rect.top)  * scaleY
    const cssX = e.clientX - rect.left
    const cssY = e.clientY - rect.top

    const dx = Math.min(15, Math.floor(cx / V4_CELL))
    const dy = Math.min(15, Math.floor(cy / V4_CELL))
    const blockIdx = POS_TO_D16[(sy * 16 + dy) * 256 + (sx * 16 + dx)]
    const b = blockIdx & 0xFF

    if (hasDetail) {
      // Tooltip /24
      const qx = Math.min(15, Math.floor((cx % V4_CELL) / V4_CELL_24))
      const qy = Math.min(15, Math.floor((cy % V4_CELL) / V4_CELL_24))
      const c  = SUB_C_FROM_POS[qy * 16 + qx]
      const prefix = `${slashEight}.${b}.${c}.0/24`
      const ownCs   = detailData?.own?.[String(b)]
      const thirdCs = detailData?.third?.[String(b)]
      const allCs   = detailData?.all?.[String(b)]
      const inOwn   = ownCs?.includes(c)  ?? false
      const inThird = thirdCs?.includes(c) ?? false
      const present = allCs?.includes(c)   ?? false
      setTooltip({ cssX, cssY, prefix, is24: true, present: isPeerMode ? (inOwn || inThird) : present,
        ownCount: inOwn ? 1 : 0, thirdCount: inThird ? 1 : 0 })
    } else {
      // Tooltip /16
      const prefix = block16ToPrefix(blockIdx)
      const activeDensity = isPeerMode && densityOwn && densityThird
        ? densityOwn[blockIdx] + (densityThird[blockIdx] ?? 0)
        : densityAll?.[blockIdx] ?? 0
      const oc = densityOwn?.[blockIdx] ?? 0
      const tc = densityThird?.[blockIdx] ?? 0
      setTooltip({ cssX, cssY, prefix, is24: false, totalCount: activeDensity, ownCount: oc, thirdCount: tc })
    }
  }, [sx, sy, slashEight, hasDetail, detailData, densityAll, densityOwn, densityThird, isPeerMode])

  const handleMouseLeave = useCallback(() => setTooltip(null), [])

  // Stats /24
  const stats = useMemo(() => {
    if (hasDetail) {
      const detail_all   = detailData?.all
      const detail_own   = detailData?.own
      const detail_third = detailData?.third

      const list: string[] = []
      let count = 0
      for (const { b } of blockIndices) {
        const bk = String(b)
        const cs = isPeerMode
          ? [...new Set([...(detail_own?.[bk] ?? []), ...(detail_third?.[bk] ?? [])])]
          : (detail_all?.[bk] ?? [])
        for (const c of cs) {
          count++
          if (count <= 30) list.push(`${slashEight}.${b}.${c}.0/24`)
        }
      }
      return { level: '/24' as const, count, list: count <= 30 ? list : [] }
    }
    // Stats /16 (loading fallback)
    const activeDensity = isPeerMode && densityOwn && densityThird
      ? densityOwn.map((v, i) => v + (densityThird![i] ?? 0))
      : densityAll
    if (!activeDensity) return { level: '/16' as const, count: 0, list: [] }
    const active = blockIndices.filter(({ blockIdx }) => activeDensity[blockIdx] > 0)
    return {
      level: '/16' as const,
      count: active.length,
      list: active.length <= 30 ? active.map(({ blockIdx }) => block16ToPrefix(blockIdx)) : [],
    }
  }, [hasDetail, detailData, blockIndices, densityAll, densityOwn, densityThird, isPeerMode, slashEight])

  return (
    <ModalAcessivel idTitulo={idTitulo} onClose={onClose}>
        {/* Canvas */}
        <div className="flex-shrink-0">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h3 id={idTitulo} className="font-mono font-semibold text-gray-900 text-sm">{slashEight}.0.0.0/8</h3>
              {loadingDetail && (
                <span className="text-xs text-gray-400 animate-pulse">carregando /24…</span>
              )}
            </div>
            <button type="button" onClick={onClose} aria-label="Fechar" className="text-gray-600 hover:text-gray-900 text-2xl leading-none ml-4 min-h-[28px] min-w-[28px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primario-700"><span aria-hidden="true">&times;</span></button>
          </div>
          <div className="relative">
            <canvas
              ref={canvasRef}
              width={ZOOM_CANVAS}
              height={ZOOM_CANVAS}
              style={{
                width: ZOOM_CSS, height: ZOOM_CSS,
                display: 'block',
                border: '1px solid #e2e8f0',
                borderRadius: 4,
                imageRendering: 'pixelated',
                cursor: 'crosshair',
              }}
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
            />
            {/* Grade /16 (sempre visível) */}
            <svg
              viewBox={`0 0 ${ZOOM_CANVAS} ${ZOOM_CANVAS}`}
              style={{ position: 'absolute', top: 0, left: 0, width: ZOOM_CSS, height: ZOOM_CSS, pointerEvents: 'none' }}
            >
              {Array.from({ length: 15 }, (_, i) => {
                const pos = (i + 1) * V4_CELL
                return (
                  <g key={i}>
                    <line x1={0} y1={pos} x2={ZOOM_CANVAS} y2={pos} stroke="#475569" strokeWidth="0.8" strokeOpacity="0.5" />
                    <line x1={pos} y1={0} x2={pos} y2={ZOOM_CANVAS} stroke="#475569" strokeWidth="0.8" strokeOpacity="0.5" />
                  </g>
                )
              })}
            </svg>
            {/* Tooltip */}
            {tooltip && (
              <div
                className="absolute z-10 bg-white border border-gray-200 rounded shadow-md px-2 py-1.5 pointer-events-none text-xs"
                style={{
                  left: tooltip.cssX + 10,
                  top: Math.max(0, tooltip.cssY - 30),
                  transform: tooltip.cssX > ZOOM_CSS * 0.65 ? 'translateX(-110%)' : undefined,
                  maxWidth: 200,
                }}
              >
                <div className="font-mono font-semibold text-gray-900">{tooltip.prefix}</div>
                {tooltip.is24 ? (
                  isPeerMode ? (
                    <div className="mt-0.5 space-y-0.5">
                      {(tooltip.ownCount ?? 0) > 0   && <div style={{ color: COLOR_OWN   }} className="text-xs">prefixo próprio</div>}
                      {(tooltip.thirdCount ?? 0) > 0  && <div style={{ color: COLOR_THIRD }} className="text-xs">prefixo de terceiro</div>}
                      {!(tooltip.ownCount ?? 0) && !(tooltip.thirdCount ?? 0) && <div className="text-gray-300 text-xs">sem dados</div>}
                    </div>
                  ) : (
                    <div className="mt-0.5 text-xs" style={{ color: (tooltip.present) ? COLOR_ALL : undefined }}>
                      {tooltip.present ? 'presente neste IXP' : <span className="text-gray-300">sem dados</span>}
                    </div>
                  )
                ) : (
                  isPeerMode ? (
                    <div className="mt-0.5 space-y-0.5">
                      {(tooltip.ownCount ?? 0) > 0   && <div style={{ color: COLOR_OWN   }} className="text-xs">{tooltip.ownCount} /24 próprios</div>}
                      {(tooltip.thirdCount ?? 0) > 0  && <div style={{ color: COLOR_THIRD }} className="text-xs">{tooltip.thirdCount} /24 de terceiros</div>}
                      {!(tooltip.totalCount ?? 0) && <div className="text-gray-300 text-xs">sem dados</div>}
                    </div>
                  ) : (
                    <div className="mt-0.5 text-xs" style={{ color: (tooltip.totalCount ?? 0) > 0 ? COLOR_ALL : undefined }}>
                      {(tooltip.totalCount ?? 0) > 0
                        ? `${tooltip.totalCount} /24${(tooltip.totalCount ?? 0) !== 1 ? 's' : ''}`
                        : <span className="text-gray-300">sem dados</span>}
                    </div>
                  )
                )}
              </div>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {hasDetail ? 'Cada ponto = /24 · Grade = /16' : 'Cada célula = /16'}
          </p>
        </div>

        {/* Stats */}
        <div className="min-w-44 max-w-64 overflow-y-auto">
          <div className="text-xs font-semibold text-gray-700 mb-2">
            {palavra(stats.count, 'Bloco', 'Blocos')} {stats.level} {palavra(stats.count, 'presente', 'presentes')}
          </div>
          <div className="text-sm space-y-1 mb-3 text-gray-700">
            <div>
              <span className="font-semibold">{stats.count.toLocaleString('pt-BR')}</span>
              <span className="text-gray-500"> {palavra(stats.count, 'bloco', 'blocos')} {stats.level}</span>
            </div>
          </div>
          {stats.list.length > 0 && (
            <>
              <div className="text-xs text-gray-400 mb-1">{palavra(stats.count, 'Bloco', 'Blocos')} {stats.level}:</div>
              <div className="space-y-0.5 max-h-80 overflow-y-auto">
                {stats.list.map(p => (
                  <div key={p} className="text-xs font-mono text-gray-700 leading-tight">{p}</div>
                ))}
              </div>
            </>
          )}
        </div>
    </ModalAcessivel>
  )
}

// ============================================================
// Dashboard: zoom global IPv4 /8 → /24
// ============================================================

interface ZoomDashV4Props {
  sx: number
  sy: number
  slashEight: number
  activeLayer: LayerKey | string
  layerColor: string
  density: number[]     // density array for activeLayer (65536 values)
  date?: string
  /** Não busca o detalhe /24 na API (camadas que não existem lá): mostra a densidade por /16. */
  semDetalhe?: boolean
  onClose: () => void
}

interface Tooltip4Dash {
  cssX: number
  cssY: number
  prefix: string
  is24: boolean
  present: boolean
  count?: number
}

export function ZoomModalDashV4({
  sx, sy, slashEight,
  activeLayer, layerColor, density,
  date, semDetalhe, onClose,
}: ZoomDashV4Props) {
  const idTitulo = useId()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [tooltip, setTooltip] = useState<Tooltip4Dash | null>(null)

  const { data: detailData, isLoading: loadingDetail } = useQuery({
    queryKey: ['hilbert-v4-detail', slashEight, activeLayer, date],
    queryFn: () => fetchHilbertV4Detail(slashEight, activeLayer, date),
    enabled: !semDetalhe,
    staleTime: Infinity, gcTime: Infinity,
  })

  const hasDetail = !!detailData

  const blockIndices = useMemo(() => {
    const arr: { dx: number; dy: number; blockIdx: number; b: number }[] = []
    for (let dy = 0; dy < 16; dy++) {
      for (let dx = 0; dx < 16; dx++) {
        const blockIdx = POS_TO_D16[(sy * 16 + dy) * 256 + (sx * 16 + dx)]
        arr.push({ dx, dy, blockIdx, b: blockIdx & 0xFF })
      }
    }
    return arr
  }, [sx, sy])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const [lr, lg, lb] = hexToRGB(layerColor)
    const [br, bg, bb] = ianaColorRGB(slashEight)

    const pixels = new Uint8ClampedArray(ZOOM_CANVAS * ZOOM_CANVAS * 4)
    for (let i = 0; i < pixels.length; i += 4) {
      pixels[i] = br; pixels[i+1] = bg; pixels[i+2] = bb; pixels[i+3] = 255
    }

    if (hasDetail) {
      const paint24 = (px: number, py: number) => {
        for (let cy = 0; cy < V4_CELL_24; cy++) {
          for (let cx = 0; cx < V4_CELL_24; cx++) {
            const i = ((py + cy) * ZOOM_CANVAS + (px + cx)) * 4
            pixels[i] = lr; pixels[i+1] = lg; pixels[i+2] = lb; pixels[i+3] = 255
          }
        }
      }
      for (const { dx, dy, b } of blockIndices) {
        const cs = detailData?.[String(b)]
        if (!cs) continue
        const ox2 = dx * V4_CELL
        const oy2 = dy * V4_CELL
        for (const c of cs) {
          const sp = SUB_POS_FROM_C[c]
          paint24(ox2 + (sp % 16) * V4_CELL_24, oy2 + Math.floor(sp / 16) * V4_CELL_24)
        }
      }
    } else {
      for (const { dx, dy, blockIdx } of blockIndices) {
        const count = density[blockIdx]
        if (!count) continue
        const opacity = opacidadeDensidade(count)
        for (let cy = 0; cy < V4_CELL; cy++) {
          for (let cx = 0; cx < V4_CELL; cx++) {
            const i = ((dy * V4_CELL + cy) * ZOOM_CANVAS + (dx * V4_CELL + cx)) * 4
            pixels[i]   = Math.round(pixels[i]   * (1-opacity) + lr * opacity)
            pixels[i+1] = Math.round(pixels[i+1] * (1-opacity) + lg * opacity)
            pixels[i+2] = Math.round(pixels[i+2] * (1-opacity) + lb * opacity)
          }
        }
      }
    }

    ctx.putImageData(new ImageData(pixels, ZOOM_CANVAS, ZOOM_CANVAS), 0, 0)
  }, [blockIndices, slashEight, density, layerColor, hasDetail, detailData])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const scaleX = ZOOM_CANVAS / rect.width
    const scaleY = ZOOM_CANVAS / rect.height
    const cx = (e.clientX - rect.left) * scaleX
    const cy = (e.clientY - rect.top)  * scaleY
    const cssX = e.clientX - rect.left
    const cssY = e.clientY - rect.top

    const dx = Math.min(15, Math.floor(cx / V4_CELL))
    const dy = Math.min(15, Math.floor(cy / V4_CELL))
    const blockIdx = POS_TO_D16[(sy * 16 + dy) * 256 + (sx * 16 + dx)]
    const b = blockIdx & 0xFF

    if (hasDetail) {
      const qx = Math.min(15, Math.floor((cx % V4_CELL) / V4_CELL_24))
      const qy = Math.min(15, Math.floor((cy % V4_CELL) / V4_CELL_24))
      const c = SUB_C_FROM_POS[qy * 16 + qx]
      const prefix = `${slashEight}.${b}.${c}.0/24`
      const cs = detailData?.[String(b)]
      const present = cs?.includes(c) ?? false
      setTooltip({ cssX, cssY, prefix, is24: true, present })
    } else {
      const prefix = block16ToPrefix(blockIdx)
      const count = density[blockIdx] ?? 0
      setTooltip({ cssX, cssY, prefix, is24: false, present: count > 0, count })
    }
  }, [sx, sy, slashEight, hasDetail, detailData, density])

  const handleMouseLeave = useCallback(() => setTooltip(null), [])

  const stats = useMemo(() => {
    if (hasDetail) {
      const list: string[] = []
      let count = 0
      for (const { b } of blockIndices) {
        for (const c of (detailData?.[String(b)] ?? [])) {
          count++
          if (count <= 30) list.push(`${slashEight}.${b}.${c}.0/24`)
        }
      }
      return { level: '/24' as const, count, list: count <= 30 ? list : [] }
    }
    const active = blockIndices.filter(({ blockIdx }) => (density[blockIdx] ?? 0) > 0)
    return {
      level: '/16' as const,
      count: active.length,
      list: active.length <= 30 ? active.map(({ blockIdx }) => block16ToPrefix(blockIdx)) : [],
    }
  }, [hasDetail, detailData, blockIndices, density, slashEight])

  return (
    <ModalAcessivel idTitulo={idTitulo} onClose={onClose}>
        <div className="flex-shrink-0">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h3 id={idTitulo} className="font-mono font-semibold text-gray-900 text-sm">{slashEight}.0.0.0/8</h3>
              {loadingDetail && (
                <span className="text-xs text-gray-400 animate-pulse">carregando /24…</span>
              )}
            </div>
            <button type="button" onClick={onClose} aria-label="Fechar" className="text-gray-600 hover:text-gray-900 text-2xl leading-none ml-4 min-h-[28px] min-w-[28px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primario-700"><span aria-hidden="true">&times;</span></button>
          </div>
          <div className="relative">
            <canvas
              ref={canvasRef}
              width={ZOOM_CANVAS}
              height={ZOOM_CANVAS}
              style={{
                width: ZOOM_CSS, height: ZOOM_CSS,
                display: 'block',
                border: '1px solid #e2e8f0',
                borderRadius: 4,
                imageRendering: 'pixelated',
                cursor: 'crosshair',
              }}
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
            />
            <svg
              viewBox={`0 0 ${ZOOM_CANVAS} ${ZOOM_CANVAS}`}
              style={{ position: 'absolute', top: 0, left: 0, width: ZOOM_CSS, height: ZOOM_CSS, pointerEvents: 'none' }}
            >
              {Array.from({ length: 15 }, (_, i) => {
                const pos = (i + 1) * V4_CELL
                return (
                  <g key={i}>
                    <line x1={0} y1={pos} x2={ZOOM_CANVAS} y2={pos} stroke="#475569" strokeWidth="0.8" strokeOpacity="0.5" />
                    <line x1={pos} y1={0} x2={pos} y2={ZOOM_CANVAS} stroke="#475569" strokeWidth="0.8" strokeOpacity="0.5" />
                  </g>
                )
              })}
            </svg>
            {tooltip && (
              <div
                className="absolute z-10 bg-white border border-gray-200 rounded shadow-md px-2 py-1.5 pointer-events-none text-xs"
                style={{
                  left: tooltip.cssX + 10,
                  top: Math.max(0, tooltip.cssY - 30),
                  transform: tooltip.cssX > ZOOM_CSS * 0.65 ? 'translateX(-110%)' : undefined,
                  maxWidth: 200,
                }}
              >
                <div className="font-mono font-semibold text-gray-900">{tooltip.prefix}</div>
                {tooltip.is24 ? (
                  <div className="mt-0.5 text-xs" style={{ color: tooltip.present ? layerColor : undefined }}>
                    {tooltip.present ? 'presente' : <span className="text-gray-300">sem dados</span>}
                  </div>
                ) : (
                  <div className="mt-0.5 text-xs" style={{ color: (tooltip.count ?? 0) > 0 ? layerColor : undefined }}>
                    {(tooltip.count ?? 0) > 0
                      ? `${tooltip.count} ${palavra(tooltip.count, 'bloco', 'blocos')} /24`
                      : <span className="text-gray-300">sem dados</span>}
                  </div>
                )}
              </div>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {hasDetail ? 'Cada ponto = /24 · Grade = /16' : 'Cada célula = /16'}
          </p>
        </div>

        <div className="min-w-44 max-w-64 overflow-y-auto">
          <div className="text-xs font-semibold text-gray-700 mb-2">
            {palavra(stats.count, 'Bloco', 'Blocos')} {stats.level} {palavra(stats.count, 'presente', 'presentes')}
          </div>
          <div className="text-sm space-y-1 mb-3 text-gray-700">
            <div>
              <span className="font-semibold">{stats.count.toLocaleString('pt-BR')}</span>
              <span className="text-gray-500"> {palavra(stats.count, 'bloco', 'blocos')} {stats.level}</span>
            </div>
          </div>
          {stats.list.length > 0 && (
            <>
              <div className="text-xs text-gray-400 mb-1">{palavra(stats.count, 'Bloco', 'Blocos')} {stats.level}:</div>
              <div className="space-y-0.5 max-h-80 overflow-y-auto">
                {stats.list.map(p => (
                  <div key={p} className="text-xs font-mono text-gray-700 leading-tight">{p}</div>
                ))}
              </div>
            </>
          )}
        </div>
    </ModalAcessivel>
  )
}

// ============================================================
// IPv6 /20 zoom modal
// ============================================================

const V6_STEP = 64
const V6_CELL = ZOOM_CANVAS / V6_STEP  // 8px por /32

interface ZoomV6Props {
  config: V6BlockConfig
  gx: number
  gy: number
  allCells: number[] | null
  ownCells: number[] | null
  thirdCells: number[] | null
  isPeerMode: boolean
  /** Cor para modo não-peer (padrão: indigo IXP). */
  color?: string
  onClose: () => void
}

interface Tooltip6 { cssX: number; cssY: number; prefix: string; inOwn: boolean; inThird: boolean; inAll: boolean }

export function ZoomModalV6({
  config, gx, gy,
  allCells, ownCells, thirdCells,
  isPeerMode, color, onClose,
}: ZoomV6Props) {
  const idTitulo = useId()
  const singleColor = color ?? COLOR_ALL
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [tooltip, setTooltip] = useState<Tooltip6 | null>(null)
  const isLegacy = config.gridSize === 256
  const ox = gx * V6_STEP
  const oy = gy * V6_STEP

  // Células dentro deste bloco /20, com posições locais pré-calculadas
  const cellsInBlock = useMemo(() => {
    const grid = isLegacy ? null : getGrid1024()
    const inBlock = (d: number) => {
      const cx = isLegacy ? GRID16[d].x : grid!.x[d]
      const cy = isLegacy ? GRID16[d].y : grid!.y[d]
      return cx >= ox && cx < ox + V6_STEP && cy >= oy && cy < oy + V6_STEP
    }
    return {
      all:   (allCells   ?? []).filter(inBlock),
      own:   (ownCells   ?? []).filter(inBlock),
      third: (thirdCells ?? []).filter(inBlock),
    }
  }, [isLegacy, ox, oy, allCells, ownCells, thirdCells])

  // Mapa reverso (lx*64+ly) → cell index, para mouse over O(1)
  const localPosMap = useMemo(() => {
    const map = new Map<number, number>()
    const grid = isLegacy ? null : getGrid1024()
    const allActive = [...new Set([...cellsInBlock.all, ...cellsInBlock.own, ...cellsInBlock.third])]
    for (const d of allActive) {
      const lx = (isLegacy ? GRID16[d].x : grid!.x[d]) - ox
      const ly = (isLegacy ? GRID16[d].y : grid!.y[d]) - oy
      map.set(ly * 64 + lx, d)
    }
    return map
  }, [cellsInBlock, isLegacy, ox, oy])

  const activeCells = isPeerMode
    ? [...new Set([...cellsInBlock.own, ...cellsInBlock.third])]
    : cellsInBlock.all

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const [ar, ag, ab] = hexToRGB(singleColor)
    const [or, og, ob] = hexToRGB(COLOR_OWN)
    const [tr, tg, tb] = hexToRGB(COLOR_THIRD)

    const pixels = new Uint8ClampedArray(ZOOM_CANVAS * ZOOM_CANVAS * 4)
    for (let i = 0; i < pixels.length; i += 4) {
      pixels[i] = 226; pixels[i+1] = 232; pixels[i+2] = 240; pixels[i+3] = 255
    }

    const grid = isLegacy ? null : getGrid1024()
    const getPos = (d: number): [number, number] =>
      isLegacy
        ? [GRID16[d].x - ox, GRID16[d].y - oy]
        : [grid!.x[d] - ox, grid!.y[d] - oy]

    const paint = (lx: number, ly: number, r: number, g: number, b: number) => {
      for (let cy = 0; cy < V6_CELL; cy++) {
        for (let cx = 0; cx < V6_CELL; cx++) {
          const i = ((ly * V6_CELL + cy) * ZOOM_CANVAS + (lx * V6_CELL + cx)) * 4
          pixels[i] = r; pixels[i+1] = g; pixels[i+2] = b; pixels[i+3] = 255
        }
      }
    }

    if (isPeerMode) {
      const ownSet   = new Set(cellsInBlock.own)
      const thirdSet = new Set(cellsInBlock.third)
      for (const d of activeCells) {
        const [lx, ly] = getPos(d)
        const inO = ownSet.has(d)
        const inT = thirdSet.has(d)
        if (inO && inT)   paint(lx, ly, Math.round((or+tr)/2), Math.round((og+tg)/2), Math.round((ob+tb)/2))
        else if (inO)     paint(lx, ly, or, og, ob)
        else              paint(lx, ly, tr, tg, tb)
      }
    } else {
      for (const d of cellsInBlock.all) {
        const [lx, ly] = getPos(d)
        paint(lx, ly, ar, ag, ab)
      }
    }

    ctx.putImageData(new ImageData(pixels, ZOOM_CANVAS, ZOOM_CANVAS), 0, 0)
  }, [isLegacy, ox, oy, cellsInBlock, activeCells, isPeerMode, singleColor])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const scaleX = ZOOM_CANVAS / rect.width
    const scaleY = ZOOM_CANVAS / rect.height
    const cx = (e.clientX - rect.left) * scaleX
    const cy = (e.clientY - rect.top)  * scaleY
    const lx = Math.min(63, Math.floor(cx / V6_CELL))
    const ly = Math.min(63, Math.floor(cy / V6_CELL))
    const d  = localPosMap.get(ly * 64 + lx)
    if (d === undefined) { setTooltip(null); return }

    const ownSet   = new Set(cellsInBlock.own)
    const thirdSet = new Set(cellsInBlock.third)
    const allSet   = new Set(cellsInBlock.all)
    setTooltip({
      cssX: e.clientX - rect.left,
      cssY: e.clientY - rect.top,
      prefix: cellIndexToV6Prefix(d, config),
      inOwn:   ownSet.has(d),
      inThird: thirdSet.has(d),
      inAll:   allSet.has(d),
    })
  }, [localPosMap, cellsInBlock, config])

  const handleMouseLeave = useCallback(() => setTooltip(null), [])

  // Prefixo /20 para o título
  const slashTwentyPrefix = useMemo(() => {
    if (!activeCells.length) return `${config.rir} /20`
    const minCell = Math.min(...activeCells)
    return cellIndexToV6Prefix(minCell & ~0xFFF, config).replace('::/32', '::/20')
  }, [activeCells, config])

  const slash32Count = activeCells.length
  const showList = slash32Count > 0 && slash32Count <= 20
  const prefixList = showList
    ? [...new Set(activeCells)].sort((a, b) => a - b).map(d => cellIndexToV6Prefix(d, config))
    : []

  const gridLines = Array.from({ length: 15 }, (_, i) => (i + 1) * (ZOOM_CANVAS / 16))

  return (
    <ModalAcessivel idTitulo={idTitulo} onClose={onClose}>
        {/* Canvas */}
        <div className="flex-shrink-0">
          <div className="flex items-center justify-between mb-2">
            <h3 id={idTitulo} className="font-mono font-semibold text-gray-900 text-sm">{slashTwentyPrefix}</h3>
            <button type="button" onClick={onClose} aria-label="Fechar" className="text-gray-600 hover:text-gray-900 text-2xl leading-none ml-4 min-h-[28px] min-w-[28px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primario-700"><span aria-hidden="true">&times;</span></button>
          </div>
          <div className="relative">
            <canvas
              ref={canvasRef}
              width={ZOOM_CANVAS}
              height={ZOOM_CANVAS}
              style={{
                width: ZOOM_CSS, height: ZOOM_CSS,
                display: 'block',
                border: '1px solid #e2e8f0',
                borderRadius: 4,
                imageRendering: 'pixelated',
                cursor: 'crosshair',
              }}
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
            />
            {/* Grade /28 */}
            <svg
              viewBox={`0 0 ${ZOOM_CANVAS} ${ZOOM_CANVAS}`}
              style={{ position: 'absolute', top: 0, left: 0, width: ZOOM_CSS, height: ZOOM_CSS, pointerEvents: 'none' }}
            >
              {gridLines.map((pos, i) => (
                <g key={i}>
                  <line x1={0} y1={pos} x2={ZOOM_CANVAS} y2={pos} stroke="#475569" strokeWidth="0.8" strokeOpacity="0.5" />
                  <line x1={pos} y1={0} x2={pos} y2={ZOOM_CANVAS} stroke="#475569" strokeWidth="0.8" strokeOpacity="0.5" />
                </g>
              ))}
            </svg>
            {/* Tooltip */}
            {tooltip && (
              <div
                className="absolute z-10 bg-white border border-gray-200 rounded shadow-md px-2 py-1.5 pointer-events-none text-xs"
                style={{
                  left: tooltip.cssX + 10,
                  top: Math.max(0, tooltip.cssY - 30),
                  transform: tooltip.cssX > ZOOM_CSS * 0.65 ? 'translateX(-110%)' : undefined,
                }}
              >
                <div className="font-mono font-semibold text-gray-900 text-xs whitespace-nowrap">{tooltip.prefix}</div>
                <div className="mt-0.5 space-y-0.5">
                  {isPeerMode ? (
                    <>
                      {tooltip.inOwn   && <div style={{ color: COLOR_OWN   }} className="text-xs">prefixo próprio</div>}
                      {tooltip.inThird && <div style={{ color: COLOR_THIRD }} className="text-xs">prefixo de terceiro</div>}
                    </>
                  ) : (
                    <div style={{ color: singleColor }} className="text-xs">presente</div>
                  )}
                </div>
              </div>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-1">Grade: /28 · Cada ponto = /32</p>
        </div>

        {/* Stats */}
        <div className="min-w-44 max-w-64 overflow-y-auto">
          <div className="text-xs font-semibold text-gray-700 mb-2">{palavra(slash32Count, 'Bloco', 'Blocos')} /32 {palavra(slash32Count, 'presente', 'presentes')}</div>
          <div className="text-sm space-y-1 mb-3 text-gray-700">
            <div>
              <span className="font-semibold">{slash32Count.toLocaleString('pt-BR')}</span>
              <span className="text-gray-500"> {palavra(slash32Count, 'bloco', 'blocos')} /32</span>
            </div>
          </div>
          {showList && (
            <>
              <div className="text-xs text-gray-400 mb-1">{palavra(slash32Count, 'Bloco', 'Blocos')} /32:</div>
              <div className="space-y-0.5">
                {prefixList.map(p => (
                  <div key={p} className="text-xs font-mono text-gray-700 leading-tight">{p}</div>
                ))}
              </div>
            </>
          )}
        </div>
    </ModalAcessivel>
  )
}
