// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { MAP_COLORS, STATE_OUTLINE_PAINT, MAP_DEFAULT_CENTER, MAP_DEFAULT_ZOOM, bearingInicial, createBaseMapStyle, addStandardControls } from '../../components/maps/mapTheme'
import type { LonLat } from '../../lib/geo'
import { circuloGeoJSON, filtroPorIbge, filtrosDoConjunto, type ConjuntoRaio } from './raio'
import { URL_MALHA } from '../../components/maps/Coropletico'
import { html } from '../../lib/html'

const BR_STATES_URL = '/br-states.geojson'
/** Um só tom (o azul do mapa) para os municípios somados; o central se destaca pelo contorno escuro e pelo preenchimento mais firme; os cortados só têm o contorno, em cinza. */
const COR = { somados: MAP_COLORS.v4Strong, centralContorno: '#0f172a', fora: '#94a3b8' }

/**
 * Mapa do município com raio: os contornos dos municípios somados sobre a malha do IBGE (PMTiles, filtrada pelos códigos IBGE), com o central destacado, os que estão
 * no raio mas passaram do teto só em contorno cinza, e os círculos do raio pedido (tracejado) e do efetivo. Ao mudar o raio só os filtros e os círculos são atualizados:
 * o mapa não é recriado. Sem WebGL a página segue sem o mapa (a lista dos municípios fica ao lado).
 */
