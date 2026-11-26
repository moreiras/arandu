import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { fetchIXPGeo, fetchIXPAssinantes, type IXPGeoLayer } from '../../services/api'
import {
  MAP_COLORS,
  STATE_OUTLINE_PAINT,
  MAP_DEFAULT_CENTER,
  MAP_DEFAULT_ZOOM,
  bearingInicial, createBaseMapStyle,
  addStandardControls,
  MARKER_OPACITY,
} from './mapTheme'
import { html, htmlSeguro } from '../../lib/html'

// ---------------------------------------------------------------------------
// Configuração das camadas
// ---------------------------------------------------------------------------

// Camadas SICI são montadas no cliente (acessos por município + centróides IBGE);
// as demais vêm do endpoint /geo.
type SiciLayer = 'sici_direct' | 'sici_total'
type MapLayer = IXPGeoLayer | SiciLayer

const isSiciLayer = (l: MapLayer): l is SiciLayer => l.startsWith('sici_')

const LAYERS: { id: MapLayer; label: string; short: string }[] = [
  { id: 'asns_members', label: 'AS participantes: localização dos membros do IXP',              short: 'AS Membros'  },
  { id: 'asns_direct',  label: 'AS com sessão no RS: ASNs com sessão no route server do IXP (LG)', short: 'AS c/ sessão RS' },
  { id: 'asns_origin',  label: 'AS de origem: ASNs BR que originam prefixos no IXP (LG)',     short: 'AS Origem'   },
  { id: 'prefixes_v6',  label: 'Prefixos IPv6: prefixos anunciados no IXP (por cidade)',    short: 'Pref IPv6'   },
  { id: 'prefixes_v4',  label: 'Prefixos IPv4: blocos /20 anunciados no IXP (por cidade)',  short: 'Pref IPv4'   },
  { id: 'sici_direct',  label: 'Assinantes SCM (SICI) dos ASNs com sessão no RS: acessos dos CNPJs desses ASNs (por município)', short: 'Assin. SCM sessão RS' },
  { id: 'sici_total',   label: 'Assinantes SCM (SICI) totais: ASNs com sessão no RS e seus clientes nos AS-paths (por município)', short: 'Assin. SCM totais' },
]

const CENTROIDS_URL = '/municipios-centroides.json'

const BRAZIL_CENTER = MAP_DEFAULT_CENTER
const BRAZIL_ZOOM = MAP_DEFAULT_ZOOM

const MAP_STYLE: maplibregl.StyleSpecification = createBaseMapStyle()

const BR_STATES_URL = '/br-states.geojson'

// ---------------------------------------------------------------------------
// Cores e expressões MapLibre (tema compartilhado — ver mapTheme.ts)
// ---------------------------------------------------------------------------

// AS Membros: azul escuro uniforme
const COLOR_MEMBERS = MAP_COLORS.asMember
// AS Direto: verde escuro uniforme
const COLOR_DIRECT  = MAP_COLORS.asDirect
// AS Origem (apenas origem): violeta
const COLOR_ORIGIN  = MAP_COLORS.asOrigin

// Cor uniforme (string) ou expressão — ambas válidas em paint properties do MapLibre.
const membersColorExpr: string | maplibregl.ExpressionSpecification = COLOR_MEMBERS
const directColorExpr:  string | maplibregl.ExpressionSpecification = COLOR_DIRECT
const originColorExpr:  maplibregl.ExpressionSpecification = [
  'case', ['==', ['get', 'is_direct'], true], COLOR_DIRECT, COLOR_ORIGIN,
]

// Raio dos círculos de AS (e PIX — mesmo tamanho)
const asnRadiusExpr: maplibregl.ExpressionSpecification = [
  'interpolate', ['linear'], ['zoom'],
  3, 3,
  7, 6,
  12, 12,
]

// Prefixos: raio ∝ log(block_count)
const prefixRadiusExpr: maplibregl.ExpressionSpecification = [
  'interpolate', ['exponential', 2], ['zoom'],
  2,  ['+', 2,  ['*', 2,  ['log10', ['+', 1, ['get', 'block_count']]]]],
  5,  ['+', 5,  ['*', 4,  ['log10', ['+', 1, ['get', 'block_count']]]]],
  8,  ['+', 9,  ['*', 7,  ['log10', ['+', 1, ['get', 'block_count']]]]],
  12, ['+', 16, ['*', 12, ['log10', ['+', 1, ['get', 'block_count']]]]],
]

