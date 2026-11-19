import { useEffect, useRef, useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { fetchASNGeo, fetchIXPs, type ASNGeoFeature } from '../../services/api'
import type { IXPPresence } from '../../types/api'
import {
  MAP_COLORS,
  STATE_OUTLINE_PAINT,
  MAP_DEFAULT_CENTER,
  MAP_DEFAULT_ZOOM,
  bearingInicial, createBaseMapStyle,
  addStandardControls,
} from './mapTheme'
import { html } from '../../lib/html'

// ---------------------------------------------------------------------------
// Cores (tema compartilhado — ver mapTheme.ts)
// ---------------------------------------------------------------------------

const V4_STRONG = MAP_COLORS.v4Strong
const V4_WEAK   = MAP_COLORS.v4Weak
const V6_STRONG = MAP_COLORS.v6Strong
const V6_WEAK   = MAP_COLORS.v6Weak
const PIX_COLOR = MAP_COLORS.pixFill
const PIX_STROKE = MAP_COLORS.pixStroke

// ---------------------------------------------------------------------------
// MapLibre constants
// ---------------------------------------------------------------------------

const BRAZIL_CENTER = MAP_DEFAULT_CENTER
const BRAZIL_ZOOM   = MAP_DEFAULT_ZOOM
const BR_STATES_URL = '/br-states.geojson'

const MAP_STYLE: maplibregl.StyleSpecification = createBaseMapStyle()

const EMPTY_FC: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] }

const prefixRadiusExpr: maplibregl.ExpressionSpecification = [
  'interpolate', ['exponential', 2], ['zoom'],
  2,  ['+', 3,  ['*', 3,  ['log10', ['+', 1, ['get', 'block_count']]]]],
  5,  ['+', 7,  ['*', 6,  ['log10', ['+', 1, ['get', 'block_count']]]]],
  8,  ['+', 13, ['*', 10, ['log10', ['+', 1, ['get', 'block_count']]]]],
  12, ['+', 22, ['*', 16, ['log10', ['+', 1, ['get', 'block_count']]]]],
]

const prefixOpacityExpr: maplibregl.ExpressionSpecification = [
  'interpolate', ['linear'], ['get', 'block_count'],
  1, 0.50, 10, 0.62, 50, 0.72, 200, 0.80, 500, 0.87,
]

const pixRadiusExpr: maplibregl.ExpressionSpecification = [
  'interpolate', ['linear'], ['zoom'], 3, 3, 7, 6, 12, 9,
]

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

interface Props {
  asn: number | string
  date?: string
  ixpPresence?: Record<string, IXPPresence>
}

