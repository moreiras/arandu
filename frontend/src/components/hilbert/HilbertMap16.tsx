/**
 * Mapa de Hilbert a resolução /16 — 256×256 células renderizadas em Canvas.
 * Cada célula representa um bloco /16 colorido pela densidade de /24s presentes.
 */
import { useRef, useEffect, useState, useCallback, useMemo } from 'react'
import {
  GRID16,
  SLASH8_GRID,
  SLASH8_POS_MAP,
  slash8HasData,
  getIanaPixels512,
  ianaCategory,
  block16ToPrefix,
  block16ToSlash8,
  hexToRGB,
  mouseToBlock16,
  opacidadeDensidade,
  COR_ALOCADO_VISIVEL,
} from './hilbert'
import { ZoomModalDashV4 } from './IXPHilbertZoom'
import { QuadrantesTeclado } from './QuadrantesTeclado'
import { nomeAmpliar, prefixoQuadranteV4 } from './quadrantes'
import { corLegivel } from '../../lib/contraste'
import { palavra } from '../../lib/sintese'

export type LayerKey = 'rir_br' | 'global_br' | 'global_all' | 'ixp_all' | 'rir_br_visible'

export interface HilbertLayerData {
  rir_br: number[]
  global_br: number[]
  global_all: number[]
  ixp_all: number[]
  rir_br_visible: number[]
}

/** Rótulo, cor e textos de uma camada do mapa. */
export interface LayerMeta { label: string; color: string; description: string; legend: string }

export const LAYER_META: Record<LayerKey, LayerMeta> = {
  rir_br: {
    label: 'Alocado Registro.br',
    color: '#3b82f6',
    description: 'Espaço IPv4 alocado ao Brasil pelo Registro.br/LACNIC',
    legend: 'Prefixos IPv4 atribuídos a entidades brasileiras pelo Registro.br. Representam o espaço de endereçamento formalmente alocado ao Brasil, esteja ou não anunciado na Internet. A intensidade cresce com o número de blocos /24 alocados no /16, e todo /16 com dado aparece, mesmo com um só /24.',
  },
  global_br: {
    label: 'ASNs BR na tabela global',
    color: '#10b981',
    description: 'Prefixos de ASNs brasileiros visíveis na tabela global',
    legend: 'Prefixos anunciados por ASNs brasileiros e observados na tabela de roteamento global. Mostra o espaço que as organizações brasileiras anunciam ao mundo, seja ele alocado ao Brasil ou não.',
  },
  global_all: {
    label: 'Tabela global, todos',
    color: '#f59e0b',
    description: 'Todos os prefixos na tabela de roteamento global',
    legend: 'Todos os prefixos IPv4 presentes na tabela de roteamento global, coletados de vários peers em diferentes regiões. Representam o conjunto dos prefixos IPv4 visíveis globalmente nesses peers.',
  },
  ixp_all: {
    label: 'IXPs do IX.br',
    color: '#8b5cf6',
    description: 'Prefixos observados em qualquer IXP do IX.br',
    legend: 'Prefixos observados em qualquer ponto de troca de tráfego (IXP) do IX.br, isto é, o espaço de endereçamento que aparece anunciado nas interligações do IX.br.',
  },
  rir_br_visible: {
    label: 'Alocado BR + visível',
    color: COR_ALOCADO_VISIVEL,
    description: 'Espaço alocado ao Brasil que está presente na tabela de roteamento global',
    legend: 'Interseção entre o espaço alocado ao Brasil (Registro.br) e a tabela de roteamento global, calculada com precisão de bloco /24. Mostra o espaço em uso: alocado ao Brasil e anunciado na Internet.',
  },
}

const CANVAS_PX = 512  // CSS pixels (canvas interno 2× para retina)
const CELL = CANVAS_PX / 256  // 2px per cell
/** Onde a camada ativa também é espaço alocado ao Brasil: o ciano de "alocado e visível". */
const BR_RED: [number, number, number] = hexToRGB(COR_ALOCADO_VISIVEL)
const DUAL_COLOR_LAYERS: readonly string[] = ['global_br', 'global_all', 'ixp_all']

interface TooltipState {
  blockIdx: number
  cssX: number
  cssY: number
}

