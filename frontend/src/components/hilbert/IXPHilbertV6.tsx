/**
 * Mapa de Hilbert IPv6 para a página de IXP.
 * 6 blocos RIR com índices esparsos de /32.
 * Modo total: indigo. Modo peer: azul (próprios) vs laranja (terceiros).
 */
import { useRef, useEffect, useState, useCallback, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchIXPHilbertV6 } from '../../services/api'
import {
  V6_BLOCKS,
  getV6BgPixels,
  GRID16,
  getGrid1024,
  cellIndexToV6Prefix,
  mouseToBlockV6,
  hexToRGB,
  type V6BlockConfig,
} from './hilbert'
import { renderV6Block } from './HilbertMapV6Block'
import { ZoomModalV6 } from './IXPHilbertZoom'
import type { IXPHilbertV6Blocks } from '../../types/api'
import { QuadrantesTeclado } from './QuadrantesTeclado'
import { AneisIsoladas } from './AneisIsoladas'
import { LEGENDA_MARCADOR, celulasIsoladas, posicaoCelulaV6, RAIO_MARCADOR_PX, TRACO_MARCADOR_PX } from './isoladas'
import { nomeAmpliar, prefixoQuadranteV6 } from './quadrantes'

// Passo de grade = /20 para todos os blocos:
// - Legado /16 (gridSize=256): step=64 → 4×4 = 16 quadrados de /20
// - RIR /12  (gridSize=1024): step=64 → 16×16 = 256 quadrados de /20
const V6_STEP = 64

function computeActiveV6Squares(cells: number[] | null, config: V6BlockConfig): Set<number> {
  if (!cells?.length) return new Set()
  const numCols = config.gridSize / V6_STEP
  const active = new Set<number>()
  if (config.gridSize === 256) {
    for (const d of cells) {
      active.add(Math.floor(GRID16[d].y / V6_STEP) * numCols + Math.floor(GRID16[d].x / V6_STEP))
    }
  } else {
    const grid = getGrid1024()
    for (const d of cells) {
      active.add(Math.floor(grid.y[d] / V6_STEP) * numCols + Math.floor(grid.x[d] / V6_STEP))
    }
  }
  return active
}

const COLOR_ALL   = '#6366f1'   // indigo — total IXP
const COLOR_OWN   = '#3b82f6'   // blue — prefixos próprios
const COLOR_THIRD = '#f97316'   // orange — prefixos de terceiros

// ---------------------------------------------------------------------------
// Dual-layer renderer (peer mode)
// ---------------------------------------------------------------------------

function renderV6BlockDual(
  ctx: CanvasRenderingContext2D,
  config: V6BlockConfig,
  ownCells: number[],
  thirdCells: number[],
) {
  const { canvasPx, gridSize } = config
  const pixels = new Uint8ClampedArray(getV6BgPixels(canvasPx))
  const [or, og, ob] = hexToRGB(COLOR_OWN)
  const [tr, tg, tb] = hexToRGB(COLOR_THIRD)

  const ownSet   = new Set(ownCells)
  const thirdSet = new Set(thirdCells)
  const all      = new Set([...ownCells, ...thirdCells])

  const paint = (d: number, r: number, g: number, b: number) => {
    if (gridSize === 256) {
      const ox = GRID16[d].x * 2
      const oy = GRID16[d].y * 2
      for (let cy = 0; cy < 2; cy++) {
        const row = (oy + cy) * canvasPx
        for (let cx = 0; cx < 2; cx++) {
          const i = (row + ox + cx) * 4
          pixels[i] = r; pixels[i + 1] = g; pixels[i + 2] = b; pixels[i + 3] = 255
        }
      }
    } else {
      const grid = getGrid1024()
      const i = (grid.y[d] * canvasPx + grid.x[d]) * 4
      pixels[i] = r; pixels[i + 1] = g; pixels[i + 2] = b; pixels[i + 3] = 255
    }
  }

  for (const d of all) {
    const inOwn   = ownSet.has(d)
    const inThird = thirdSet.has(d)
    if (inOwn && inThird) {
      paint(d, Math.round((or + tr) / 2), Math.round((og + tg) / 2), Math.round((ob + tb) / 2))
    } else if (inOwn) {
      paint(d, or, og, ob)
    } else {
      paint(d, tr, tg, tb)
    }
  }
  ctx.putImageData(new ImageData(pixels, canvasPx, canvasPx), 0, 0)
}

