/**
 * Bloco visual de 6 mapas de Hilbert IPv6 lado a lado — um por RIR.
 * Compartilha seletor de camada e legenda. Cada sub-mapa é HilbertMapV6Block.
 */
import { useState, useRef, useLayoutEffect } from 'react'
import { V6_BLOCKS, type V6BlockConfig } from './hilbert'
import { HilbertMapV6Block, V6_LAYER_META, V6_DUAL_COLOR_LAYERS, type V6LayerKey, type V6LayerMeta, type V6BlockData } from './HilbertMapV6Block'
import type { HilbertV6Data } from '../../types/api'
import { corLegivel } from '../../lib/contraste'

interface HilbertMapV6Props {
  data: HilbertV6Data | Record<string, Record<string, number[]>> | null
  /** Largura CSS de cada sub-mapa em px (default 160). */
  blockWidth?: number
  /** Definição das camadas (padrão: as nacionais, `V6_LAYER_META`); a ordem das chaves é a dos botões. */
  layerMeta?: Record<string, V6LayerMeta>
  /** Camada inicial (padrão: `rir_br`). */
  camadaInicial?: string
  /** Avisa a troca de camada, para quem mostra algo que depende dela. */
  onCamada?: (camada: string) => void
  /** Camadas pintadas em ciano (alocado e visível) onde `baseLayer` também tem a célula (padrão: as nacionais). */
  dualLayers?: readonly string[]
  baseLayer?: string
  /** Nome acessível do canvas de cada bloco; sem ele os canvas ficam como sempre foram. */
  rotuloBloco?: (config: V6BlockConfig) => string
  /** Texto abaixo dos mapas (padrão: o do panorama). */
  rodape?: string
}

const RODAPE_PADRAO = 'Cada célula = bloco /32 IPv6. Legado (2001::/16): grade 256×256. Blocos /12: grade 1024×1024 (downscale suave). Passe o mouse para ver o prefixo. Clique em blocos destacados para ampliar.'

export function HilbertMapV6({ data, blockWidth: blockWidthProp = 160, layerMeta = V6_LAYER_META, camadaInicial = 'rir_br', onCamada, dualLayers = V6_DUAL_COLOR_LAYERS, baseLayer = 'rir_br', rotuloBloco, rodape = RODAPE_PADRAO }: HilbertMapV6Props) {
  const [activeLayer, setActiveLayerEstado] = useState<V6LayerKey | string>(camadaInicial)
  const setActiveLayer = (k: string) => { setActiveLayerEstado(k); onCamada?.(k) }
  const dadosPorBloco = data as Record<string, Record<string, number[]> | undefined> | null
  const blocos = V6_BLOCKS
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
        {Object.keys(layerMeta).map((key) => {
          const meta = layerMeta[key]
          const active = activeLayer === key
          return (
            <button
              key={key}
              type="button"
              aria-pressed={active}
              onClick={() => setActiveLayer(key)}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                active
                  ? 'text-white border-transparent'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'
              }`}
              style={active ? { backgroundColor: corLegivel(meta.color), borderColor: corLegivel(meta.color) } : undefined}
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
        style={{ borderColor: layerMeta[activeLayer].color }}
      >
        {layerMeta[activeLayer].legend}
      </p>

      {/* 6 mapas — 3 colunas no desktop, 2 no mobile */}
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
        {blocos.map((config) => {
          const blockData = dadosPorBloco ? (dadosPorBloco[config.id] as V6BlockData | undefined) ?? null : null
          return (
            <HilbertMapV6Block
              key={config.id}
              config={config}
              data={blockData}
              activeLayer={activeLayer}
              cssWidth={blockWidth}
              layerColor={layerMeta[activeLayer].color}
              layerMeta={layerMeta}
              dualLayers={dualLayers}
              baseLayer={baseLayer}
              rotuloCanvas={rotuloBloco?.(config)}
            />
          )
        })}
      </div>

      <p className="text-xs text-gray-400 mt-1.5">{rodape}</p>
    </div>
  )
}