interface HilbertMap16Props {
  /** Densidade (/24s por /16) de cada camada; as chaves são as de `layerMeta`. */
  data: HilbertLayerData | Record<string, number[]> | null
  activeLayer: LayerKey | string
  width?: number
  date?: string
  /** Definição das camadas (padrão: as nacionais, `LAYER_META`). */
  layerMeta?: Record<string, LayerMeta>
  /** Camadas pintadas em ciano (alocado e visível) onde a camada `baseLayer` também tem dado (padrão: as nacionais). */
  dualLayers?: readonly string[]
  baseLayer?: string
  /** Sem o detalhe /24 do zoom (que vem da API nacional): o /8 ampliado mostra só a densidade por /16. */
  semDetalhe?: boolean
  /** Nome acessível do canvas; sem ele o canvas fica como sempre foi. */
  rotuloCanvas?: string
}

interface ZoomedBlock { sx: number; sy: number; slashEight: number }

function renderCanvas(
  ctx: CanvasRenderingContext2D,
  canvasPx: number,
  density: number[] | null,
  overlayColor: string,
  /** Se fornecido, blocos com rir_br > 0 são pintados no ciano de "alocado e visível". */
  brDensity: number[] | null,
) {
  const cell = canvasPx / 256
  const pixels = new Uint8ClampedArray(getIanaPixels512())  // copy IANA base

  if (density) {
    const [or, og, ob] = hexToRGB(overlayColor)
    for (let d = 0; d < 65536; d++) {
      const count = density[d]
      if (!count) continue
      const opacity = opacidadeDensidade(count)
      const isBR = brDensity ? brDensity[d] > 0 : false
      const [cr, cg, cb] = isBR ? BR_RED : [or, og, ob]
      const { x, y } = GRID16[d]
      for (let cy = 0; cy < cell; cy++) {
        for (let cx = 0; cx < cell; cx++) {
          const idx = ((y * cell + cy) * canvasPx + (x * cell + cx)) * 4
          pixels[idx]     = Math.round(pixels[idx]     * (1 - opacity) + cr * opacity)
          pixels[idx + 1] = Math.round(pixels[idx + 1] * (1 - opacity) + cg * opacity)
          pixels[idx + 2] = Math.round(pixels[idx + 2] * (1 - opacity) + cb * opacity)
        }
      }
    }
  }

  const imgData = new ImageData(pixels, canvasPx, canvasPx)
  ctx.putImageData(imgData, 0, 0)
}