export function MapaRaio({ conjunto, centroides, nomes, altura = 320 }: { conjunto: ConjuntoRaio; centroides: Record<string, LonLat>; nomes: Record<string, string>; altura?: number }) {
  const el = useRef<HTMLDivElement>(null)
  const mapa = useRef<maplibregl.Map | null>(null)
  const dados = useRef({ conjunto, centroides, nomes })
  dados.current = { conjunto, centroides, nomes }

  const desenhar = () => {
    const m = mapa.current
    if (!m) return
    const { conjunto: c, centroides: cs } = dados.current
    const origem = cs[c.central]
    if (!origem) return
    const f = filtrosDoConjunto(c)
    m.setFilter('mun-somados-fill', f.somados)
    m.setFilter('mun-somados-linha', f.somados)
    m.setFilter('mun-central-fill', f.central)
    m.setFilter('mun-central-linha', f.central)
    m.setFilter('mun-fora-linha', f.fora)
    const circulos: GeoJSON.Feature[] = []
    if (c.raioKm > 0) circulos.push({ ...circuloGeoJSON(origem, c.raioKm), properties: { tipo: 'pedido' } })
    if (c.cortado) circulos.push({ ...circuloGeoJSON(origem, c.raioEfetivoKm), properties: { tipo: 'efetivo' } })
    ;(m.getSource('circulos') as maplibregl.GeoJSONSource | undefined)?.setData({ type: 'FeatureCollection', features: circulos })
    const pontos = [...c.foraDoLimite, ...c.selecionados].map((v) => cs[v.ibge]).filter((p): p is LonLat => !!p)
    const lons = pontos.map((p) => p[0]); const lats = pontos.map((p) => p[1])
    if (c.raioKm > 0 && lons.length > 1) m.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: 40, maxZoom: 9, duration: 0 })
    else m.jumpTo({ center: origem, zoom: 8 })
  }

  useEffect(() => {
    if (!el.current || mapa.current) return
    let ro: ResizeObserver | null = null
    try {
      const m = new maplibregl.Map({ container: el.current, style: createBaseMapStyle(), center: MAP_DEFAULT_CENTER, zoom: MAP_DEFAULT_ZOOM, bearing: bearingInicial(), attributionControl: false })
      mapa.current = m
      addStandardControls(m)
      ro = new ResizeObserver(() => m.resize())
      ro.observe(el.current)
      m.on('load', () => {
        const base = new URL(URL_MALHA, window.location.origin).href
        m.addSource('malha', { type: 'vector', url: `pmtiles://${base}`, attribution: 'Fonte: IBGE' })
        m.addSource('circulos', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
        const vazio = filtroPorIbge([])
        m.addLayer({ id: 'mun-somados-fill', type: 'fill', source: 'malha', 'source-layer': 'municipios', filter: vazio, paint: { 'fill-color': COR.somados, 'fill-opacity': 0.14 } })
        m.addLayer({ id: 'mun-central-fill', type: 'fill', source: 'malha', 'source-layer': 'municipios', filter: vazio, paint: { 'fill-color': COR.somados, 'fill-opacity': 0.35 } })
        m.addLayer({ id: 'mun-fora-linha', type: 'line', source: 'malha', 'source-layer': 'municipios', filter: vazio, paint: { 'line-color': COR.fora, 'line-width': 0.8, 'line-dasharray': [2, 2] } })
        m.addLayer({ id: 'mun-somados-linha', type: 'line', source: 'malha', 'source-layer': 'municipios', filter: vazio, paint: { 'line-color': COR.somados, 'line-width': 0.9, 'line-opacity': 0.9 } })
        m.addLayer({ id: 'mun-central-linha', type: 'line', source: 'malha', 'source-layer': 'municipios', filter: vazio, paint: { 'line-color': COR.centralContorno, 'line-width': 2.2 } })
        m.addLayer({ id: 'circulos-pedido', type: 'line', source: 'circulos', filter: ['==', ['get', 'tipo'], 'pedido'], paint: { 'line-color': '#475569', 'line-width': 1.2, 'line-dasharray': [3, 2] } })
        m.addLayer({ id: 'circulos-efetivo', type: 'line', source: 'circulos', filter: ['==', ['get', 'tipo'], 'efetivo'], paint: { 'line-color': MAP_COLORS.v4Strong, 'line-width': 1.6 } })
        // O popup é DOM puro (sem estado do React): o hover não re-renderiza nada.
        const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false })
        const sobre = (e: maplibregl.MapLayerMouseEvent) => {
          const p = e.features?.[0]?.properties as Record<string, unknown> | undefined; if (!p) return
          m.getCanvas().style.cursor = 'pointer'
          const { conjunto: c, nomes: ns } = dados.current
          const ibge = String(p.ibge)
          const quem = ns[ibge] ?? (p.nome ? `${p.nome} ${p.uf ?? ''}`.trim() : `IBGE ${ibge}`)
          const km = c.selecionados.find((v) => v.ibge === ibge)?.km
          const nota = ibge === c.central ? 'município central' : km != null ? `${Math.round(km)} km do centro` : ''
          popup.setLngLat(e.lngLat).setHTML(html`<div style="font:12px system-ui"><strong>${quem}</strong><div style="color:#64748b">${nota}</div></div>`).addTo(m)
        }
        const saiu = () => { m.getCanvas().style.cursor = ''; popup.remove() }
        for (const id of ['mun-somados-fill', 'mun-central-fill']) { m.on('mousemove', id, sobre); m.on('mouseleave', id, saiu) }
        fetch(BR_STATES_URL).then((r) => r.json()).then((states) => {
          if (!mapa.current) return
          mapa.current.addSource('states', { type: 'geojson', data: states })
          mapa.current.addLayer({ id: 'states-line', type: 'line', source: 'states', paint: STATE_OUTLINE_PAINT }, 'circulos-pedido')
        }).catch(() => { /* contorno é decoração */ })
        desenhar()
      })
    } catch {
      mapa.current = null // sem WebGL: a página segue sem o mapa
    }
    return () => { ro?.disconnect(); mapa.current?.remove(); mapa.current = null }
  }, [])

  useEffect(() => {
    const m = mapa.current
    if (!m) return
    if (m.getLayer('mun-somados-fill')) desenhar()
  }, [conjunto, centroides, nomes])

  return <div ref={el} data-testid="mapa-raio" role="img" aria-label={`Mapa com o contorno de ${conjunto.selecionados.length} ${conjunto.selecionados.length === 1 ? 'município' : 'municípios'}; a lista deles está logo abaixo`} className="w-full rounded-lg border border-gray-200 overflow-hidden" style={{ height: altura }} />
}