export function ASNGeoMap({ asn, date, ixpPresence }: Props) {
  // IXPs onde o ASN aparece como originador
  const ixpCodes = useMemo(
    () => Object.keys(ixpPresence ?? {}).filter(
      c => ixpPresence![c].v4?.origin || ixpPresence![c].v6?.origin
    ).sort(),
    [ixpPresence]
  )

  // Nomes dos IXPs a partir do índice (cacheado pelo react-query)
  const { data: ixpList } = useQuery({
    queryKey: ['ixps', date],
    queryFn: () => fetchIXPs(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
    enabled: ixpCodes.length > 0,
  })
  const ixpNames = useMemo(() => {
    const m: Record<string, string> = {}
    for (const e of ixpList?.ixps ?? []) m[e.code] = e.name
    return m
  }, [ixpList])

  // Seleção: 'ft' = full table, qualquer outra string = código de IXP
  const [selected, setSelected] = useState<string>('ft')
  const [afi, setAfi]           = useState<'v4' | 'v6'>('v6')

  // Queries de dados — IXP: sempre ativas (permite trocar v4/v6 sem delay)
  const { data: ftV4,  isLoading: loadFtV4  } = useQuery({
    queryKey: ['asn-geo', asn, 'fulltable_v4', date],
    queryFn:  () => fetchASNGeo(asn, 'fulltable_v4', date),
    enabled: selected === 'ft',
    staleTime: Infinity, gcTime: Infinity, retry: false,
  })
  const { data: ftV6,  isLoading: loadFtV6  } = useQuery({
    queryKey: ['asn-geo', asn, 'fulltable_v6', date],
    queryFn:  () => fetchASNGeo(asn, 'fulltable_v6', date),
    enabled: selected === 'ft',
    staleTime: Infinity, gcTime: Infinity, retry: false,
  })
  const { data: ixpV4, isLoading: loadIxpV4 } = useQuery({
    queryKey: ['asn-geo', asn, 'ixp_v4', date],
    queryFn:  () => fetchASNGeo(asn, 'ixp_v4', date),
    enabled: ixpCodes.length > 0,
    staleTime: Infinity, gcTime: Infinity, retry: false,
  })
  const { data: ixpV6, isLoading: loadIxpV6 } = useQuery({
    queryKey: ['asn-geo', asn, 'ixp_v6', date],
    queryFn:  () => fetchASNGeo(asn, 'ixp_v6', date),
    enabled: ixpCodes.length > 0,
    staleTime: Infinity, gcTime: Infinity, retry: false,
  })

  // Features e PIX ativos conforme seleção
  const activeFeatures = useMemo((): ASNGeoFeature[] => {
    if (selected === 'ft') {
      return ((afi === 'v4' ? ftV4 : ftV6)?.features ?? []) as ASNGeoFeature[]
    }
    const src = (afi === 'v4' ? ixpV4 : ixpV6)?.features ?? []
    return (src as ASNGeoFeature[]).filter(
      f => (f.properties as Record<string, unknown>)?.ixp_code === selected
    )
  }, [selected, afi, ftV4, ftV6, ixpV4, ixpV6])

  const activePix = useMemo((): Array<{ name: string; lat: number; lon: number }> => {
    if (selected === 'ft') return []
    const src = (afi === 'v4' ? ixpV4 : ixpV6)
    return ((src?.ixp_pix ?? []) as Array<{ ixp_code?: string; name: string; lat: number; lon: number }>)
      .filter(p => p.ixp_code === selected)
  }, [selected, afi, ixpV4, ixpV6])

  const isLoading = selected === 'ft'
    ? (afi === 'v4' ? loadFtV4 : loadFtV6)
    : (afi === 'v4' ? loadIxpV4 : loadIxpV6)

  // ---------------------------------------------------------------------------
  // MapLibre
  // ---------------------------------------------------------------------------

  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef       = useRef<maplibregl.Map | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const el = containerRef.current
    if (!el || mapRef.current) return

    const map = new maplibregl.Map({
      container: el, style: MAP_STYLE,
      center: BRAZIL_CENTER, zoom: BRAZIL_ZOOM, bearing: bearingInicial(),
      attributionControl: false,
    })
    addStandardControls(map, { dbip: true })

    map.on('load', () => {
      map.addSource('states', { type: 'geojson', data: EMPTY_FC })
      map.addLayer({ id: 'states-outline', type: 'line', source: 'states',
        paint: STATE_OUTLINE_PAINT })
      fetch(BR_STATES_URL).then(r => r.json())
        .then(g => (map.getSource('states') as maplibregl.GeoJSONSource).setData(g))
        .catch(() => {})

      map.addSource('pix', { type: 'geojson', data: EMPTY_FC })
      map.addLayer({ id: 'layer-pix', type: 'circle', source: 'pix',
        paint: {
          'circle-radius': pixRadiusExpr,
          'circle-color': PIX_COLOR, 'circle-opacity': 0.9,
          'circle-stroke-width': 1.5, 'circle-stroke-color': PIX_STROKE,
        },
      })

      map.addSource('data', { type: 'geojson', data: EMPTY_FC })
      map.addLayer({ id: 'layer-downstream', type: 'circle', source: 'data',
        filter: ['==', ['get', 'role'], 'downstream'],
        paint: {
          'circle-radius': prefixRadiusExpr,
          'circle-color': V4_WEAK,
          'circle-opacity': prefixOpacityExpr,
          'circle-stroke-width': 0,
        },
      })
      map.addLayer({ id: 'layer-own', type: 'circle', source: 'data',
        filter: ['==', ['get', 'role'], 'own'],
        paint: {
          'circle-radius': prefixRadiusExpr,
          'circle-color': V4_STRONG,
          'circle-opacity': prefixOpacityExpr,
          'circle-stroke-width': 0,
        },
      })

      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, maxWidth: '240px' })

      const showPrefixPopup = (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
        const f = e.features?.[0]; if (!f) return
        map.getCanvas().style.cursor = 'pointer'
        const p = f.properties as Record<string, unknown>
        const city = p.city ? `${p.uf ?? ''}/${p.city}` : (p.country as string ?? '?')
        const cnt  = (p.block_count as number ?? 0).toLocaleString('pt-BR')
        const unit = p.block_unit as string ?? 'blocos'
        const role = p.role === 'own' ? 'Próprio' : 'Cliente'
        const ind  = p.direct === false ? ' (indireto)' : ''
        popup.setLngLat(e.lngLat)
          .setHTML(html`<strong>${city}</strong><br/>${cnt} ${unit} · ${role}${ind}`)
          .addTo(map)
      }
      const hidePrefixPopup = () => { map.getCanvas().style.cursor = ''; popup.remove() }
      map.on('mouseenter', 'layer-downstream', showPrefixPopup)
      map.on('mouseleave', 'layer-downstream', hidePrefixPopup)
      map.on('mouseenter', 'layer-own', showPrefixPopup)
      map.on('mouseleave', 'layer-own', hidePrefixPopup)
      map.on('mouseenter', 'layer-pix', (e) => {
        const f = e.features?.[0]; if (!f) return
        map.getCanvas().style.cursor = 'crosshair'
        const p = f.properties as Record<string, unknown>
        popup.setLngLat(e.lngLat).setHTML(html`<strong>${p.name ?? ''}</strong>`).addTo(map)
      })
      map.on('mouseleave', 'layer-pix', () => { map.getCanvas().style.cursor = ''; popup.remove() })

      setReady(true)
    })

    mapRef.current = map
    return () => { map.remove(); mapRef.current = null }
  }, [])

  // Atualiza dados no mapa quando a seleção ou os dados mudam
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return

    ;(map.getSource('data') as maplibregl.GeoJSONSource)?.setData({
      type: 'FeatureCollection', features: activeFeatures,
    })
    ;(map.getSource('pix') as maplibregl.GeoJSONSource)?.setData(
      activePix.length
        ? { type: 'FeatureCollection', features: activePix.map(p => ({
            type: 'Feature' as const,
            geometry: { type: 'Point' as const, coordinates: [p.lon, p.lat] },
            properties: { name: p.name },
          }))}
        : EMPTY_FC
    )
    const strong = afi === 'v4' ? V4_STRONG : V6_STRONG
    const weak   = afi === 'v4' ? V4_WEAK   : V6_WEAK
    map.setPaintProperty('layer-own', 'circle-color', strong)
    map.setPaintProperty('layer-downstream', 'circle-color', weak)
  }, [activeFeatures, activePix, afi, ready])

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const ownCount = activeFeatures.filter(f => f.properties?.role === 'own').length
  const dsCount  = activeFeatures.length - ownCount
  const strong   = afi === 'v4' ? V4_STRONG : V6_STRONG
  const weak     = afi === 'v4' ? V4_WEAK   : V6_WEAK

  const isDirect = selected !== 'ft' && (ixpPresence?.[selected]?.[afi]?.direct ?? false)

  return (
    <div className="space-y-2">
      {/* Seletor de camada (FT + PTTs) */}
      <div className="flex flex-wrap gap-1">
        <button
          onClick={() => setSelected('ft')}
          className={`text-xs px-2 py-1 rounded border transition-colors ${
            selected === 'ft'
              ? 'bg-gray-700 text-white border-gray-700'
              : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
          }`}
        >
          Full table
        </button>

        {ixpCodes.map(code => {
          const name    = ixpNames[code] ?? code.toUpperCase()
          const isDir   = ixpPresence?.[code]?.[afi]?.direct ?? false
          const isActive = selected === code
          return (
            <button
              key={code}
              onClick={() => setSelected(code)}
              title={`${name} — ${isDir ? 'direto' : 'indireto'}`}
              className={`text-xs px-2 py-1 rounded border transition-colors ${
                isActive
                  ? 'bg-gray-700 text-white border-gray-700'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
              }`}
            >
              {name}
              <span className={`ml-1 ${isActive ? 'text-gray-300' : isDir ? 'text-ok-500' : 'text-gray-300'}`}>
                {isDir ? '●' : '○'}
              </span>
            </button>
          )
        })}

        {/* Separador + toggle v4/v6 */}
        {(ixpCodes.length > 0 || true) && (
          <span className="mx-1 text-gray-300 self-center select-none">|</span>
        )}
        {(['v6', 'v4'] as const).map(a => (
          <button
            key={a}
            onClick={() => setAfi(a)}
            className={`text-xs px-2 py-1 rounded border transition-colors ${
              afi === a
                ? 'bg-gray-700 text-white border-gray-700'
                : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
            }`}
          >
            {a === 'v4' ? 'IPv4' : 'IPv6'}
          </button>
        ))}

        {/* Contagem e status */}
        {!isLoading && activeFeatures.length > 0 && (
          <span className="text-xs text-gray-400 self-center ml-1">
            · {activeFeatures.length.toLocaleString('pt-BR')} cidades
          </span>
        )}
        {isLoading && (
          <span className="text-xs text-gray-400 animate-pulse self-center ml-1">carregando…</span>
        )}
      </div>

      {/* Mapa */}
      <div className="relative rounded-lg border border-gray-200 overflow-hidden" style={{ height: 437 }}>
        {!isLoading && activeFeatures.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10 text-sm text-gray-400">
            {selected === 'ft'
              ? 'Nenhum prefixo geolocalizável'
              : `Nenhum prefixo geolocalizável para ${ixpNames[selected] ?? selected.toUpperCase()}`}
          </div>
        )}
        <div ref={containerRef} className="w-full h-full" />
      </div>

      {/* Legenda */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-500">
        {ownCount > 0 && (
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full opacity-80" style={{ background: strong }} />
            {selected === 'ft'
              ? 'Próprios'
              : isDirect ? 'Próprios (direto)' : 'Próprios (indireto)'}
            {' '}({ownCount.toLocaleString('pt-BR')} cidades)
          </span>
        )}
        {dsCount > 0 && (
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full opacity-80" style={{ background: weak }} />
            Clientes
          </span>
        )}
        {activePix.length > 0 && (
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full opacity-50" style={{ background: PIX_COLOR }} />
            PTT (localização física)
          </span>
        )}
        <span className="text-gray-400">· {afi === 'v4' ? '● direto · ○ indireto' : '● direto · ○ indireto'} · Tamanho ∝ log(blocos)</span>
      </div>
    </div>
  )
}
