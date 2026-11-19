// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { addStandardControls, bearingInicial, MAP_DEFAULT_CENTER } from './mapTheme'
import { COR_SEM_DADO } from './coresCoropletico'

/** Onde está a malha municipal do IBGE em tiles (`scripts/build-malha-municipal.py`); atribuição obrigatória: "Fonte: IBGE". */
export const URL_MALHA = '/malha-municipal.pmtiles'
/** Caixa do Brasil (oeste, sul, leste, norte) para enquadrar o mapa. */
const CAIXA_BRASIL: [[number, number], [number, number]] = [[-74.2, -34.0], [-28.6, 5.4]]

export interface PropsCoropletico {
  /** Expressão de cor do preenchimento (de `expressaoCor` ou `expressaoBivariada`); atualizada sem recriar o mapa. */
  cor: unknown
  /** `municipio` pinta os municípios (com os limites das UFs por cima); `uf` pinta as UFs. */
  nivel?: 'municipio' | 'uf'
  /** Texto de uma feição no tooltip (HTML escapado pelo chamador não é necessário: é inserido como texto). */
  rotulo?: (id: string, nome: string, uf: string) => string
  /** Clique numa feição: código IBGE do município ou sigla da UF. */
  aoClicar?: (id: string, nivel: 'municipio' | 'uf') => void
  altura?: number
  className?: string
  descricao: string
  /** Enquadramento inicial (oeste, sul, leste, norte); sem ele, o país inteiro. Usado nas páginas de UF. */
  caixa?: [[number, number], [number, number]]
}

/**
 * Mapa coroplético sobre a malha municipal em tiles vetoriais (PMTiles lido por `Range`): sem GeoJSON, sem mapa-base, só os limites e a cor por feição.
 * O hover não usa estado do React (tooltip por DOM, regra do projeto). Orientação inicial: a lembrada pelo usuário (padrão sul para cima).
 */
export function Coropletico({ cor, nivel = 'municipio', rotulo, aoClicar, altura = 520, className = '', descricao, caixa }: PropsCoropletico) {
  const ref = useRef<HTMLDivElement>(null)
  const mapa = useRef<maplibregl.Map | null>(null)
  const corRef = useRef(cor)
  const rotuloRef = useRef(rotulo)
  const cliqueRef = useRef(aoClicar)
  corRef.current = cor; rotuloRef.current = rotulo; cliqueRef.current = aoClicar
  const camada = nivel === 'uf' ? 'ufs-fill' : 'mun-fill'

  useEffect(() => {
    const el = ref.current
    if (!el || mapa.current) return
    const base = new URL(URL_MALHA, window.location.origin).href
    const m = new maplibregl.Map({
      container: el, attributionControl: false, center: MAP_DEFAULT_CENTER, zoom: 2.6, bearing: bearingInicial(), maxZoom: 9, dragRotate: true,
      style: {
        version: 8,
        sources: { malha: { type: 'vector', url: `pmtiles://${base}`, attribution: 'Fonte: IBGE' } },
        layers: [
          { id: 'fundo', type: 'background', paint: { 'background-color': '#f8fafc' } },
          { id: 'mun-fill', type: 'fill', source: 'malha', 'source-layer': 'municipios', paint: { 'fill-color': COR_SEM_DADO, 'fill-opacity': nivel === 'municipio' ? 1 : 0 } },
          { id: 'ufs-fill', type: 'fill', source: 'malha', 'source-layer': 'ufs', paint: { 'fill-color': COR_SEM_DADO, 'fill-opacity': nivel === 'uf' ? 1 : 0 } },
          { id: 'mun-linha', type: 'line', source: 'malha', 'source-layer': 'municipios', minzoom: 5, paint: { 'line-color': '#ffffff', 'line-width': 0.4, 'line-opacity': 0.7 } },
          { id: 'ufs-linha', type: 'line', source: 'malha', 'source-layer': 'ufs', paint: { 'line-color': '#475569', 'line-width': ['interpolate', ['linear'], ['zoom'], 3, 0.5, 7, 1.5] } },
        ],
      } as maplibregl.StyleSpecification,
    })
    addStandardControls(m)
    const dica = document.createElement('div')
    dica.className = 'pointer-events-none absolute z-10 hidden rounded bg-gray-900/90 px-2 py-1 text-xs text-white'
    el.appendChild(dica)
    m.on('load', () => {
      m.fitBounds(caixa ?? CAIXA_BRASIL, { padding: 8, duration: 0, bearing: m.getBearing() })      // enquadra o país inteiro na orientação lembrada
      m.setPaintProperty(camada, 'fill-color', corRef.current as never)
    })
    m.on('mousemove', camada, (e) => {
      const f = e.features?.[0]
      if (!f) { dica.style.display = 'none'; return }
      const p = f.properties as Record<string, string>
      const id = nivel === 'uf' ? p.uf : p.ibge
      dica.textContent = rotuloRef.current ? rotuloRef.current(id, p.nome, p.uf) : `${p.nome}${nivel === 'municipio' ? `/${p.uf}` : ''}`
      dica.style.display = 'block'
      dica.style.left = `${e.point.x + 12}px`
      dica.style.top = `${e.point.y + 12}px`
    })
    m.on('mouseleave', camada, () => { dica.style.display = 'none' })
    m.on('click', camada, (e) => {
      const p = e.features?.[0]?.properties as Record<string, string> | undefined
      if (p && cliqueRef.current) cliqueRef.current(nivel === 'uf' ? p.uf : p.ibge, nivel === 'uf' ? 'uf' : 'municipio')
    })
    const ro = new ResizeObserver(() => m.resize())
    ro.observe(el)
    mapa.current = m
    return () => { ro.disconnect(); m.remove(); mapa.current = null }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const m = mapa.current
    if (!m) return
    const aplicar = () => m.setPaintProperty(camada, 'fill-color', cor as never)
    if (m.isStyleLoaded()) aplicar(); else m.once('load', aplicar)
  }, [cor, camada])

  return <div ref={ref} role="group" aria-label={descricao} style={{ height: altura }} className={`relative w-full overflow-hidden rounded-lg border border-gray-200 ${className}`} />
}
