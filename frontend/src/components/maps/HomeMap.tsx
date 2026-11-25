import { escapar } from '../../lib/html'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { fetchHomeMap, fetchASN } from '../../services/api'
import type { ASNDocument, IXPIndexEntry } from '../../types/api'
import {
  MAP_COLORS,
  STATE_OUTLINE_PAINT,
  MAP_DEFAULT_CENTER,
  MAP_DEFAULT_ZOOM,
  bearingInicial, createBaseMapStyle,
  addStandardControls,
  MARKER_RADIUS_EXPR,
  MARKER_OPACITY,
} from './mapTheme'

// ---------------------------------------------------------------------------
// Colors (aliases pro tema compartilhado — ver mapTheme.ts)
// ---------------------------------------------------------------------------

const COLOR_BOTH   = MAP_COLORS.visibilityBoth
const COLOR_V4     = MAP_COLORS.visibilityV4Only
const COLOR_V6     = MAP_COLORS.visibilityV6Only
const COLOR_NONE   = MAP_COLORS.visibilityNone
const COLOR_PIX    = MAP_COLORS.pixFill
const COLOR_PIX_STROKE = MAP_COLORS.pixStroke

// ---------------------------------------------------------------------------
// MapLibre constants
// ---------------------------------------------------------------------------

const BRAZIL_CENTER = MAP_DEFAULT_CENTER
const BRAZIL_ZOOM   = MAP_DEFAULT_ZOOM
const BR_STATES_URL = '/br-states.geojson'
const EMPTY_FC: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] }

const MAP_STYLE: maplibregl.StyleSpecification = createBaseMapStyle()

// Proporção áurea (largura:altura) — mantém o mapa fluido conforme a largura
// do container, em vez de alturas fixas por breakpoint.
const GOLDEN_RATIO = 1.6180339887

const asnRadiusExpr = MARKER_RADIUS_EXPR

const pixRadiusExpr: maplibregl.ExpressionSpecification = [
  'interpolate', ['linear'], ['zoom'], 3, 4, 7, 7, 12, 11,
]

// Layers in draw order (bottom → top): none, v4, v6, both, pix
const ASN_LAYERS: Array<{ id: string; filter: maplibregl.ExpressionSpecification; color: string }> = [
  { id: 'asn-none', filter: ['==', ['get', 'visibility'], 'none'],   color: COLOR_NONE },
  { id: 'asn-v4',   filter: ['==', ['get', 'visibility'], 'v4_only'], color: COLOR_V4   },
  { id: 'asn-v6',   filter: ['==', ['get', 'visibility'], 'v6_only'], color: COLOR_V6   },
  { id: 'asn-both', filter: ['==', ['get', 'visibility'], 'both'],   color: COLOR_BOTH  },
]

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface Props {
  date?: string
  height?: number
  className?: string
  /** Título exibido acima do mapa. */
  title?: string
  /** Índice de IXes (para enriquecer o tooltip dos PIX). */
  ixpIndex?: IXPIndexEntry[]
  /** Total de ASNs BR visíveis na tabela global — denominador das coberturas. */
  brAsnsInFt?: number | null
}

// Cache de docs de AS para o tooltip (lazy fetch no hover, sem rebuscar).
const asnDocCache = new Map<number, Promise<ASNDocument>>()

const fmtBR = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('pt-BR')
const fmtPctBR = (n: number | null | undefined) =>
  n == null ? '—' : `${n.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`

