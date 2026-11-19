import { html } from '../../lib/html'
import { useEffect, useMemo, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { GrupoPrefixoGeoFeature } from '../../services/api'
import {
  MAP_COLORS,
  STATE_OUTLINE_PAINT,
  MAP_DEFAULT_CENTER,
  MAP_DEFAULT_ZOOM,
  bearingInicial, createBaseMapStyle,
  addStandardControls,
} from '../maps/mapTheme'

const BR_STATES_URL = '/br-states.geojson'
const EMPTY_FC: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] }

const radiusExpr: maplibregl.ExpressionSpecification = [
  'interpolate', ['exponential', 2], ['zoom'],
  2, ['+', 3, ['*', 3, ['log10', ['+', 1, ['get', 'block_count']]]]],
  5, ['+', 6, ['*', 5, ['log10', ['+', 1, ['get', 'block_count']]]]],
  8, ['+', 10, ['*', 8, ['log10', ['+', 1, ['get', 'block_count']]]]],
  12, ['+', 16, ['*', 12, ['log10', ['+', 1, ['get', 'block_count']]]]],
]

/**
 * Fallback de mapa para grupos sem acessos declarados ao SICI: bolhas dos
 * blocos IPv4 (azul) e IPv6 (laranja) geolocalizados dos ASNs do grupo —
 * mesma fonte/paleta do mapa de um AS individual (ASNGeoMap), mas agregado
 * entre todos os ASNs das empresas do grupo.
 */
export function GrupoPrefixosGeoMap({
  features,
  height = 380,
}: {
  features: GrupoPrefixoGeoFeature[]
  height?: number
}) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const [ready, setReady] = useState(false)

  const fc = useMemo<GeoJSON.FeatureCollection>(
    () => ({ type: 'FeatureCollection', features: features as unknown as GeoJSON.Feature[] }),
    [features],
  )

  useEffect(() => {
    if (!container.current || map.current) return
    map.current = new maplibregl.Map({
      container: container.current,
      style: createBaseMapStyle(),
      center: MAP_DEFAULT_CENTER,
      zoom: MAP_DEFAULT_ZOOM,
      bearing: bearingInicial(),
      attributionControl: false,
    })
    addStandardControls(map.current, { dbip: true })

    const ro = new ResizeObserver(() => map.current?.resize())
    ro.observe(container.current)

    map.current.on('load', () => {
      const m = map.current
      if (!m) return
      m.addSource('prefixos', { type: 'geojson', data: EMPTY_FC })
      m.addLayer({
        id: 'prefixos-circles', type: 'circle', source: 'prefixos',
        paint: {
          'circle-color': ['match', ['get', 'afi'], 'v6', MAP_COLORS.v6Strong, MAP_COLORS.v4Strong],
          'circle-opacity': 0.65,
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 0.8,
          'circle-radius': radiusExpr,
        },
      })

      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false })
      m.on('mouseenter', 'prefixos-circles', e => {
        m.getCanvas().style.cursor = 'pointer'
        const f = e.features?.[0]
        if (!f) return
        const p = f.properties as Record<string, unknown>
        popup.setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number])
          .setHTML(
            html`<div style="font:12px system-ui;line-height:1.45">
               <div style="font-weight:600">${p.city ?? ''} <span style="color:#94a3b8">${p.uf ?? ''}</span></div>
               <div>IP${p.afi === 'v6' ? 'v6' : 'v4'} · ${Number(p.block_count ?? 0).toLocaleString('pt-BR')} blocos</div>
             </div>`)
          .addTo(m)
      })
      m.on('mouseleave', 'prefixos-circles', () => {
        m.getCanvas().style.cursor = ''
        popup.remove()
      })

      fetch(BR_STATES_URL).then(r => r.json()).then(states => {
        if (!map.current) return
        map.current.addSource('states', { type: 'geojson', data: states })
        map.current.addLayer(
          { id: 'states-line', type: 'line', source: 'states', paint: STATE_OUTLINE_PAINT },
          'prefixos-circles',
        )
      }).catch(() => { /* contorno é decoração */ })

      setReady(true)
    })

    return () => { ro.disconnect(); map.current?.remove(); map.current = null }
  }, [])

  useEffect(() => {
    if (!ready) return
    const src = map.current?.getSource('prefixos') as maplibregl.GeoJSONSource | undefined
    src?.setData(fc)
  }, [fc, ready])

  return (
    <div>
      <div ref={container} style={{ height }} className="w-full rounded-lg overflow-hidden border border-gray-200" />
      <div className="text-xs text-gray-400 mt-1 flex items-center gap-3">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: MAP_COLORS.v4Strong }} /> IPv4
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: MAP_COLORS.v6Strong }} /> IPv6
        </span>
        <span>— sem acessos declarados ao SICI; mostrando blocos IP dos ASNs do grupo</span>
      </div>
    </div>
  )
}
