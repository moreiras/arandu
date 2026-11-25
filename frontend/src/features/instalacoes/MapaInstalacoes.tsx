// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useMemo, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { STATE_OUTLINE_PAINT, MAP_DEFAULT_CENTER, MAP_DEFAULT_ZOOM, bearingInicial, createBaseMapStyle, addStandardControls, MARKER_OPACITY } from '../../components/maps/mapTheme'
import type { FacilityResumo } from '../../types/api'
import { escapar, localDe, n } from './comum'

const BR_STATES_URL = '/br-states.geojson'
const EMPTY_FC: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] }
const FONTE = 'instalacoes'
const CAMADA = 'instalacoes-point'
const CAMADA_GRUPO = 'instalacoes-grupo'
const CAMADA_GRUPO_N = 'instalacoes-grupo-n'
// área do círculo proporcional ao número de redes (raio ∝ raiz), com piso para a instalação sem redes.
// (o `zoom` só pode estar no nível de cima da expressão: as saídas da interpolação é que dependem do dado)
const RAIZ_REDES: maplibregl.ExpressionSpecification = ['sqrt', ['max', 0, ['coalesce', ['get', 'redes'], 0]]]
const RAIO_REDES: maplibregl.ExpressionSpecification = ['interpolate', ['linear'], ['zoom'], 3, ['+', 3, ['*', 0.6, RAIZ_REDES]], 12, ['+', 6, ['*', 1.2, RAIZ_REDES]]]
const RAIO_GRUPO: maplibregl.ExpressionSpecification = ['+', 8, ['*', 0.9, ['sqrt', ['max', 0, ['get', 'redes_soma']]]]]
const COR = { recente: '#15803d', parado: '#d97706', antigo: '#6b7280', semData: '#94a3b8' }

/** Um ponto por instalação com coordenada; a cor é o indicador de cadastro (inferido pelas datas), não o estado da instalação. */
export function paraGeoJson(itens: FacilityResumo[]): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: itens.filter((f) => f.lat != null && f.lon != null).map((f) => ({
      type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [f.lon as number, f.lat as number] },
      properties: { id: f.id, nome: f.nome ?? '', org: f.org_nome ?? '', local: localDe(f), redes: f.n_redes ?? f.redes_declaradas ?? null, classe: f.cadastro?.classe ?? 'sem' },
    })),
  }
}

function popupHtml(p: Record<string, unknown>): string {
  return `<div class="text-xs leading-relaxed">
    <div class="font-semibold text-sm mb-1"><a href="/instalacao/${escapar(p.id)}" class="hover:underline">${escapar(p.nome)}</a></div>
    ${p.org ? `<div class="text-gray-500">${escapar(p.org)}</div>` : ''}
    <div>${escapar(p.local)}</div>
    ${p.redes != null ? `<div>${escapar(n(Number(p.redes)))} redes cadastradas</div>` : ''}
  </div>`
}

