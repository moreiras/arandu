/**
 * Renderiza um bloco IPv6 (e.g. 2800::/12) como mapa de Hilbert em canvas.
 * Cada célula = um /32. Dados esparsos: apenas índices de células ativas.
 * Legado (256×256): 2 px/célula. Blocos /12 (1024×1024): 1 px/célula.
 */
import { useRef, useEffect, useState, useCallback, useMemo } from 'react'
import {
  GRID16,
  getGrid1024,
  getV6BgPixels,
  cellIndexToV6Prefix,
  mouseToBlockV6,
  hexToRGB,
  type V6BlockConfig,
} from './hilbert'
import { ZoomModalV6 } from './IXPHilbertZoom'

export type V6LayerKey = 'rir_br' | 'global_br' | 'global_all' | 'ixp_all' | 'rir_br_visible'

export const V6_LAYER_META: Record<V6LayerKey, { label: string; color: string; description: string; legend: string }> = {
  rir_br: {
    label: 'Alocado Registro.br',
    color: '#3b82f6',
    description: 'Espaço IPv6 alocado ao Brasil pelo Registro.br/RIR',
    legend: 'Prefixos IPv6 atribuídos a entidades brasileiras pelo Registro.br. Representam o espaço de endereçamento formalmente alocado ao Brasil, esteja ou não anunciado na Internet.',
  },
  global_br: {
    label: 'ASNs BR na tabela global',
    color: '#10b981',
    description: 'Prefixos de ASNs brasileiros visíveis na tabela global',
    legend: 'Prefixos IPv6 anunciados por ASNs brasileiros e observados na tabela de roteamento global. Mostra o espaço que as organizações brasileiras anunciam ao mundo.',
  },
  global_all: {
    label: 'Tabela global, todos',
    color: '#f59e0b',
    description: 'Todos os prefixos IPv6 na tabela de roteamento global',
    legend: 'Todos os prefixos IPv6 presentes na tabela de roteamento global. Representam o conjunto dos prefixos IPv6 visíveis globalmente.',
  },
  ixp_all: {
    label: 'IXPs do IX.br',
    color: '#8b5cf6',
    description: 'Prefixos IPv6 observados em qualquer IXP do IX.br',
    legend: 'Prefixos IPv6 observados em qualquer ponto de troca de tráfego (IXP) do IX.br. Representam o espaço de endereçamento que aparece anunciado nas interligações do IX.br.',
  },
  rir_br_visible: {
    label: 'Alocado BR + visível',
    color: '#ef4444',
    description: 'Espaço IPv6 alocado ao Brasil e presente na tabela de roteamento global',
    legend: 'Interseção entre o espaço IPv6 alocado ao Brasil (Registro.br) e a tabela de roteamento global. Mostra o espaço em uso: alocado ao Brasil e anunciado na Internet.',
  },
}

export interface V6BlockData {
  rir_br: number[]
  global_br: number[]
  global_all: number[]
  ixp_all: number[]
  rir_br_visible: number[]
}

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

interface HilbertMapV6BlockProps {
  config: V6BlockConfig
  data: V6BlockData | null
  activeLayer: V6LayerKey
  cssWidth: number
  /** Cor para o zoom modal (usa a cor da camada ativa). */
  layerColor?: string
}

interface ZoomedSquare { gx: number; gy: number }

const V6_BR_RED: [number, number, number] = [0xef, 0x44, 0x44]
const V6_DUAL_COLOR_LAYERS: V6LayerKey[] = ['global_br', 'global_all', 'ixp_all']

