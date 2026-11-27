/**
 * Mapa de Hilbert IPv4 específico para a página de IXP.
 * Suporta modo "total" (todos os prefixos do IXP) e modo "peer"
 * (prefixos próprios em azul, terceiros em laranja).
 */
import { useRef, useEffect, useState, useCallback, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchIXPHilbert } from '../../services/api'
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
} from './hilbert'
import { ZoomModalV4 } from './IXPHilbertZoom'
import { QuadrantesTeclado } from './QuadrantesTeclado'
import { nomeAmpliar, prefixoQuadranteV4 } from './quadrantes'

const CANVAS_PX = 512
const CELL = CANVAS_PX / 256

const COLOR_ALL = '#6366f1'   // indigo — total IXP
const COLOR_OWN = '#3b82f6'   // blue — prefixos próprios
const COLOR_THIRD = '#f97316' // orange — prefixos de terceiros


function renderSingle(
  ctx: CanvasRenderingContext2D,
  density: number[],
  color: string,
) {
  const [or, og, ob] = hexToRGB(color)
  const pixels = new Uint8ClampedArray(getIanaPixels512())
  for (let d = 0; d < 65536; d++) {
    const count = density[d]
    if (!count) continue
    const opacity = opacidadeDensidade(count)
    const { x, y } = GRID16[d]
    for (let cy = 0; cy < CELL; cy++) {
      for (let cx = 0; cx < CELL; cx++) {
        const idx = ((y * CELL + cy) * CANVAS_PX + (x * CELL + cx)) * 4
        pixels[idx]     = Math.round(pixels[idx]     * (1 - opacity) + or * opacity)
        pixels[idx + 1] = Math.round(pixels[idx + 1] * (1 - opacity) + og * opacity)
        pixels[idx + 2] = Math.round(pixels[idx + 2] * (1 - opacity) + ob * opacity)
      }
    }
  }
  ctx.putImageData(new ImageData(pixels, CANVAS_PX, CANVAS_PX), 0, 0)
}

function renderDual(
  ctx: CanvasRenderingContext2D,
  own: number[],
  third: number[],
) {
  const [or, og, ob] = hexToRGB(COLOR_OWN)
  const [tr, tg, tb] = hexToRGB(COLOR_THIRD)
  const pixels = new Uint8ClampedArray(getIanaPixels512())

  for (let d = 0; d < 65536; d++) {
    const ownCount = own[d] ?? 0
    const thirdCount = third[d] ?? 0
    const total = ownCount + thirdCount
    if (!total) continue

    const opacity = opacidadeDensidade(total)
    // Blend: blue × own_pct + orange × third_pct
    const ownPct = ownCount / total
    const thirdPct = 1 - ownPct
    const cr = Math.round(or * ownPct + tr * thirdPct)
    const cg = Math.round(og * ownPct + tg * thirdPct)
    const cb = Math.round(ob * ownPct + tb * thirdPct)

    const { x, y } = GRID16[d]
    for (let cy = 0; cy < CELL; cy++) {
      for (let cx = 0; cx < CELL; cx++) {
        const idx = ((y * CELL + cy) * CANVAS_PX + (x * CELL + cx)) * 4
        pixels[idx]     = Math.round(pixels[idx]     * (1 - opacity) + cr * opacity)
        pixels[idx + 1] = Math.round(pixels[idx + 1] * (1 - opacity) + cg * opacity)
        pixels[idx + 2] = Math.round(pixels[idx + 2] * (1 - opacity) + cb * opacity)
      }
    }
  }
  ctx.putImageData(new ImageData(pixels, CANVAS_PX, CANVAS_PX), 0, 0)
}

interface TooltipState { blockIdx: number; cssX: number; cssY: number }
interface ZoomedBlock  { sx: number; sy: number; slashEight: number }

interface IXPHilbert16Props {
  code: string
  date?: string
  /** Lista de ASNs com sessão no route server para o dropdown */
  peerList: number[]
  /** Peer selecionado externamente (sincroniza com a tabela) */
  selectedPeer: number | null
  onSelectPeer: (asn: number | null) => void
  width?: number
}