function prefixColorExpr(afi: 'v4' | 'v6'): maplibregl.ExpressionSpecification {
  const brColor = afi === 'v4' ? MAP_COLORS.prefixV4Br : MAP_COLORS.prefixV6Br
  return ['case', ['!=', ['get', 'country'], 'BR'], MAP_COLORS.nonBr, brColor]
}

const prefixOpacityExpr: maplibregl.ExpressionSpecification = [
  'interpolate', ['linear'], ['get', 'block_count'],
  1, 0.25, 10, 0.40, 50, 0.52, 200, 0.62, 500, 0.70,
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const EMPTY_FC: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] }

function pixFC(pix: Array<{ name: string; lat: number; lon: number }>): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: pix.map((p) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
      properties: { name: p.name },
    })),
  }
}

// ---------------------------------------------------------------------------
// Hook: inicializa mapa
// ---------------------------------------------------------------------------

function useMapLibre(
  containerRef: React.RefObject<HTMLDivElement | null>,
  onAsnClick: (asn: number) => void,
) {
  const mapRef = useRef<maplibregl.Map | null>(null)
  const [ready, setReady] = useState(false)
  const onClickRef = useRef(onAsnClick)
  useEffect(() => { onClickRef.current = onAsnClick }, [onAsnClick])

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: BRAZIL_CENTER,
      zoom: BRAZIL_ZOOM,
      bearing: bearingInicial(),
      attributionControl: false,
    })
    addStandardControls(map, { dbip: true })

    map.on('load', () => {
      // Bordas estaduais
      map.addSource('states', { type: 'geojson', data: EMPTY_FC })
      map.addLayer({
        id: 'states-outline', type: 'line', source: 'states',
        paint: STATE_OUTLINE_PAINT,
      })
      fetch(BR_STATES_URL).then((r) => r.json())
        .then((g) => (map.getSource('states') as maplibregl.GeoJSONSource).setData(g))
        .catch(() => {})

      // PIX do IXP — abaixo das camadas de AS (adicionado primeiro)
      map.addSource('ixp-pix', { type: 'geojson', data: EMPTY_FC })
      map.addLayer({
        id: 'layer-pix', type: 'circle', source: 'ixp-pix',
        paint: {
          'circle-radius': asnRadiusExpr,
          'circle-color': MAP_COLORS.pixFill,
          'circle-opacity': 0.9,
          'circle-stroke-width': 1.5,
          'circle-stroke-color': MAP_COLORS.pixStroke,
        },
      })

      // Dados do IXP (AS / prefixos)
      map.addSource('ixp-data', { type: 'geojson', data: EMPTY_FC })

      map.addLayer({
        id: 'layer-prefixes', type: 'circle', source: 'ixp-data',
        layout: { visibility: 'none' },
        paint: {
          'circle-radius': prefixRadiusExpr,
          'circle-color': prefixColorExpr('v4'),
          'circle-opacity': prefixOpacityExpr,
          'circle-stroke-width': 0,
        },
      })

      map.addLayer({
        id: 'layer-asns', type: 'circle', source: 'ixp-data',
        layout: { visibility: 'none' },
        paint: {
          'circle-radius': asnRadiusExpr,
          'circle-color': membersColorExpr,
          'circle-opacity': 0.85,
          'circle-stroke-width': 0.8,
          'circle-stroke-color': '#ffffff',
        },
      })

      // Assinantes SICI por município — fonte própria, montada no cliente
      map.addSource('ixp-sici', { type: 'geojson', data: EMPTY_FC })
      map.addLayer({
        id: 'layer-sici', type: 'circle', source: 'ixp-sici',
        layout: { visibility: 'none' },
        paint: {
          'circle-radius': 3,
          'circle-color': MAP_COLORS.v4Strong,
          'circle-opacity': MARKER_OPACITY,
          'circle-stroke-width': 0.8,
          'circle-stroke-color': '#ffffff',
        },
      })

      // Popups
      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, maxWidth: '220px' })

      const showAsnPopup = (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
        const f = e.features?.[0]; if (!f) return
        map.getCanvas().style.cursor = 'pointer'
        const p = f.properties as Record<string, unknown>
        const label = p.name ? `AS${p.asn}: ${p.name}` : `AS${p.asn}`
        const loc   = p.city ? `${p.uf ?? ''}/${p.city}` : (p.uf as string ?? '')
        popup.setLngLat(e.lngLat).setHTML(html`<strong>${label}</strong>${loc ? htmlSeguro`<br/>${loc}` : ''}`).addTo(map)
      }

      const showPrefixPopup = (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
        const f = e.features?.[0]; if (!f) return
        map.getCanvas().style.cursor = 'pointer'
        const p    = f.properties as Record<string, unknown>
        const city = p.city ? `${p.uf ?? ''}/${p.city}` : (p.country as string ?? '?')
        const cnt  = (p.block_count as number ?? 0).toLocaleString('pt-BR')
        popup.setLngLat(e.lngLat).setHTML(html`<strong>${city}</strong><br/>${cnt} blocos /20`).addTo(map)
      }

      const showPixPopup = (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
        const f = e.features?.[0]; if (!f) return
        map.getCanvas().style.cursor = 'crosshair'
        const name = (f.properties as Record<string, unknown>).name as string ?? ''
        popup.setLngLat(e.lngLat).setHTML(html`<strong>${name}</strong>`).addTo(map)
      }

      map.on('mouseenter', 'layer-prefixes', showPrefixPopup)
      map.on('mouseleave', 'layer-prefixes', () => { map.getCanvas().style.cursor = ''; popup.remove() })
      map.on('mouseenter', 'layer-asns', showAsnPopup)
      map.on('mouseleave', 'layer-asns', () => { map.getCanvas().style.cursor = ''; popup.remove() })
      const showSiciPopup = (e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
        const f = e.features?.[0]; if (!f) return
        map.getCanvas().style.cursor = 'pointer'
        const p = f.properties as Record<string, unknown>
        const cnt = Number(p.acessos ?? 0).toLocaleString('pt-BR')
        popup.setLngLat(e.lngLat).setHTML(html`<strong>${p.nome} <span style="color:#94a3b8">${p.uf}</span></strong><br/>${cnt} assinantes SCM`).addTo(map)
      }

      map.on('mouseenter', 'layer-sici', showSiciPopup)
      map.on('mouseleave', 'layer-sici', () => { map.getCanvas().style.cursor = ''; popup.remove() })
      map.on('mouseenter', 'layer-pix', showPixPopup)
      map.on('mouseleave', 'layer-pix', () => { map.getCanvas().style.cursor = ''; popup.remove() })

      map.on('click', 'layer-asns', (e) => {
        const asn = e.features?.[0]?.properties?.asn
        if (asn != null) onClickRef.current(Number(asn))
      })

      setReady(true)
    })

    mapRef.current = map
    return () => { map.remove(); mapRef.current = null }
  }, [containerRef])

  return { mapRef, ready }
}

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