// ---------------------------------------------------------------------------
// Single block component
// ---------------------------------------------------------------------------

interface BlockProps {
  config: V6BlockConfig
  allCells: number[] | null   // total mode
  ownCells: number[] | null   // peer mode
  thirdCells: number[] | null // peer mode
  isPeerMode: boolean
  cssWidth: number
}

function IXPV6Block({ config, allCells, ownCells, thirdCells, isPeerMode, cssWidth }: BlockProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [tooltip, setTooltip] = useState<{ d: number; cssX: number; cssY: number } | null>(null)
  const [zoomedSquare, setZoomedSquare] = useState<{ gx: number; gy: number } | null>(null)
  const [isHoveredClickable, setIsHoveredClickable] = useState(false)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    if (isPeerMode && ownCells !== null && thirdCells !== null) {
      renderV6BlockDual(ctx, config, ownCells, thirdCells)
    } else if (!isPeerMode && allCells !== null) {
      renderV6Block(ctx, config, allCells, COLOR_ALL, null)
    }
  }, [config, allCells, ownCells, thirdCells, isPeerMode])

  const hd = tooltip?.d ?? -1
  const ownSet   = useMemo(() => isPeerMode ? new Set(ownCells ?? [])   : null, [isPeerMode, ownCells])
  const thirdSet = useMemo(() => isPeerMode ? new Set(thirdCells ?? []) : null, [isPeerMode, thirdCells])

  // Quadrados /20 com dados (para destacar bordas)
  const activeCellsForGrid = useMemo(
    () => isPeerMode ? [...(ownCells ?? []), ...(thirdCells ?? [])] : (allCells ?? []),
    [isPeerMode, ownCells, thirdCells, allCells],
  )
  const activeSquares = useMemo(
    () => computeActiveV6Squares(activeCellsForGrid.length ? activeCellsForGrid : null, config),
    [activeCellsForGrid, config],
  )

  // gridScale converte coordenadas do canvas (0..canvasPx) → grade Hilbert (0..gridSize)
  // Para blocos /12: gridSize=canvasPx=1024, escala=1. Para legado: gridSize=256, canvasPx=512, escala=0.5
  const gridScale = config.gridSize / config.canvasPx
  const numCols = config.gridSize / V6_STEP

  const aneis = useMemo(() => {
    const pos = posicaoCelulaV6(config.gridSize)
    return celulasIsoladas(activeCellsForGrid, pos, config.gridSize, cssWidth).map(pos)
  }, [activeCellsForGrid, config.gridSize, cssWidth])
  const quadrantes = useMemo(() => [...activeSquares].map((idx) => {
    const col = idx % numCols
    const lin = Math.floor(idx / numCols)
    return { col, lin, nome: nomeAmpliar(prefixoQuadranteV6(config, col, lin)), aoAbrir: () => setZoomedSquare({ gx: col, gy: lin }) }
  }), [activeSquares, numCols, config])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const scale = config.canvasPx / rect.width
    const canvasX = (e.clientX - rect.left) * scale
    const canvasY = (e.clientY - rect.top) * scale
    setTooltip({
      d: mouseToBlockV6(canvasX, canvasY, config.canvasPx, config),
      cssX: e.clientX - rect.left,
      cssY: e.clientY - rect.top,
    })
    const gx = Math.floor(canvasX * gridScale / V6_STEP)
    const gy = Math.floor(canvasY * gridScale / V6_STEP)
    setIsHoveredClickable(activeSquares.has(gy * numCols + gx))
  }, [config, gridScale, numCols, activeSquares])

  const handleMouseLeave = useCallback(() => {
    setTooltip(null)
    setIsHoveredClickable(false)
  }, [])

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const scale = config.canvasPx / rect.width
    const canvasX = (e.clientX - rect.left) * scale
    const canvasY = (e.clientY - rect.top) * scale
    const gx = Math.floor(canvasX * gridScale / V6_STEP)
    const gy = Math.floor(canvasY * gridScale / V6_STEP)
    if (activeSquares.has(gy * numCols + gx)) {
      setZoomedSquare({ gx, gy })
    }
  }, [config, gridScale, numCols, activeSquares])

  const { gridSize } = config
  const isLegacy = gridSize === 256

  return (
    <div className="flex flex-col items-center gap-0.5">
      <span className="text-xs font-semibold text-gray-600 leading-none">{config.rir}</span>
      <span className="text-xs font-mono text-gray-400 leading-none">{config.label}</span>
      <div className="relative select-none mt-0.5" style={{ width: cssWidth, height: cssWidth }}>
        <canvas
          ref={canvasRef}
          width={config.canvasPx}
          height={config.canvasPx}
          style={{
            width: cssWidth,
            height: cssWidth,
            display: 'block',
            border: '1px solid #e2e8f0',
            borderRadius: 2,
            imageRendering: 'pixelated',
            cursor: isHoveredClickable ? 'pointer' : 'default',
          }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          onClick={handleClick}
        />
        {/* Grade /20 — borda mais forte se há dados no quadrado */}
        <svg
          viewBox={`0 0 ${gridSize} ${gridSize}`}
          style={{ position: 'absolute', top: 0, left: 0, width: cssWidth, height: cssWidth, pointerEvents: 'none', overflow: 'hidden', borderRadius: 2 }}
        >
          {Array.from({ length: numCols * numCols }, (_, idx) => {
            const gx = idx % numCols
            const gy = Math.floor(idx / numCols)
            const hasData = activeSquares.has(idx)
            return (
              <g key={idx}>
                <rect x={gx * V6_STEP} y={gy * V6_STEP}
                  width={V6_STEP} height={V6_STEP}
                  fill="none" stroke="#334155"
                  strokeWidth={isLegacy ? 0.6 : 2.5} strokeOpacity={0.40}
                />
                {hasData && <rect x={gx * V6_STEP} y={gy * V6_STEP}
                  width={V6_STEP} height={V6_STEP}
                  fill="none" stroke="#1e293b"
                  strokeWidth={isLegacy ? 2 : 8} strokeOpacity={0.55}
                />}
              </g>
            )
          })}
          <AneisIsoladas pontos={aneis} gridSize={gridSize} larguraCss={cssWidth} raioPx={RAIO_MARCADOR_PX} tracoPx={TRACO_MARCADOR_PX} />
        </svg>
        <QuadrantesTeclado lado={numCols} quadrantes={quadrantes} rotulo={`Quadrantes do mapa IPv6 ${config.label}, use as setas`} />
        {/* Tooltip */}
        {tooltip !== null && hd >= 0 && (
          <div
            className="absolute z-10 bg-white border border-gray-200 rounded shadow-md px-2 py-1.5 pointer-events-none"
            style={{
              left: tooltip.cssX + 8,
              top: Math.max(0, tooltip.cssY - 28),
              maxWidth: 220,
              transform: tooltip.cssX > cssWidth * 0.6 ? 'translateX(-110%)' : undefined,
            }}
          >
            <div className="font-mono font-semibold text-gray-900 text-xs whitespace-nowrap">
              {cellIndexToV6Prefix(hd, config)}
            </div>
            <div className="text-gray-500 text-xs">{config.rir} · {config.label}</div>
            {isPeerMode ? (
              <div className="mt-0.5 space-y-0.5">
                {ownSet?.has(hd)   && <div style={{ color: COLOR_OWN   }} className="text-xs">prefixo próprio</div>}
                {thirdSet?.has(hd) && <div style={{ color: COLOR_THIRD }} className="text-xs">prefixo de terceiro</div>}
                {!ownSet?.has(hd) && !thirdSet?.has(hd) && <div className="text-gray-300 text-xs">sem dados neste peer</div>}
              </div>
            ) : (
              <div className="mt-0.5">
                {(allCells ?? []).includes(hd)
                  ? <div style={{ color: COLOR_ALL }} className="text-xs">presente neste IXP</div>
                  : <div className="text-gray-300 text-xs">sem dados</div>
                }
              </div>
            )}
          </div>
        )}
      </div>

      {zoomedSquare && (
        <ZoomModalV6
          config={config}
          gx={zoomedSquare.gx}
          gy={zoomedSquare.gy}
          allCells={allCells}
          ownCells={ownCells}
          thirdCells={thirdCells}
          isPeerMode={isPeerMode}
          onClose={() => setZoomedSquare(null)}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface IXPHilbertV6Props {
  code: string
  date?: string
  peerList: number[]
  selectedPeer: number | null
  onSelectPeer: (asn: number | null) => void
  blockWidth?: number
}

export function IXPHilbertV6({
  code,
  date,
  peerList,
  selectedPeer,
  onSelectPeer,
  blockWidth = 240,
}: IXPHilbertV6Props) {
  const { data: totalData, isLoading: loadingTotal } = useQuery({
    queryKey: ['ixp-hilbert-v6', code, date],
    queryFn: () => fetchIXPHilbertV6(code, undefined, date),
    staleTime: Infinity, gcTime: Infinity,
  })

  const isPeerMode = selectedPeer !== null

  const { data: peerData, isLoading: loadingPeer } = useQuery({
    queryKey: ['ixp-hilbert-v6-peer', code, selectedPeer, date],
    queryFn: () => fetchIXPHilbertV6(code, selectedPeer!, date),
    enabled: isPeerMode,
    staleTime: Infinity, gcTime: Infinity,
  })

  const isLoading = loadingTotal || (isPeerMode && loadingPeer)

  return (
    <div className="space-y-3">
      {/* Controles */}
      <div className="flex items-center gap-3">
        <label className="text-xs text-gray-600 font-medium whitespace-nowrap">Visualizar:</label>
        <select
          value={selectedPeer ?? ''}
          onChange={(e) => onSelectPeer(e.target.value ? parseInt(e.target.value) : null)}
          className="text-xs border border-gray-200 rounded px-2 py-1.5 bg-white text-gray-800 focus:outline-none focus:ring-1 focus:ring-primario-400"
        >
          <option value="">Total IXP (todos os prefixos)</option>
          {peerList.map((asn) => (
            <option key={asn} value={asn}>AS{asn}</option>
          ))}
        </select>
        {isLoading && <span className="text-xs text-gray-400 animate-pulse">Carregando…</span>}
      </div>

      {/* Legenda */}
      {isPeerMode ? (
        <div className="flex flex-wrap gap-4 text-xs text-gray-600">
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm" style={{ background: COLOR_OWN }} />
            Prefixos próprios (AS{selectedPeer} é originador)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm" style={{ background: COLOR_THIRD }} />
            Prefixos de terceiros (repassados pelo AS{selectedPeer})
          </span>
        </div>
      ) : (
        <p className="text-xs text-gray-500">
          <span className="inline-block w-3 h-3 rounded-sm align-middle mr-1" style={{ background: COLOR_ALL }} />
          Prefixos IPv6 anunciados neste IXP. Cada célula = bloco /32. {LEGENDA_MARCADOR}
        </p>
      )}

      {/* Blocos — linha 1: Legado, LACNIC, ARIN / linha 2: RIPE, APNIC, AFRINIC */}
      {[V6_BLOCKS.slice(0, 3), V6_BLOCKS.slice(3)].map((row, ri) => (
        <div key={ri} className="flex flex-wrap gap-4">
          {row.map((config) => (
            <IXPV6Block
              key={config.id}
              config={config}
              allCells={totalData?.all?.[config.id] ?? null}
              ownCells={peerData?.own?.[config.id] ?? null}
              thirdCells={peerData?.third?.[config.id] ?? null}
              isPeerMode={isPeerMode}
              cssWidth={blockWidth}
            />
          ))}
        </div>
      ))}

      <p className="text-xs text-gray-400">
        Cada célula = bloco /32. Use o dropdown ou clique na tabela para selecionar um peer.
      </p>
    </div>
  )
}
