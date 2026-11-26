// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/**
 * Curva de Hilbert dos prefixos de um AS: um quadro de células (IPv4: /16 numa grade 256×256; IPv6: /32 de um bloco de RIR)
 * com as camadas do AS em cores. Células cobertas por prefixo mais curto são todas pintadas; prefixo mais longo que a célula
 * marca a célula que o contém. Poucas células ganham um marcador maior, para não sumirem num quadro de dezenas de milhares.
 * Hover só muda o `title` do canvas (DOM direto), nunca estado do React; o clique escolhe um quadrante (IPv4: /8; IPv6: /20).
 */
import { useCallback, useEffect, useMemo, useRef } from 'react'
import {
  GRID16, SLASH8_GRID, block16ToPrefix, cellIndexToV6Prefix, getGrid1024, getIanaPixels512, getV6BgPixels,
  hexToRGB, mouseToBlock16, mouseToBlockV6, type V6BlockConfig,
} from './hilbert'
import type { Intervalo } from './prefixosAs'

export interface CamadaCurva { id: string; cor: string; faixas: Intervalo[] }

/** Configuração do quadro IPv4 (/16): a mesma forma de um bloco IPv6 de grade 256. */
export const QUADRO_V4: V6BlockConfig = { id: 'v4', label: '0.0.0.0/0', rir: 'IPv4', baseG1: 0, baseLen: 0, unitLen: 32, order: 8, gridSize: 256, totalCells: 65536, canvasPx: 512 }

/** Lado do quadrante, em células: 16 (um /8 no IPv4) ou 64 (um /20 no IPv6). */
export const ladoQuadrante = (cfg: V6BlockConfig) => (cfg.id === 'v4' ? 16 : 64)
const MAX_MARCADORES = 300

function posicao(cfg: V6BlockConfig, d: number): [number, number] {
  if (cfg.gridSize === 256) return [GRID16[d].x, GRID16[d].y]
  const g = getGrid1024()
  return [g.x[d], g.y[d]]
}

interface Props {
  config: V6BlockConfig
  camadas: CamadaCurva[]
  /** Quadrante escolhido (índice da célula dividido pelo tamanho do quadrante), ou null. */
  selecionado: number | null
  onSelecionar: (quad: number | null) => void
  rotulo: string
  /** Largura máxima em px; o quadro encolhe com o contêiner. */
  larguraMax?: number
}

export function HilbertAs({ config, camadas, selecionado, onSelecionar, rotulo, larguraMax = 360 }: Props) {
  const ref = useRef<HTMLCanvasElement>(null)
  const { canvasPx, gridSize } = config
  const celula = canvasPx / gridSize
  const lado = ladoQuadrante(config)
  const porQuad = lado * lado

  useEffect(() => {
    const ctx = ref.current?.getContext('2d')
    if (!ctx) return
    const px = new Uint8ClampedArray(config.id === 'v4' ? getIanaPixels512() : getV6BgPixels(canvasPx))
    let total = 0
    for (const c of camadas) {
      const [r, g, b] = hexToRGB(c.cor)
      for (const f of c.faixas) {
        for (let d = f.ini; d < f.fim; d++) {
          total++
          const [x, y] = posicao(config, d)
          for (let cy = 0; cy < celula; cy++) {
            for (let cx = 0; cx < celula; cx++) {
              const i = ((y * celula + cy) * canvasPx + x * celula + cx) * 4
              px[i] = r; px[i + 1] = g; px[i + 2] = b; px[i + 3] = 255
            }
          }
        }
      }
    }
    ctx.putImageData(new ImageData(px, canvasPx, canvasPx), 0, 0)
    if (total > MAX_MARCADORES) return
    const m = Math.round(canvasPx / 56)
    ctx.lineWidth = 1
    ctx.strokeStyle = '#ffffff'
    for (const c of camadas) {
      ctx.fillStyle = c.cor
      for (const f of c.faixas) {
        for (let d = f.ini; d < f.fim; d++) {
          const [x, y] = posicao(config, d)
          const cx = x * celula + celula / 2 - m / 2
          const cy = y * celula + celula / 2 - m / 2
          ctx.fillRect(cx, cy, m, m)
          ctx.strokeRect(cx, cy, m, m)
        }
      }
    }
  }, [config, camadas, canvasPx, celula])

  const indiceEm = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    const x = ((e.clientX - r.left) / r.width) * canvasPx
    const y = ((e.clientY - r.top) / r.height) * canvasPx
    return config.id === 'v4' ? mouseToBlock16(x, y, canvasPx) : mouseToBlockV6(x, y, canvasPx, config)
  }, [config, canvasPx])

  // Sem estado do React: o texto do hover vai direto ao atributo `title`.
  const aoMover = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const d = indiceEm(e)
    e.currentTarget.title = config.id === 'v4' ? block16ToPrefix(d) : cellIndexToV6Prefix(d, config)
  }, [config, indiceEm])

  const aoClicar = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const quad = Math.floor(indiceEm(e) / porQuad)
    onSelecionar(quad === selecionado ? null : quad)
  }, [indiceEm, porQuad, onSelecionar, selecionado])

  const grade = useMemo(() => {
    const n = gridSize / lado
    return Array.from({ length: n + 1 }, (_, i) => i * lado)
  }, [gridSize, lado])

  const sel = useMemo(() => {
    if (selecionado == null) return null
    const [x, y] = posicao(config, selecionado * porQuad)
    return { x: Math.floor(x / lado) * lado, y: Math.floor(y / lado) * lado }
  }, [config, selecionado, porQuad, lado])

  return (
    <div className="relative select-none aspect-square" style={{ width: `min(100%, ${larguraMax}px)` }}>
      <canvas
        ref={ref} role="img" aria-label={rotulo} width={canvasPx} height={canvasPx}
        className="absolute inset-0 w-full h-full cursor-pointer rounded border border-gray-200"
        style={{ imageRendering: 'pixelated' }}
        onMouseMove={aoMover} onClick={aoClicar}
      />
      <svg aria-hidden="true" viewBox={`0 0 ${gridSize} ${gridSize}`} className="absolute inset-0 w-full h-full pointer-events-none">
        {grade.map((v) => (
          <g key={v}>
            <line x1={v} x2={v} y1={0} y2={gridSize} stroke="#334155" strokeWidth={gridSize / 700} strokeOpacity={0.35} />
            <line y1={v} y2={v} x1={0} x2={gridSize} stroke="#334155" strokeWidth={gridSize / 700} strokeOpacity={0.35} />
          </g>
        ))}
        {config.id === 'v4' && SLASH8_GRID.map(({ block, sx, sy }) => (
          <text key={block} x={sx * 16 + 8} y={sy * 16 + 8} fontSize="3.2" textAnchor="middle" dominantBaseline="middle" fill="#1e293b" fillOpacity="0.7"
            stroke="white" strokeWidth="0.5" strokeOpacity="0.5" style={{ fontFamily: 'monospace', fontWeight: 700 }}>{block}</text>
        ))}
        {sel && <rect x={sel.x} y={sel.y} width={lado} height={lado} fill="none" stroke="#0f172a" strokeWidth={gridSize / 170} />}
      </svg>
    </div>
  )
}
