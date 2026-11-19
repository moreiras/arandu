/**
 * Bloco visual de 6 mapas de Hilbert IPv6 lado a lado — um por RIR.
 * Compartilha seletor de camada e legenda. Cada sub-mapa é HilbertMapV6Block.
 */
import { useState, useRef, useLayoutEffect } from 'react'
import { V6_BLOCKS } from './hilbert'
import { HilbertMapV6Block, V6_LAYER_META, type V6LayerKey, type V6BlockData } from './HilbertMapV6Block'
import type { HilbertV6Data } from '../../types/api'

interface HilbertMapV6Props {
  data: HilbertV6Data | null
  /** Largura CSS de cada sub-mapa em px (default 160). */
  blockWidth?: number
}

export function HilbertMapV6({ data, blockWidth: blockWidthProp = 160 }: HilbertMapV6Props) {
  const [activeLayer, setActiveLayer] = useState<V6LayerKey>('rir_br')
  const containerRef = useRef<HTMLDivElement>(null)
  const [cols, setCols] = useState(3)
  const [blockWidth, setBlockWidth] = useState(blockWidthProp)

  useLayoutEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver(entries => {
      const w = entries[0].contentRect.width
      const c = w < 500 ? 2 : 3
      setCols(c)
      setBlockWidth(Math.min(Math.floor((w - (c - 1) * 16) / c), blockWidthProp))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [blockWidthProp])

  return (
    <div ref={containerRef}>
      {/* Seletor de camada — mesmo estilo do mapa IPv4 */}
      <div className="flex flex-wrap gap-1.5 mb-2">
        {(Object.keys(V6_LAYER_META) as V6LayerKey[]).map((key) => {
          const meta = V6_LAYER_META[key]
          const active = activeLayer === key
          return (
            <button
              key={key}
              onClick={() => setActiveLayer(key)}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                active
                  ? 'text-white border-transparent'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'
              }`}
              style={active ? { backgroundColor: meta.color, borderColor: meta.color } : undefined}
              title={meta.description}
            >
              {meta.label}
            </button>
          )
        })}
      </div>

      {/* Legenda dinâmica */}
      <p
        className="text-xs text-gray-500 mb-3 leading-relaxed border-l-2 pl-2"
        style={{ borderColor: V6_LAYER_META[activeLayer].color }}
      >
        {V6_LAYER_META[activeLayer].legend}
      </p>

      {/* 6 mapas — 3 colunas no desktop, 2 no mobile */}
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
        {V6_BLOCKS.map((config) => {
          const blockData = data ? (data[config.id as keyof HilbertV6Data] as V6BlockData) : null
          return (
            <HilbertMapV6Block
              key={config.id}
              config={config}
              data={blockData}
              activeLayer={activeLayer}
              cssWidth={blockWidth}
              layerColor={V6_LAYER_META[activeLayer].color}
            />
          )
        })}
      </div>

      <p className="text-xs text-gray-400 mt-1.5">
        Cada célula = bloco /32 IPv6. Legado (2001::/16): grade 256×256.
        Blocos /12: grade 1024×1024 (downscale suave). Passe o mouse para ver o prefixo. Clique em blocos destacados para ampliar.
      </p>
    </div>
  )
}