export function IXPHilbert16({
  code,
  date,
  peerList,
  selectedPeer,
  onSelectPeer,
  width = 440,
}: IXPHilbert16Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [tooltip, setTooltip] = useState<TooltipState | null>(null)
  const [zoomedBlock, setZoomedBlock] = useState<ZoomedBlock | null>(null)
  const [isHoveredClickable, setIsHoveredClickable] = useState(false)

  // Hilbert total (sem peer)
  const { data: totalData, isLoading: loadingTotal } = useQuery({
    queryKey: ['ixp-hilbert', code, date],
    queryFn: () => fetchIXPHilbert(code, undefined, date),
    staleTime: Infinity, gcTime: Infinity,
  })

  // Hilbert por peer (só quando selecionado)
  const { data: peerData, isLoading: loadingPeer } = useQuery({
    queryKey: ['ixp-hilbert-peer', code, selectedPeer, date],
    queryFn: () => fetchIXPHilbert(code, selectedPeer!, date),
    enabled: selectedPeer !== null,
    staleTime: Infinity, gcTime: Infinity,
  })

  const isLoading = loadingTotal || (selectedPeer !== null && loadingPeer)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    if (selectedPeer !== null && peerData?.own && peerData?.third) {
      renderDual(ctx, peerData.own, peerData.third)
    } else if (totalData?.all) {
      renderSingle(ctx, totalData.all, COLOR_ALL)
    }
  }, [totalData, peerData, selectedPeer])

  const activeDensity =
    selectedPeer !== null && peerData?.own
      ? peerData.own.map((v, i) => v + (peerData.third?.[i] ?? 0))
      : totalData?.all ?? null

  // Pré-computa quais quadrados /8 têm pelo menos um /16 com dados
  const slash8WithData = useMemo(() => {
    if (!activeDensity) return new Set<number>()
    const active = new Set<number>()
    SLASH8_GRID.forEach(({ sx, sy }, idx) => {
      if (slash8HasData(sx, sy, activeDensity)) active.add(idx)
    })
    return active
  }, [activeDensity])

  const quadrantes = useMemo(() => [...slash8WithData].map((idx) => {
    const { sx, sy, block } = SLASH8_GRID[idx]
    return { col: sx, lin: sy, nome: nomeAmpliar(prefixoQuadranteV4(block)), aoAbrir: () => setZoomedBlock({ sx, sy, slashEight: block }) }
  }), [slash8WithData])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const scaleX = CANVAS_PX / rect.width
    const scaleY = CANVAS_PX / rect.height
    const canvasX = (e.clientX - rect.left) * scaleX
    const canvasY = (e.clientY - rect.top) * scaleY
    const blockIdx = mouseToBlock16(canvasX, canvasY, CANVAS_PX)
    setTooltip({ blockIdx, cssX: e.clientX - rect.left, cssY: e.clientY - rect.top })
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
            <option key={asn} value={asn}>
              AS{asn}
            </option>
          ))}
        </select>
        {isLoading && (
          <span className="text-xs text-gray-400 animate-pulse">Carregando…</span>
        )}
      </div>

      {/* Legenda */}
      {selectedPeer !== null ? (
        <div className="flex gap-4 text-xs text-gray-600">
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm" style={{ background: COLOR_OWN }} />
            Prefixos próprios (AS{selectedPeer} é originador)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm" style={{ background: COLOR_THIRD }} />
            Prefixos de terceiros (repassados pelo AS{selectedPeer})
          </span>
          <span className="text-gray-400 italic">
            · mix de cores = blocos com ambos
          </span>
        </div>
      ) : (
        <p className="text-xs text-gray-500">
          <span className="inline-block w-3 h-3 rounded-sm align-middle mr-1" style={{ background: COLOR_ALL }} />
          Prefixos IPv4 anunciados neste IXP. A intensidade cresce com o número de /24 no bloco /16; todo bloco com dado aparece, mesmo com um só /24.
        </p>
      )}

      {/* Canvas */}
      {/* Mapa de largura fixa em px: no celular rola dentro do próprio contêiner, não a página. */}
      <div className="max-w-full overflow-x-auto">
        <div className="relative select-none" style={{ width, height: width }}>
          {!totalData && loadingTotal ? (
            <div className="absolute inset-0 bg-gray-100 rounded-lg animate-pulse" />
          ) : (
            <>
              <canvas
                ref={canvasRef}
                width={CANVAS_PX}
                height={CANVAS_PX}
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

              {/* Grade /8 — borda mais forte se há dados no bloco */}
              <svg
                viewBox="0 0 256 256"
                style={{
                  position: 'absolute', top: 0, left: 0,
                  width, height: width,
                  pointerEvents: 'none',
                  overflow: 'hidden',
                  borderRadius: 4,
                }}
              >
                {SLASH8_GRID.map(({ block, sx, sy }, idx) => {
                  const hasData = slash8WithData.has(idx)
                  return (
                    <g key={block}>
                      {/* grid base */}
                      <rect x={sx * 16} y={sy * 16} width={16} height={16}
                        fill="none" stroke="#334155" strokeWidth={0.35} strokeOpacity={0.40} />
                      {/* destaque vermelho sobreposto */}
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

              <QuadrantesTeclado lado={16} quadrantes={quadrantes} rotulo="Quadrantes do mapa IPv4, use as setas" />

              {/* Tooltip */}
              {tooltip !== null && (() => {
                const { blockIdx, cssX, cssY } = tooltip
                const prefix = block16ToPrefix(blockIdx)
                const slash8 = block16ToSlash8(blockIdx)
                const ownVal = peerData?.own?.[blockIdx] ?? 0
                const thirdVal = peerData?.third?.[blockIdx] ?? 0
                const allVal = activeDensity?.[blockIdx] ?? 0
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
                    <div className="font-semibold text-gray-900">{prefix}</div>
                    <div className="text-gray-500 text-xs">{ianaCategory(slash8)}</div>
                    {selectedPeer !== null ? (
                      <div className="mt-0.5 space-y-0.5">
                        {ownVal > 0 && (
                          <div style={{ color: COLOR_OWN }}>
                            {ownVal} /24{ownVal !== 1 ? 's' : ''} próprios
                          </div>
                        )}
                        {thirdVal > 0 && (
                          <div style={{ color: COLOR_THIRD }}>
                            {thirdVal} /24{thirdVal !== 1 ? 's' : ''} de terceiros
                          </div>
                        )}
                        {!ownVal && !thirdVal && (
                          <div className="text-gray-300">sem dados neste peer</div>
                        )}
                      </div>
                    ) : allVal > 0 ? (
                      <div className="mt-0.5" style={{ color: COLOR_ALL }}>
                        {allVal} /24{allVal !== 1 ? 's' : ''}
                      </div>
                    ) : (
                      <div className="text-gray-300 mt-0.5">sem dados</div>
                    )}
                  </div>
                )
              })()}
            </>
          )}
        </div>
      </div>

      <p className="text-xs text-gray-400">
        Cada célula = bloco /16. Clique em um bloco /8 destacado, ou use Tab e Enter, para ampliar. Use o dropdown ou a tabela para selecionar um peer.
      </p>

      {zoomedBlock && (
        <ZoomModalV4
          sx={zoomedBlock.sx}
          sy={zoomedBlock.sy}
          slashEight={zoomedBlock.slashEight}
          code={code}
          date={date}
          selectedPeer={selectedPeer}
          densityAll={totalData?.all ?? null}
          densityOwn={peerData?.own ?? null}
          densityThird={peerData?.third ?? null}
          isPeerMode={selectedPeer !== null}
          onClose={() => setZoomedBlock(null)}
        />
      )}
    </div>
  )
}