interface Props { code: string; date?: string }

export function IXPGeoMap({ code, date }: Props) {
  const [activeLayer, setActiveLayer] = useState<MapLayer>('asns_members')
  const isSici = isSiciLayer(activeLayer)
  // Nas camadas SICI o /geo só fornece os PIX (iguais em qualquer camada)
  const geoLayer: IXPGeoLayer = isSici ? 'asns_members' : activeLayer
  const containerRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const { mapRef, ready } = useMapLibre(containerRef, (asn) => navigate(`/asn/${asn}`))

  const { data, isLoading, isError } = useQuery({
    queryKey: ['ixp-geo', code, geoLayer, date],
    queryFn: () => fetchIXPGeo(code, geoLayer, date),
    staleTime: Infinity, gcTime: Infinity,
    retry: false,
  })

  // Mesma query key da IXPPage — compartilha o cache
  const { data: assinantes, isLoading: loadingSici, isError: errorSici } = useQuery({
    queryKey: ['ixp-assinantes', code, date],
    queryFn: () => fetchIXPAssinantes(code, date),
    enabled: isSici,
    staleTime: Infinity, gcTime: Infinity,
  })

  const { data: centroids } = useQuery<Record<string, [number, number]>>({
    queryKey: ['municipios-centroides'],
    queryFn: () => fetch(CENTROIDS_URL).then((r) => r.json()),
    enabled: isSici,
    staleTime: Infinity, gcTime: Infinity,
  })

  const siciMunicipios = !isSici || !assinantes ? null
    : activeLayer === 'sici_direct' ? assinantes.municipios_diretos : assinantes.municipios_totais

  const siciFC = useMemo((): GeoJSON.FeatureCollection => {
    if (!siciMunicipios || !centroids) return EMPTY_FC
    return {
      type: 'FeatureCollection',
      features: siciMunicipios.flatMap((m) => {
        const c = centroids[m.ibge]
        if (!c) return []
        return [{
          type: 'Feature' as const,
          geometry: { type: 'Point' as const, coordinates: c },
          properties: { ibge: m.ibge, nome: m.nome, uf: m.uf, acessos: m.acessos },
        }]
      }),
    }
  }, [siciMunicipios, centroids])

  const siciTotal = siciMunicipios?.reduce((acc, m) => acc + m.acessos, 0) ?? 0

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return

    // Atualiza marcadores PIX
    const pixSource = map.getSource('ixp-pix') as maplibregl.GeoJSONSource | undefined
    const validPix = (data?.ixp_pix ?? []).filter(
      (p): p is { name: string; lat: number; lon: number } => p.lat != null && p.lon != null
    )
    pixSource?.setData(validPix.length ? pixFC(validPix) : EMPTY_FC)

    // Atualiza dados da camada ativa
    const dataSource = map.getSource('ixp-data') as maplibregl.GeoJSONSource | undefined
    const siciSource = map.getSource('ixp-sici') as maplibregl.GeoJSONSource | undefined
    if (!dataSource || !siciSource) return
    dataSource.setData(isSici ? EMPTY_FC : (data ?? EMPTY_FC))
    siciSource.setData(isSici ? siciFC : EMPTY_FC)

    const isPrefix = activeLayer.startsWith('prefixes_')
    map.setLayoutProperty('layer-prefixes', 'visibility', isPrefix  ? 'visible' : 'none')
    map.setLayoutProperty('layer-asns',     'visibility', !isPrefix && !isSici ? 'visible' : 'none')
    map.setLayoutProperty('layer-sici',     'visibility', isSici ? 'visible' : 'none')

    if (isSici) {
      // Raio ∝ √acessos (área proporcional ao valor), com o piso do marcador-padrão
      // — mesmo critério do mapa de acessos por município (AccessMunicipioMap)
      const maxAcessos = siciFC.features.reduce(
        (mx, f) => Math.max(mx, Number(f.properties?.acessos ?? 0)), 0) || 1
      const sq = Math.sqrt(maxAcessos)
      map.setPaintProperty('layer-sici', 'circle-radius', [
        'interpolate', ['linear'], ['zoom'],
        3,  ['interpolate', ['linear'], ['sqrt', ['get', 'acessos']], 0, 3, sq, 16],
        7,  ['interpolate', ['linear'], ['sqrt', ['get', 'acessos']], 0, 5, sq, 32],
        12, ['interpolate', ['linear'], ['sqrt', ['get', 'acessos']], 0, 9, sq, 48],
      ])
      map.setPaintProperty('layer-sici', 'circle-color',
        activeLayer === 'sici_direct' ? MAP_COLORS.asDirect : MAP_COLORS.v4Strong)
    } else if (isPrefix) {
      const afi = activeLayer.endsWith('v6') ? 'v6' : 'v4'
      map.setPaintProperty('layer-prefixes', 'circle-color', prefixColorExpr(afi))
    } else {
      const colorExpr =
        activeLayer === 'asns_direct'  ? directColorExpr  :
        activeLayer === 'asns_origin'  ? originColorExpr  :
        membersColorExpr
      map.setPaintProperty('layer-asns', 'circle-color', colorExpr)
    }
  }, [data, siciFC, isSici, activeLayer, ready, mapRef])

  const featureCount = isSici ? siciFC.features.length : (data?.features?.length ?? 0)
  const loading = isSici ? loadingSici || !centroids : isLoading
  const failed  = isSici ? errorSici : isError
  const isPrefix = activeLayer.startsWith('prefixes_')

  return (
    <div className="space-y-2">
      {/* Seletor de camada */}
      <div className="flex flex-wrap gap-1">
        {LAYERS.map((l) => (
          <button key={l.id} onClick={() => setActiveLayer(l.id)} title={l.label}
            className={`text-xs px-2 py-1 rounded border transition-colors ${
              activeLayer === l.id
                ? 'bg-gray-700 text-white border-gray-700'
                : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
            }`}>
            {l.short}
          </button>
        ))}
      </div>

      {/* Descrição + contagem */}
      <div className="flex items-center gap-2 text-xs text-gray-500 min-h-[1.25rem]">
        <span>{LAYERS.find((l) => l.id === activeLayer)?.label}</span>
        {!loading && !failed && featureCount > 0 && (
          <span className="text-gray-400">
            · {featureCount.toLocaleString('pt-BR')} {isSici ? 'municípios' : isPrefix ? 'cidades' : 'ASNs'}
            {isSici && <> · {siciTotal.toLocaleString('pt-BR')} assinantes
              {assinantes?.mes_referencia && <> (SICI {assinantes.mes_referencia})</>}</>}
          </span>
        )}
      </div>

      {/* Mapa */}
      <div className="relative rounded-lg border border-gray-200 overflow-hidden" style={{ height: 437 }}>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10 text-sm text-gray-400">
            Carregando…
          </div>
        )}
        {failed && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-50 z-10 text-sm text-gray-400">
            Dados de geolocalização não disponíveis para este snapshot
          </div>
        )}
        <div ref={containerRef} className="w-full h-full" />
      </div>

      {/* Legenda */}
      {isSici ? (
        <div className="flex flex-wrap gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full" style={{
              background: activeLayer === 'sici_direct' ? MAP_COLORS.asDirect : MAP_COLORS.v4Strong,
              opacity: MARKER_OPACITY,
            }} />
            Acessos SCM (B2C + B2B) no município
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full opacity-90" style={{ background: MAP_COLORS.pixFill }} />
            PIX do IXP
          </span>
          <span className="text-gray-400">
            · Área ∝ assinantes · {activeLayer === 'sici_direct'
              ? 'CNPJs dos ASNs com sessão no route server'
              : 'CNPJs dos ASNs com sessão no route server e dos ASes nos AS-paths anunciados (deduplicado por CNPJ)'}
          </span>
        </div>
      ) : isPrefix ? (
        <div className="flex flex-wrap gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full" style={{ background: MAP_COLORS.prefixV6Br, opacity: 0.7 }} />IPv6 BR
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full" style={{ background: MAP_COLORS.prefixV4Br, opacity: 0.7 }} />IPv4 BR
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full" style={{ background: MAP_COLORS.nonBr, opacity: 0.8 }} />Não-BR
          </span>
          <span className="text-gray-400">· Opacidade ∝ densidade · Tamanho ∝ log(blocos)</span>
        </div>
      ) : (
        <div className="flex flex-wrap gap-4 text-xs text-gray-500">
          {activeLayer === 'asns_members' && (
            <span className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded-full opacity-85" style={{ background: COLOR_MEMBERS }} />
              AS Membro
            </span>
          )}
          {activeLayer === 'asns_direct' && (
            <span className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded-full opacity-85" style={{ background: COLOR_DIRECT }} />
              AS com sessão no RS
            </span>
          )}
          {activeLayer === 'asns_origin' && (<>
            <span className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded-full opacity-85" style={{ background: COLOR_DIRECT }} />
              AS com sessão no RS (também anunciado)
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded-full opacity-85" style={{ background: COLOR_ORIGIN }} />
              AS Origem (só origem)
            </span>
          </>)}
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-full opacity-90" style={{ background: MAP_COLORS.pixFill }} />
            PIX do IXP
          </span>
          <span className="text-gray-400">· Clique no AS para ver detalhes</span>
        </div>
      )}
    </div>
  )
}
