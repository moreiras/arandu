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
import { circuloGeoJSON, type ConjuntoRaio } from './raio'
import { html } from '../../lib/html'

const BR_STATES_URL = '/br-states.geojson'
const COR = { central: '#dc2626', agregado: MAP_COLORS.v4Strong, fora: '#cbd5e1' }

/**
 * Mapa do município com raio: o central em vermelho, os agregados em azul, os que estão no raio mas passaram do teto em cinza, e os
 * círculos do raio pedido (tracejado) e do efetivo. Pontos nos centróides, como nos outros mapas por município; sem WebGL a página segue sem o mapa.
 */
export function MapaRaio({ conjunto, centroides, nomes, altura = 320 }: { conjunto: ConjuntoRaio; centroides: Record<string, LonLat>; nomes: Record<string, string>; altura?: number }) {
  const el = useRef<HTMLDivElement>(null)
  const mapa = useRef<maplibregl.Map | null>(null)
  const dados = useRef({ conjunto, centroides, nomes })
  dados.current = { conjunto, centroides, nomes }

  const desenhar = () => {
    const m = mapa.current
    if (!m) return
    const { conjunto: c, centroides: cs, nomes: ns } = dados.current
    const origem = cs[c.central]
    if (!origem) return
    const ponto = (ibge: string, papel: keyof typeof COR, km: number): GeoJSON.Feature<GeoJSON.Point> | null => {
      const p = cs[ibge]
      return p ? { type: 'Feature', geometry: { type: 'Point', coordinates: p }, properties: { ibge, papel, km: Math.round(km), nome: ns[ibge] ?? '' } } : null
    }
    const feats = [
      ...c.foraDoLimite.map((v) => ponto(v.ibge, 'fora', v.km)),
      ...c.selecionados.map((v) => ponto(v.ibge, v.ibge === c.central ? 'central' : 'agregado', v.km)),
    ].filter((f): f is GeoJSON.Feature<GeoJSON.Point> => !!f)
    ;(m.getSource('pontos') as maplibregl.GeoJSONSource | undefined)?.setData({ type: 'FeatureCollection', features: feats })
    const circulos: GeoJSON.Feature[] = []
    if (c.raioKm > 0) circulos.push({ ...circuloGeoJSON(origem, c.raioKm), properties: { tipo: 'pedido' } })
    if (c.cortado) circulos.push({ ...circuloGeoJSON(origem, c.raioEfetivoKm), properties: { tipo: 'efetivo' } })
    ;(m.getSource('circulos') as maplibregl.GeoJSONSource | undefined)?.setData({ type: 'FeatureCollection', features: circulos })
    const lons = feats.map((f) => f.geometry.coordinates[0]); const lats = feats.map((f) => f.geometry.coordinates[1])
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
        m.addSource('circulos', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
        m.addSource('pontos', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
        m.addLayer({ id: 'circulos-fill', type: 'fill', source: 'circulos', filter: ['==', ['get', 'tipo'], 'efetivo'], paint: { 'fill-color': MAP_COLORS.v4Strong, 'fill-opacity': 0.06 } })
        m.addLayer({ id: 'circulos-pedido', type: 'line', source: 'circulos', filter: ['==', ['get', 'tipo'], 'pedido'], paint: { 'line-color': '#475569', 'line-width': 1.2, 'line-dasharray': [3, 2] } })
        m.addLayer({ id: 'circulos-efetivo', type: 'line', source: 'circulos', filter: ['==', ['get', 'tipo'], 'efetivo'], paint: { 'line-color': MAP_COLORS.v4Strong, 'line-width': 1.6 } })
        m.addLayer({
          id: 'pontos', type: 'circle', source: 'pontos',
          paint: {
            'circle-color': ['match', ['get', 'papel'], 'central', COR.central, 'agregado', COR.agregado, COR.fora],
            'circle-radius': ['match', ['get', 'papel'], 'central', 7, 'agregado', 5, 3.5], 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 0.8, 'circle-opacity': 0.9,
          },
        })
        const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false })
        m.on('mouseenter', 'pontos', (e) => {
          m.getCanvas().style.cursor = 'pointer'
          const f = e.features?.[0]; if (!f) return
          const p = f.properties as Record<string, unknown>
          const quem = p.nome ? String(p.nome) : `IBGE ${p.ibge}`
          const nota = p.papel === 'fora' ? 'fora do limite de municípios: não entra nas somas' : p.papel === 'central' ? 'município central' : `${p.km} km do centro`
          popup.setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number]).setHTML(html`<div style="font:12px system-ui"><strong>${quem}</strong><div style="color:#64748b">${nota}</div></div>`).addTo(m)
        })
        m.on('mouseleave', 'pontos', () => { m.getCanvas().style.cursor = ''; popup.remove() })
        fetch(BR_STATES_URL).then((r) => r.json()).then((states) => {
          if (!mapa.current) return
          mapa.current.addSource('states', { type: 'geojson', data: states })
          mapa.current.addLayer({ id: 'states-line', type: 'line', source: 'states', paint: STATE_OUTLINE_PAINT }, 'circulos-fill')
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
    if (m.isStyleLoaded() && m.getSource('pontos')) desenhar()
  }, [conjunto, centroides, nomes])

  return <div ref={el} data-testid="mapa-raio" className="w-full rounded-lg border border-gray-200 overflow-hidden" style={{ height: altura }} />
}