export function HilbertMap16({ data: dataProp, activeLayer, width = CANVAS_PX, date, layerMeta = LAYER_META, dualLayers = DUAL_COLOR_LAYERS, baseLayer = 'rir_br', semDetalhe = false, rotuloCanvas }: HilbertMap16Props) {
  const data = dataProp as Record<string, number[]> | null
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [tooltip, setTooltip] = useState<TooltipState | null>(null)
  const [zoomedBlock, setZoomedBlock] = useState<ZoomedBlock | null>(null)
  const [isHoveredClickable, setIsHoveredClickable] = useState(false)

  const density = data ? data[activeLayer] : null

  const slash8WithData = useMemo(() => {
    if (!density) return new Set<number>()
    const active = new Set<number>()
    SLASH8_GRID.forEach(({ sx, sy }, idx) => {
      if (slash8HasData(sx, sy, density)) active.add(idx)
    })
    return active
  }, [density])

  const quadrantes = useMemo(() => [...slash8WithData].map((idx) => {
    const { sx, sy, block } = SLASH8_GRID[idx]
    return { col: sx, lin: sy, nome: nomeAmpliar(prefixoQuadranteV4(block)), aoAbrir: () => setZoomedBlock({ sx, sy, slashEight: block }) }
  }), [slash8WithData])

  // Render whenever data or layer changes
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const color = layerMeta[activeLayer].color
    const brDensity = data && dualLayers.includes(activeLayer) ? data[baseLayer] ?? null : null
    renderCanvas(ctx, CANVAS_PX, density, color, brDensity)
  }, [data, activeLayer, density, layerMeta, dualLayers, baseLayer])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const cssX = e.clientX - rect.left
    const cssY = e.clientY - rect.top
    const scaleX = CANVAS_PX / rect.width
    const scaleY = CANVAS_PX / rect.height
    const canvasX = cssX * scaleX
    const canvasY = cssY * scaleY
    const blockIdx = mouseToBlock16(canvasX, canvasY, CANVAS_PX)
    setTooltip({ blockIdx, cssX, cssY })
    const { x, y } = GRID16[blockIdx]
    const entry = SLASH8_POS_MAP.get(`${Math.floor(x / 16)},${Math.floor(y / 16)}`)
    setIsHoveredClickable(!!entry && slash8WithData.has(entry.idx))
  }, [slash8WithData])

  const handleMouseLeave = useCallback(() => {
    setTooltip(null)
    setIsHoveredClickable(false)
  }, [])

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const scaleX = CANVAS_PX / rect.width
    const scaleY = CANVAS_PX / rect.height
    const canvasX = (e.clientX - rect.left) * scaleX
    const canvasY = (e.clientY - rect.top) * scaleY
    const blockIdx = mouseToBlock16(canvasX, canvasY, CANVAS_PX)
    const { x, y } = GRID16[blockIdx]
    const sx = Math.floor(x / 16)
    const sy = Math.floor(y / 16)
    const entry = SLASH8_POS_MAP.get(`${sx},${sy}`)
    if (entry && slash8WithData.has(entry.idx)) {
      setZoomedBlock({ sx, sy, slashEight: entry.block })
    }
  }, [slash8WithData])

  return (
    <>
    {/* Mapa de largura fixa em px: no celular rola dentro do próprio contêiner, não a página. */}
    <div className="max-w-full overflow-x-auto">
      <div className="relative select-none" style={{ width, height: width }}>
        <canvas
          ref={canvasRef}
          width={CANVAS_PX}
          height={CANVAS_PX}
          {...(rotuloCanvas ? { role: 'img', 'aria-label': rotuloCanvas } : {})}
          style={{
            width,
            height: width,
            display: 'block',
            border: '1px solid #e2e8f0',
            borderRadius: 4,
            imageRendering: 'pixelated',
            cursor: isHoveredClickable ? 'pointer' : 'default',
          }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          onClick={handleClick}
        />

        {/* Overlay /8: grade 16×16 + bordas vermelhas + labels */}
        <svg
          viewBox="0 0 256 256"
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width,
            height: width,
            pointerEvents: 'none',
            overflow: 'hidden',
            borderRadius: 4,
          }}
        >
          {SLASH8_GRID.map(({ block, sx, sy }, idx) => {
            const hasData = slash8WithData.has(idx)
            return (
              <g key={block}>
                <rect x={sx * 16} y={sy * 16} width={16} height={16}
                  fill="none" stroke="#334155" strokeWidth={0.35} strokeOpacity={0.40} />
                {hasData && <rect x={sx * 16} y={sy * 16} width={16} height={16}
                  fill="none" stroke="#1e293b" strokeWidth={1.2} strokeOpacity={0.55} />}
                <text
                  x={sx * 16 + 8}
                  y={sy * 16 + 8}
                  fontSize="3.2"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="#1e293b"
                  fillOpacity="0.70"
                  stroke="white"
                  strokeWidth="0.5"
                  strokeOpacity="0.50"
                  style={{ fontFamily: 'monospace', fontWeight: 700 }}
                >
                  {block}
                </text>
              </g>
            )
          })}
        </svg>

        <QuadrantesTeclado lado={16} quadrantes={quadrantes} />

        {tooltip !== null && (() => {
          const { blockIdx, cssX, cssY } = tooltip
          const count = density?.[blockIdx] ?? 0
          const slash8 = block16ToSlash8(blockIdx)
          const isBR = dualLayers.includes(activeLayer) && (data?.[baseLayer]?.[blockIdx] ?? 0) > 0
          const dotColor = corLegivel(isBR ? COR_ALOCADO_VISIVEL : layerMeta[activeLayer].color)
          return (
            <div
              className="absolute z-10 bg-white border border-gray-200 rounded shadow-md px-2 py-1.5 text-xs pointer-events-none"
              style={{
                left: cssX + 10,
                top: cssY - 8,
                maxWidth: 240,
                transform: cssX > width * 0.65 ? 'translateX(-110%)' : undefined,
              }}
            >
              <div className="font-semibold text-gray-900">{block16ToPrefix(blockIdx)}</div>
              <div className="text-gray-500 text-xs">{ianaCategory(slash8)}</div>
              {count > 0 ? (
                <div className="mt-0.5 space-y-0.5">
                  <div style={{ color: dotColor }}>
                    {count} {palavra(count, 'bloco', 'blocos')} /24: {layerMeta[activeLayer].label}
                  </div>
                  {isBR && (
                    <div className="text-xs" style={{ color: corLegivel(COR_ALOCADO_VISIVEL) }}>
                      ● alocado Registro.br
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-gray-300 mt-0.5">sem dados nesta camada</div>
              )}
            </div>
          )
        })()}
      </div>
    </div>

    {zoomedBlock && density && (
      <ZoomModalDashV4
        sx={zoomedBlock.sx}
        sy={zoomedBlock.sy}
        slashEight={zoomedBlock.slashEight}
        activeLayer={activeLayer}
        layerColor={layerMeta[activeLayer].color}
        semDetalhe={semDetalhe}
        density={density}
        date={date}
        onClose={() => setZoomedBlock(null)}
      />
    )}
    </>
  )
}