export function renderV6Block(
  ctx: CanvasRenderingContext2D,
  config: V6BlockConfig,
  activeCells: number[] | null,
  overlayColor: string,
  /** Se fornecido, células com índice no set são pintadas em vermelho (#ef4444). */
  brSet: Set<number> | null,
) {
  const { canvasPx, gridSize } = config

  // Fundo slate-200 cacheado (evita loop de fill por render)
  const pixels = new Uint8ClampedArray(getV6BgPixels(canvasPx))

  if (activeCells?.length) {
    const [r, g, b] = hexToRGB(overlayColor)
    const [rr, rg, rb] = V6_BR_RED

    if (gridSize === 256) {
      // Legado: 2 px/célula
      for (const d of activeCells) {
        const isBR = brSet?.has(d) ?? false
        const [cr, cg, cb] = isBR ? [rr, rg, rb] : [r, g, b]
        const ox = GRID16[d].x * 2
        const oy = GRID16[d].y * 2
        for (let cy = 0; cy < 2; cy++) {
          const row = (oy + cy) * canvasPx
          for (let cx = 0; cx < 2; cx++) {
            const i = (row + ox + cx) * 4
            pixels[i] = cr; pixels[i + 1] = cg; pixels[i + 2] = cb; pixels[i + 3] = 255
          }
        }
      }
    } else {
      // /12: 1 px/célula
      const grid = getGrid1024()
      for (const d of activeCells) {
        const isBR = brSet?.has(d) ?? false
        const [cr, cg, cb] = isBR ? [rr, rg, rb] : [r, g, b]
        const i = (grid.y[d] * canvasPx + grid.x[d]) * 4
        pixels[i] = cr; pixels[i + 1] = cg; pixels[i + 2] = cb; pixels[i + 3] = 255
      }
    }
  }

  ctx.putImageData(new ImageData(pixels, canvasPx, canvasPx), 0, 0)
}