export function HomeMap({ date, height, className, title, ixpIndex, brAsnsInFt }: Props) {
  const navigate = useNavigate()

  // Refs lidos pelos handlers do mapa (registrados uma única vez no load).
  const dateRef = useRef(date)
  const hoveredAsnRef = useRef<number | null>(null)
  const ixpByCodeRef = useRef<Map<string, IXPIndexEntry>>(new Map())
  const brDenomRef = useRef<number | null>(brAsnsInFt ?? null)

  useEffect(() => { dateRef.current = date }, [date])
  useEffect(() => { brDenomRef.current = brAsnsInFt ?? null }, [brAsnsInFt])
  useEffect(() => {
    const m = new Map<string, IXPIndexEntry>()
    for (const e of ixpIndex ?? []) m.set(e.code, e)
    ixpByCodeRef.current = m
  }, [ixpIndex])

  const { data, isLoading } = useQuery({
    queryKey: ['home-map', date],
    queryFn: () => fetchHomeMap(date),
    staleTime: Infinity, gcTime: Infinity,
    retry: false,
  })

  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef       = useRef<maplibregl.Map | null>(null)
  const [ready, setReady] = useState(false)

  // ---------------------------------------------------------------------------
  // Map init
  // ---------------------------------------------------------------------------

  useEffect(() => {
    const el = containerRef.current
    if (!el || mapRef.current) return

    const map = new maplibregl.Map({
      container: el, style: MAP_STYLE,
      center: BRAZIL_CENTER, zoom: BRAZIL_ZOOM, bearing: bearingInicial(),
      attributionControl: false,
    })
    addStandardControls(map)

    // A altura vem de aspect-ratio (proporção áurea sobre a largura fluida do
    // container), não de um valor fixo — sem isto o canvas do MapLibre não
    // percebe as mudanças contínuas de tamanho ao redimensionar a janela.
    const ro = new ResizeObserver(() => map.resize())
    ro.observe(el)

    map.on('load', () => {
      // State borders
      map.addSource('states', { type: 'geojson', data: EMPTY_FC })
      map.addLayer({
        id: 'states-outline', type: 'line', source: 'states',
        paint: STATE_OUTLINE_PAINT,
      })
      fetch(BR_STATES_URL).then(r => r.json())
        .then(g => (map.getSource('states') as maplibregl.GeoJSONSource).setData(g))
        .catch(() => {})

      // PIX source + layer (desenhado primeiro → fica por baixo dos ASes)
      map.addSource('pix', { type: 'geojson', data: EMPTY_FC })
      map.addLayer({
        id: 'pix', type: 'circle', source: 'pix',
        paint: {
          'circle-radius': pixRadiusExpr,
          'circle-color': COLOR_PIX,
          'circle-opacity': 0.9,
          'circle-stroke-width': 1.5,
          'circle-stroke-color': COLOR_PIX_STROKE,
        },
      })

      // ASN source + layers (one per visibility category, bottom to top) — sobre os PIX
      map.addSource('asns', { type: 'geojson', data: EMPTY_FC })
      for (const { id, filter, color } of ASN_LAYERS) {
        map.addLayer({
          id, type: 'circle', source: 'asns', filter,
          paint: {
            'circle-radius': asnRadiusExpr,
            'circle-color': color,
            'circle-opacity': id === 'asn-none' ? 0.45 : MARKER_OPACITY,
            'circle-stroke-width': 0,
          },
        })
      }

      // ---------------------------------------------------------------------------
      // Popup
      // ---------------------------------------------------------------------------

      const popup = new maplibregl.Popup({
        closeButton: false, closeOnClick: false, maxWidth: '260px',
      })

      const allAsnLayerIds = ASN_LAYERS.map(l => l.id)

      const vis: Record<string, string> = {
        both: 'IPv6 + IPv4', v6_only: 'só IPv6', v4_only: 'só IPv4', none: 'não visível na FT',
      }

      // HTML base do AS (mostrado imediatamente, enriquecido após o fetch).
      const asnBaseHtml = (p: Record<string, unknown>) => {
        const loc = p.city ? `${p.city}${p.uf ? '/' + p.uf : ''}` : ''
        const visLabel = vis[p.visibility as string] ?? ''
        return (
          `<strong>AS${escapar(p.asn)}</strong> ${loc ? `· ${escapar(loc)}` : ''}<br/>` +
          `<span style="font-size:0.88em;color:#555">${escapar(p.name ?? '')}</span><br/>` +
          `<span style="font-size:0.82em;color:#777">${escapar(visLabel)}</span>`
        )
      }

      // Linhas extras do AS, vindas do documento completo (lazy).
      const asnExtraHtml = (doc: ASNDocument) => {
        const usersV6 = doc.apnic_v6_pct_as != null ? ` · ${fmtPctBR(doc.apnic_v6_pct_as)} IPv6` : ''
        return (
          `<hr style="border:none;border-top:1px solid #eee;margin:3px 0"/>` +
          `<span style="font-size:0.85em;color:#444">` +
          `👥 ${escapar(fmtBR(doc.apnic_users))} usuários estimados${escapar(usersV6)}<br/>` +
          `🔗 IXPs: ${escapar(fmtBR(doc.ixps_direct?.length))} com sessão no RS · ${escapar(fmtBR(doc.ixps_origin?.length))} originando<br/>` +
          `↕ BGP: ${fmtBR(doc.upstreams?.length)} upstreams · ${fmtBR(doc.downstreams?.length)} downstreams` +
          `</span>`
        )
      }

      const showAsnPopup = (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
        const f = e.features?.[0]; if (!f) return
        map.getCanvas().style.cursor = 'pointer'
        const p = f.properties as Record<string, unknown>
        const asn = Number(p.asn)
        const base = asnBaseHtml(p)
        hoveredAsnRef.current = asn
        popup.setLngLat(e.lngLat)
          .setHTML(base + `<br/><span style="font-size:0.8em;color:#aaa">carregando…</span>`)
          .addTo(map)

        let promise = asnDocCache.get(asn)
        if (!promise) {
          promise = fetchASN(asn, dateRef.current)
          asnDocCache.set(asn, promise)
        }
        promise
          .then((doc) => {
            if (hoveredAsnRef.current !== asn) return // mouse já saiu / outro AS
            popup.setHTML(base + asnExtraHtml(doc))
          })
          .catch(() => {
            asnDocCache.delete(asn)
            if (hoveredAsnRef.current === asn) popup.setHTML(base)
          })
      }

      const hidePopup = () => {
        map.getCanvas().style.cursor = ''
        hoveredAsnRef.current = null
        popup.remove()
      }

      for (const id of allAsnLayerIds) {
        map.on('mouseenter', id, showAsnPopup)
        map.on('mouseleave', id, hidePopup)
        map.on('click', id, (e) => {
          const asn = (e.features?.[0]?.properties as Record<string, unknown>)?.asn
          if (asn != null) navigate(`/asn/${asn}`)
        })
      }

      map.on('mouseenter', 'pix', (e) => {
        const f = e.features?.[0]; if (!f) return
        map.getCanvas().style.cursor = 'pointer'
        const p = f.properties as Record<string, unknown>
        const code = String(p.ixp_code ?? '')
        const entry = ixpByCodeRef.current.get(code)
        const denom = brDenomRef.current
        const cidade = (entry?.name ?? p.ixp_name ?? '') as string
        const uf = entry?.uf ?? ''
        // nomes de PIX já costumam vir com colchetes (ex.: "[PIX RNP]")
        const title = `IX.br ${cidade}${uf ? `, ${uf}` : ''}${p.name ? ` ${p.name}` : ''}`

        let body = ''
        if (entry) {
          const cov = (n?: number) =>
            denom && n != null ? ` <span style="color:#888">(${escapar(fmtPctBR((n / denom) * 100))} dos AS BR)</span>` : ''
          body =
            `<hr style="border:none;border-top:1px solid #eee;margin:3px 0"/>` +
            `<span style="font-size:0.85em;color:#444">` +
            `👥 ${escapar(fmtBR(entry.ixbr_members_count))} participantes<br/>` +
            `🛜 Nos route servers: ${fmtBR(entry.asn_direct_union_count)} ASes` +
            (entry.br_asns_direct_union_count != null
              ? `<br/>&nbsp;&nbsp;↳ ${escapar(fmtBR(entry.br_asns_direct_union_count))} BR${cov(entry.br_asns_direct_union_count)}`
              : '') +
            `<br/>📢 Originando prefixos: ${escapar(fmtBR(entry.br_asns_origin_union_count))} AS BR${cov(entry.br_asns_origin_union_count)}` +
            `</span>`
        }
        popup.setLngLat(e.lngLat)
          .setHTML(`<strong>${escapar(title)}</strong>${body}`)
          .addTo(map)
      })
      map.on('mouseleave', 'pix', hidePopup)
      map.on('click', 'pix', (e) => {
        const code = (e.features?.[0]?.properties as Record<string, unknown>)?.ixp_code
        if (code) navigate(`/ixp/${code}`)
      })

      setReady(true)
    })

    mapRef.current = map
    return () => { ro.disconnect(); map.remove(); mapRef.current = null }
  }, [navigate])

  // ---------------------------------------------------------------------------
  // Update data when query resolves
  // ---------------------------------------------------------------------------

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready || !data) return

    const asnFeatures = data.features.filter(f => f.properties?.role === 'asn')
    const pixFeatures = data.features.filter(f => f.properties?.role === 'pix')

    ;(map.getSource('asns') as maplibregl.GeoJSONSource)?.setData({
      type: 'FeatureCollection', features: asnFeatures,
    })
    ;(map.getSource('pix') as maplibregl.GeoJSONSource)?.setData({
      type: 'FeatureCollection', features: pixFeatures,
    })
  }, [data, ready])

  // ---------------------------------------------------------------------------
  // Legend counts
  // ---------------------------------------------------------------------------

  const counts = { both: 0, v4_only: 0, v6_only: 0, none: 0, pix: 0 }
  for (const f of data?.features ?? []) {
    const r = f.properties?.role
    if (r === 'pix') { counts.pix++; continue }
    const v = f.properties?.visibility as keyof typeof counts | undefined
    if (v && v in counts) counts[v]++
  }

  return (
    <div className="space-y-2">
      {title !== undefined && (
        <h2 className="text-base font-semibold text-gray-800">
          {title}
        </h2>
      )}
      <div
        className={`relative rounded-lg border border-gray-200 overflow-hidden ${className ?? ''}`}
        style={height !== undefined ? { height } : { aspectRatio: GOLDEN_RATIO }}
      >
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-50 z-10 text-sm text-gray-400 animate-pulse">
            Carregando mapa…
          </div>
        )}
        <div ref={containerRef} className="w-full h-full" />
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-500">
        {counts.both > 0 && (
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full" style={{ background: COLOR_BOTH, opacity: 0.85 }} />
            IPv6 + IPv4 ({counts.both.toLocaleString('pt-BR')})
          </span>
        )}
        {counts.v6_only > 0 && (
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full" style={{ background: COLOR_V6, opacity: 0.85 }} />
            Só IPv6 ({counts.v6_only.toLocaleString('pt-BR')})
          </span>
        )}
        {counts.v4_only > 0 && (
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full" style={{ background: COLOR_V4, opacity: 0.85 }} />
            Só IPv4 ({counts.v4_only.toLocaleString('pt-BR')})
          </span>
        )}
        {counts.none > 0 && (
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full" style={{ background: COLOR_NONE, opacity: 0.6 }} />
            Não visível na FT ({counts.none.toLocaleString('pt-BR')})
          </span>
        )}
        {counts.pix > 0 && (
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full" style={{ background: COLOR_PIX, opacity: 0.85 }} />
            PIX de PTT ({counts.pix.toLocaleString('pt-BR')})
          </span>
        )}
      </div>
    </div>
  )
}