/** Mapa de datacenters e pontos de interconexão do PeeringDB. Sem estado de hover no React: o cursor é CSS do canvas. */
export function MapaInstalacoes({ itens, altura = 380 }: { itens: FacilityResumo[]; altura?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const mapa = useRef<maplibregl.Map | null>(null)
  const geo = useMemo(() => paraGeoJson(itens), [itens])
  const geoRef = useRef(geo)
  geoRef.current = geo

  useEffect(() => {
    if (!ref.current || mapa.current) return
    const map = new maplibregl.Map({ container: ref.current, style: createBaseMapStyle(), center: MAP_DEFAULT_CENTER, zoom: MAP_DEFAULT_ZOOM, bearing: bearingInicial(), attributionControl: false })
    mapa.current = map
    addStandardControls(map)
    const observer = new ResizeObserver(() => map.resize())
    observer.observe(ref.current)
    const montar = () => {
      map.addSource('states', { type: 'geojson', data: EMPTY_FC })
      map.addLayer({ id: 'states-outline', type: 'line', source: 'states', paint: STATE_OUTLINE_PAINT })
      fetch(BR_STATES_URL).then((r) => r.json()).then((g) => (map.getSource('states') as maplibregl.GeoJSONSource).setData(g)).catch(() => {})
      // Instalações próximas viram um círculo só no zoom afastado (soma das redes); ao aproximar, cada uma aparece com raio pelo número de redes.
      map.addSource(FONTE, { type: 'geojson', data: geoRef.current, cluster: true, clusterRadius: 28, clusterMaxZoom: 9,
        clusterProperties: { redes_soma: ['+', ['coalesce', ['get', 'redes'], 0]] } })
      map.addLayer({
        id: CAMADA_GRUPO, type: 'circle', source: FONTE, filter: ['has', 'point_count'],
        paint: { 'circle-color': '#0369a1', 'circle-opacity': 0.55, 'circle-radius': RAIO_GRUPO, 'circle-stroke-width': 1, 'circle-stroke-color': '#0c4a6e' },
      })
      map.addLayer({
        id: CAMADA_GRUPO_N, type: 'symbol', source: FONTE, filter: ['has', 'point_count'],
        layout: { 'text-field': ['to-string', ['get', 'point_count']], 'text-size': 11, 'text-font': ['Noto Sans Regular'], 'text-allow-overlap': true },
        paint: { 'text-color': '#ffffff' },
      })
      map.addLayer({
        id: CAMADA, type: 'circle', source: FONTE, filter: ['!', ['has', 'point_count']],
        paint: {
          'circle-color': ['match', ['get', 'classe'], 'recente', COR.recente, 'parado', COR.parado, 'antigo', COR.antigo, COR.semData],
          'circle-radius': RAIO_REDES, 'circle-stroke-width': 0.5, 'circle-stroke-color': '#ffffff', 'circle-opacity': MARKER_OPACITY,
        },
      })
      map.on('click', CAMADA_GRUPO, (e) => {
        const f = e.features?.[0]
        if (!f) return
        const src = map.getSource(FONTE) as maplibregl.GeoJSONSource
        src.getClusterExpansionZoom(f.properties?.cluster_id as number).then((z) => map.easeTo({ center: (f.geometry as GeoJSON.Point).coordinates as [number, number], zoom: z })).catch(() => {})
      })
      map.on('mouseenter', CAMADA_GRUPO, () => { map.getCanvas().style.cursor = 'pointer' })
      map.on('mouseleave', CAMADA_GRUPO, () => { map.getCanvas().style.cursor = '' })
      map.on('click', CAMADA, (e) => {
        const f = e.features?.[0]
        if (f) new maplibregl.Popup({ closeButton: false, maxWidth: '260px' }).setLngLat(e.lngLat).setHTML(popupHtml(f.properties as Record<string, unknown>)).addTo(map)
      })
      map.on('mouseenter', CAMADA, () => { map.getCanvas().style.cursor = 'pointer' })
      map.on('mouseleave', CAMADA, () => { map.getCanvas().style.cursor = '' })
    }
    if (map.isStyleLoaded()) montar()
    else map.once('load', montar)
    return () => { observer.disconnect(); map.remove(); mapa.current = null }
  }, [])

  useEffect(() => {
    const src = mapa.current?.getSource(FONTE) as maplibregl.GeoJSONSource | undefined
    if (src) src.setData(geo)
  }, [geo])

  return (
    <div className="relative rounded-lg border border-gray-200 overflow-hidden" style={{ height: altura }} data-testid="mapa-instalacoes">
      <div ref={ref} className="w-full h-full" />
      <div className="absolute bottom-8 right-3 flex flex-wrap gap-2 text-xs bg-white/90 backdrop-blur px-3 py-2 rounded shadow-sm border border-gray-200">
        {([['recente', 'atividade em até 12 meses'], ['parado', 'sem atividade há 1 a 3 anos'], ['antigo', 'sem atividade há mais de 3 anos']] as const).map(([k, r]) => (
          <span key={k} className="flex items-center gap-1"><span className="w-3 h-3 rounded-full inline-block" style={{ background: COR[k] }} /> {r}</span>
        ))}
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full inline-block bg-tecnico-700/60" /> várias instalações (número no círculo)</span>
        <span className="text-gray-600">tamanho = redes cadastradas</span>
      </div>
    </div>
  )
}