export function HilbertMapV6Block({ config, data, activeLayer, cssWidth, layerColor }: HilbertMapV6BlockProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [tooltip, setTooltip] = useState<{ d: number; cssX: number; cssY: number } | null>(null)
  const [zoomedSquare, setZoomedSquare] = useState<ZoomedSquare | null>(null)
  const [isHoveredClickable, setIsHoveredClickable] = useState(false)

  // Sets para lookup O(1) no tooltip (evita includes() O(n))
  const rir_brSet      = useMemo(() => new Set(data?.rir_br         ?? []), [data?.rir_br])
  const globalBrSet    = useMemo(() => new Set(data?.global_br      ?? []), [data?.global_br])
  const globalSet      = useMemo(() => new Set(data?.global_all     ?? []), [data?.global_all])
  const ixpSet         = useMemo(() => new Set(data?.ixp_all        ?? []), [data?.ixp_all])
  const rir_visibleSet = useMemo(() => new Set(data?.rir_br_visible ?? []), [data?.rir_br_visible])

  const activeCells = useMemo(
    () => data ? (data[activeLayer] ?? []) : [],
    [data, activeLayer],
  )

  const activeSquares = useMemo(
    () => computeActiveV6Squares(activeCells.length ? activeCells : null, config),
    [activeCells, config],
  )

  const gridScale = config.gridSize / config.canvasPx
  const numCols = config.gridSize / V6_STEP

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const brSet = V6_DUAL_COLOR_LAYERS.includes(activeLayer) ? rir_brSet : null
    renderV6Block(ctx, config, data ? data[activeLayer] : null, V6_LAYER_META[activeLayer].color, brSet)
  }, [data, activeLayer, config, rir_brSet])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const cssX = e.clientX - rect.left
    const cssY = e.clientY - rect.top
    const scale = config.canvasPx / rect.width
    const canvasX = cssX * scale
    const canvasY = cssY * scale
    setTooltip({ d: mouseToBlockV6(canvasX, canvasY, config.canvasPx, config), cssX, cssY })
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

  const hd = tooltip?.d ?? -1
  const activePresent   = hd >= 0 && (
    activeLayer === 'rir_br'         ? rir_brSet.has(hd)
    : activeLayer === 'global_br'    ? globalBrSet.has(hd)
    : activeLayer === 'global_all'   ? globalSet.has(hd)
    : activeLayer === 'ixp_all'      ? ixpSet.has(hd)
    : rir_visibleSet.has(hd)
  )
  const isBRinDual = V6_DUAL_COLOR_LAYERS.includes(activeLayer) && rir_brSet.has(hd)
  const activeDotColor = isBRinDual ? '#ef4444' : V6_LAYER_META[activeLayer].color

  // Outras camadas presentes além da ativa
  const otherLayers: V6LayerKey[] = (['rir_br', 'global_br', 'global_all', 'ixp_all', 'rir_br_visible'] as V6LayerKey[])
    .filter(k => k !== activeLayer && (
      k === 'rir_br'         ? rir_brSet.has(hd)
      : k === 'global_br'    ? globalBrSet.has(hd)
      : k === 'global_all'   ? globalSet.has(hd)
      : k === 'ixp_all'      ? ixpSet.has(hd)
      : rir_visibleSet.has(hd)
    ))

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
            cursor: isHoveredClickable ? 'pointer' : 'default',
          }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          onClick={handleClick}
        />
        {/* Grade /20 com bordas vermelhas em quadrados com dados */}
        {(() => {
          const gs = config.gridSize
          const isLegacy = gs === 256
          return (
            <svg
              viewBox={`0 0 ${gs} ${gs}`}
              style={{
                position: 'absolute', top: 0, left: 0,
                width: cssWidth, height: cssWidth,
                pointerEvents: 'none', overflow: 'hidden', borderRadius: 2,
              }}
            >
              {Array.from({ length: numCols * numCols }, (_, idx) => {
                const gx = idx % numCols
                const gy = Math.floor(idx / numCols)
                const hasData = activeSquares.has(idx)
                return (
                  <g key={idx}>
                    <rect x={gx * V6_STEP} y={gy * V6_STEP} width={V6_STEP} height={V6_STEP}
                      fill="none" stroke="#334155"
                      strokeWidth={isLegacy ? 0.6 : 2.5} strokeOpacity={0.40} />
                    {hasData && <rect x={gx * V6_STEP} y={gy * V6_STEP} width={V6_STEP} height={V6_STEP}
                      fill="none" stroke="#ef4444"
                      strokeWidth={isLegacy ? 2 : 8} strokeOpacity={0.30} />}
                  </g>
                )
              })}
            </svg>
          )
        })()}
        {tooltip !== null && (
          <div
            className="absolute z-10 bg-white border border-gray-200 rounded shadow-md px-2 py-1.5 pointer-events-none"
            style={{
              left: tooltip.cssX + 8,
              top: Math.max(0, tooltip.cssY - 28),
              maxWidth: 210,
              transform: tooltip.cssX > cssWidth * 0.6 ? 'translateX(-110%)' : undefined,
            }}
          >
            {/* Linha 1: prefixo */}
            <div className="font-mono font-semibold text-gray-900 text-xs whitespace-nowrap">
              {cellIndexToV6Prefix(tooltip.d, config)}
            </div>
            {/* Linha 2: bloco/RIR */}
            <div className="text-gray-500 text-xs">{config.rir} · {config.label}</div>
            {/* Linha 3: camada ativa */}
            {activePresent ? (
              <div className="mt-0.5 space-y-0.5">
                <div style={{ color: activeDotColor }} className="text-xs">
                  {V6_LAYER_META[activeLayer].label}
                  {isBRinDual && <span className="ml-1 text-xs">· alocado BR</span>}
                </div>
                {otherLayers.map(k => (
                  <div key={k} className="text-xs flex items-center gap-1" style={{ color: V6_LAYER_META[k].color }}>
                    <span>●</span><span>{V6_LAYER_META[k].label}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-0.5 space-y-0.5">
                <div className="text-gray-300 text-xs">sem dados nesta camada</div>
                {otherLayers.map(k => (
                  <div key={k} className="text-xs flex items-center gap-1" style={{ color: V6_LAYER_META[k].color }}>
                    <span>●</span><span>{V6_LAYER_META[k].label}</span>
                  </div>
                ))}
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
          allCells={activeCells}
          ownCells={null}
          thirdCells={null}
          isPeerMode={false}
          color={layerColor ?? V6_LAYER_META[activeLayer].color}
          onClose={() => setZoomedSquare(null)}
        />
      )}
    </div>
  )
}
