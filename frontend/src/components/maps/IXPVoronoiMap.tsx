/**
 * Mapa de "áreas de influência" dos PTTs do IX.br por vizinho mais próximo geodésico.
 *
 * Método (Voronoi esférico exato + topologia compartilhada):
 *  1. Diagrama de Voronoi esférico exato dos PTTs (d3-geo-voronoi), recortado
 *     pelo contorno real do Brasil (união dos estados via turf) — polígonos
 *     vetoriais de verdade, não uma grade rasterizada, então as fronteiras
 *     saem sempre retas/lisas, sem serrilhado.
 *  2. Os polígonos recortados viram uma única topologia (topojson-server,
 *     quantizada) que funde os vértices coincidentes de fronteiras vizinhas
 *     num único arco compartilhado — garante que a borda entre dois PTTs
 *     vizinhos seja literalmente a mesma linha dos dois lados.
 *  3. Coloração por grafo de adjacência (welsh-powell sobre os vizinhos reais,
 *     via topojson-client.neighbors), restrita a tons de verde/amarelo/azul —
 *     evita que dois PTTs que se tocam recebam o mesmo tom.
 *  4. Preenchimento sem contorno (borda transparente): só a mudança de cor
 *     entre polígonos vizinhos marca a fronteira.
 *  5. Área (km²) dominada por cada PTT = área geodésica do polígono recortado.
 *
 * Tooltip ao passar o mouse sobre a área de um PTT: estatísticas do PTT + da
 * "região" (conjunto de ASNs/prefixos cujo PTT mais próximo é aquele).
 */
import { escapar } from '../../lib/html'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { geoVoronoi } from 'd3-geo-voronoi'
import * as turf from '@turf/turf'
import { topology } from 'topojson-server'
import { feature as topoFeature, neighbors as topoNeighbors } from 'topojson-client'
import type { Topology, GeometryCollection } from 'topojson-specification'
import { IXP_COORDS } from './ixpCoords'
import type { IXPIndexEntry } from '../../types/api'
import { fetchMapAsns, fetchMapPrefixes, fetchIXPresence, type IXPresenceResponse } from '../../services/api'
import { STATE_OUTLINE_PAINT, MAP_DEFAULT_CENTER, MAP_DEFAULT_ZOOM, bearingInicial, createBaseMapStyle, addStandardControls } from './mapTheme'

// ---------------------------------------------------------------------------
// Constantes do mapa
// ---------------------------------------------------------------------------

const BRAZIL_CENTER = MAP_DEFAULT_CENTER
const BRAZIL_ZOOM = MAP_DEFAULT_ZOOM
const BR_STATES_URL = '/br-states.geojson'
const EMPTY_FC: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] }

const MAP_STYLE: maplibregl.StyleSpecification = createBaseMapStyle()

// Paleta com exatamente 5 tons (pedido do usuário: 2 azuis, 2 verdes, 1
// amarelo) — o grafo real de adjacência dos PTTs precisa de no máximo 5
// cores (Welsh-Powell sobre ~40 nós), então essa paleta cobre exatamente o
// necessário sem repetir tom entre vizinhos. Nenhum tom âmbar/laranja — o
// amarelo é puro para não ser confundido com a família azul/verde.
const PALETTE = [
  '#2e7d32', // verde escuro
  '#0277bd', // azul escuro
  '#81c784', // verde claro
  '#4fc3f7', // azul claro
  '#fdd835', // amarelo
]

// ---------------------------------------------------------------------------
// PTTs
// ---------------------------------------------------------------------------

interface Ptt {
  code: string
  lat: number
  lon: number
  latRad: number
  lonRad: number
}

const D2R = Math.PI / 180

/** Distância great-circle aproximada (haversine), em km. */
function haversineKm(lat1Rad: number, lon1Rad: number, lat2Rad: number, lon2Rad: number): number {
  const dLat = lat2Rad - lat1Rad
  const dLon = lon2Rad - lon1Rad
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1Rad) * Math.cos(lat2Rad) * Math.sin(dLon / 2) ** 2
  return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

/** Lista ordenada de PTTs (ordem estável, usada só para exibição/rótulos). */
const PTTS: Ptt[] = Object.entries(IXP_COORDS)
  .sort(([a], [b]) => a.localeCompare(b))
  .map(([code, [lat, lon]]) => ({
    code,
    lat,
    lon,
    latRad: lat * D2R,
    lonRad: lon * D2R,
  }))

/** Índice do PTT mais próximo de um ponto (lat/lon em graus). -1 se não houver.
 *  Usado só para classificar ASNs/prefixos nas estatísticas (tooltip) — é
 *  matematicamente equivalente a "em qual célula de Voronoi o ponto cai". */
function nearestPttIdx(lat: number, lon: number): number {
  const latRad = lat * D2R
  const lonRad = lon * D2R
  let best = -1
  let bestD = Infinity
  for (let i = 0; i < PTTS.length; i++) {
    const d = haversineKm(latRad, lonRad, PTTS[i].latRad, PTTS[i].lonRad)
    if (d < bestD) {
      bestD = d
      best = i
    }
  }
  return best
}

// ---------------------------------------------------------------------------
// Regiões: Voronoi esférico exato, recortado ao Brasil, com topologia
// compartilhada, coloração de grafo e mesh de fronteiras.
// ---------------------------------------------------------------------------

interface Regions {
  fillFC: GeoJSON.FeatureCollection // 1 polígono por PTT, com fillColor/code
  brazil: GeoJSON.Feature<GeoJSON.Polygon | GeoJSON.MultiPolygon> // usado no hit-test do hover/click
  areaByCode: Record<string, number> // km² dominados por PTT
}

type StatesFC = GeoJSON.FeatureCollection<GeoJSON.Polygon | GeoJSON.MultiPolygon>

/** Coloração gulosa (Welsh-Powell): ordena por grau decrescente e atribui a
 *  menor cor ainda não usada pelos vizinhos já coloridos — garante que dois
 *  nós adjacentes no grafo real de fronteiras nunca compartilhem cor. */
function colorGraph(adjacency: number[][]): number[] {
  const n = adjacency.length
  const order = [...Array(n).keys()].sort((a, b) => adjacency[b].length - adjacency[a].length)
  const color = new Array<number>(n).fill(-1)
  for (const v of order) {
    const used = new Set(adjacency[v].map((u) => color[u]).filter((c) => c >= 0))
    let c = 0
    while (used.has(c)) c++
    color[v] = c
  }
  return color
}

// Anel de pontos-fantasma bem afastados do Brasil: sem eles, os PTTs nas
// bordas do conjunto (AC, RR, CE, RS...) ficam na casca convexa do diagrama
// de Voronoi ESFÉRICO — nesse caso a célula não tem limite natural e se
// estende por boa parte do globo (aparecendo como um polígono gigante que
// cruza todos os outros quando recortado ao Brasil, e deixando o PTT que
// originou aquela célula parecendo "sem preenchimento" onde ela deveria
// estar). Cercando os PTTs reais com um anel de sites fora do território,
// todo PTT real vira um ponto interior do diagrama e sua célula fica
// naturalmente limitada.
const VORONOI_GHOST_CENTER: [number, number] = [-52, -14] // lon, lat — ~centro do Brasil
const VORONOI_GHOST_RADIUS_KM = 4500
const VORONOI_GHOST_COUNT = 24
const GHOST_PREFIX = '__ghost__'

function buildGhostRing(): Ptt[] {
  const [lon0, lat0] = VORONOI_GHOST_CENTER
  const ghosts: Ptt[] = []
  for (let i = 0; i < VORONOI_GHOST_COUNT; i++) {
    const bearing = (360 / VORONOI_GHOST_COUNT) * i
    const [lon, lat] = turf.destination(
      turf.point([lon0, lat0]),
      VORONOI_GHOST_RADIUS_KM,
      bearing,
      { units: 'kilometers' },
    ).geometry.coordinates
    ghosts.push({ code: `${GHOST_PREFIX}${i}`, lat, lon, latRad: lat * D2R, lonRad: lon * D2R })
  }
  return ghosts
}

function buildRegions(states: StatesFC): Regions {
  // 1) Diagrama de Voronoi esférico exato (um polígono por PTT + anel-fantasma
  //    para limitar as células dos PTTs de borda — ver buildGhostRing acima).
  const voronoi = geoVoronoi<Ptt>().x((p) => p.lon).y((p) => p.lat)
  const cells = voronoi.polygons([...PTTS, ...buildGhostRing()])

  // 2) Território brasileiro como um único polígono (união dos estados).
  const brazil = turf.union(
    turf.featureCollection(states.features) as unknown as Parameters<typeof turf.union>[0],
  ) as GeoJSON.Feature<GeoJSON.Polygon | GeoJSON.MultiPolygon> | null
  if (!brazil) throw new Error('Falha ao unir os polígonos dos estados (br-states.geojson)')

  // 3) Recorta cada célula de Voronoi ao território — só a partir daqui os
  //    polígonos passam a ter a forma real "área de influência dentro do Brasil".
  const clipped: GeoJSON.Feature<GeoJSON.Polygon | GeoJSON.MultiPolygon>[] = []
  for (const cell of cells.features) {
    const code = cell.properties.site.code
    if (code.startsWith(GHOST_PREFIX)) continue // célula do anel-fantasma — só existe pra limitar as reais
    const inter = turf.intersect(
      turf.featureCollection([cell, brazil]) as unknown as Parameters<typeof turf.intersect>[0],
    )
    if (!inter) continue
    clipped.push({
      type: 'Feature',
      geometry: inter.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon,
      properties: { code },
    })
  }

  // 4) Topologia compartilhada (quantizada): funde vértices coincidentes das
  //    fronteiras entre polígonos vizinhos num único arco por fronteira —
  //    é isso que elimina o serrilhado e permite extrair o mesh de bordas.
  const clippedFC: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: clipped }
  const topo = topology({ ptts: clippedFC }, 1e5) as Topology
  const geomCollection = topo.objects.ptts as GeometryCollection

  // 5) Adjacência real (quem compartilha arco com quem) + coloração de grafo.
  const adjacency = topoNeighbors(geomCollection.geometries)
  const colorIdx = colorGraph(adjacency)

  // 6) Preenchimento final: geometria derivada da topologia (arcos
  //    compartilhados, sem discrepância de ponto flutuante entre vizinhos).
  const finalFC = topoFeature(topo, geomCollection) as GeoJSON.FeatureCollection<
    GeoJSON.Polygon | GeoJSON.MultiPolygon,
    { code: string }
  >
  const areaByCode: Record<string, number> = {}
  const fillFeatures: GeoJSON.Feature[] = finalFC.features.map((f, i) => {
    const code = f.properties.code
    areaByCode[code] = turf.area(f as unknown as Parameters<typeof turf.area>[0]) / 1e6
    return {
      type: 'Feature',
      geometry: f.geometry,
      properties: { code, fillColor: PALETTE[colorIdx[i] % PALETTE.length] },
    }
  })

  return {
    fillFC: { type: 'FeatureCollection', features: fillFeatures },
    brazil,
    areaByCode,
  }
}

// ---------------------------------------------------------------------------
// Estatísticas por PTT (tooltip)
// ---------------------------------------------------------------------------

interface PttStats {
  name: string
  uf: string
  members: number // AS participando (ixbr_members_count)
  membersBR: number // destes, BR (ix-presence ∩ ASNs BR geolocalizados)
  origin: number // AS originando prefixos (asn_origin_union_count)
  originBR: number // destes, BR (br_asns_origin_union_count)
  hqN: number // ASes com sede na região
  hqMembers: number
  hqOrigin: number
  opN: number // ASes operando na região (sede ∪ prefixos geolocalizados)
  opMembers: number
  opOrigin: number
  areaKm2: number
}

interface GeoFeature {
  geometry: { coordinates: [number, number] }
  properties: Record<string, unknown>
}
function buildStats(
  ixps: IXPIndexEntry[],
  asnGeo: { features: GeoFeature[] } | undefined,
  prefixGeo: { features: GeoFeature[] } | undefined,
  presence: IXPresenceResponse | undefined,
  areaByCode: Record<string, number>,
): Record<string, PttStats> {
  const codeToIdx = new Map(PTTS.map((p, i) => [p.code, i]))
  const idxFor = (lat: number, lon: number) => nearestPttIdx(lat, lon)

  // Conjuntos BR geolocalizados e classificação por PTT (sede e prefixos).
  const brAsns = new Set<number>()
  const hqByCode: Map<string, Set<number>> = new Map()
  const opByCode: Map<string, Set<number>> = new Map()
  for (const p of PTTS) {
    hqByCode.set(p.code, new Set())
    opByCode.set(p.code, new Set())
  }

  for (const f of asnGeo?.features ?? []) {
    const asn = Number(f.properties.asn)
    if (!asn) continue
    brAsns.add(asn)
    const [lon, lat] = f.geometry.coordinates
    const idx = idxFor(lat, lon)
    if (idx < 0) continue
    const code = PTTS[idx].code
    hqByCode.get(code)!.add(asn)
    opByCode.get(code)!.add(asn)
  }

  for (const f of prefixGeo?.features ?? []) {
    const asn = Number(f.properties.origin_asn)
    if (!asn) continue
    const [lon, lat] = f.geometry.coordinates
    const idx = idxFor(lat, lon)
    if (idx < 0) continue
    opByCode.get(PTTS[idx].code)!.add(asn)
  }

  // ix-presence: m (membro do PTT), o (origina prefixos no PTT) por ASN.
  const memberOf = new Map<number, Set<string>>()
  const originOf = new Map<number, Set<string>>()
  const brMembersByCode: Record<string, number> = {}
  for (const p of PTTS) brMembersByCode[p.code] = 0
  for (const [asnStr, rec] of Object.entries(presence?.asns ?? {})) {
    const asn = Number(asnStr)
    if (rec.m?.length) memberOf.set(asn, new Set(rec.m))
    if (rec.o?.length) originOf.set(asn, new Set(rec.o))
    if (brAsns.has(asn)) {
      for (const code of rec.m ?? []) {
        if (code in brMembersByCode) brMembersByCode[code]++
      }
    }
  }

  const countWith = (asns: Set<number>, by: Map<number, Set<string>>, code: string) => {
    let n = 0
    for (const asn of asns) if (by.get(asn)?.has(code)) n++
    return n
  }

  const out: Record<string, PttStats> = {}
  for (const ixp of ixps) {
    if (!codeToIdx.has(ixp.code)) continue
    const code = ixp.code
    const hq = hqByCode.get(code)!
    const op = opByCode.get(code)!
    out[code] = {
      name: ixp.name,
      uf: ixp.uf,
      members: ixp.ixbr_members_count ?? 0,
      membersBR: brMembersByCode[code] ?? 0,
      origin: ixp.asn_origin_union_count ?? 0,
      originBR: ixp.br_asns_origin_union_count ?? 0,
      hqN: hq.size,
      hqMembers: countWith(hq, memberOf, code),
      hqOrigin: countWith(hq, originOf, code),
      opN: op.size,
      opMembers: countWith(op, memberOf, code),
      opOrigin: countWith(op, originOf, code),
      areaKm2: areaByCode[code] ?? 0,
    }
  }
  return out
}

// ---------------------------------------------------------------------------
// Helpers de formatação / tooltip
// ---------------------------------------------------------------------------

const fmt = (n: number) => n.toLocaleString('pt-BR')
const fmtKm2 = (n: number) =>
  n >= 1e6
    ? `${(n / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi`
    : Math.round(n).toLocaleString('pt-BR')

function tooltipHTML(s: PttStats): string {
  return (
    `<strong style="font-size:13px">IX.br ${escapar(s.name)}${s.uf ? `, ${escapar(s.uf)}` : ''}</strong>` +
    `<div style="font-size:0.85em;color:#374151;line-height:1.6;margin-top:3px">` +
    `👥 ${escapar(fmt(s.members))} AS participando, ${escapar(fmt(s.membersBR))} destes BR<br/>` +
    `📢 ${escapar(fmt(s.origin))} AS originando prefixos, ${escapar(fmt(s.originBR))} destes BR<br/>` +
    `🏢 ${escapar(fmt(s.hqN))} ASes com sede na região <span style="color:#6b7280">(${escapar(fmt(s.hqMembers))} membros do PTT, ${escapar(fmt(s.hqOrigin))} originando prefixos)</span><br/>` +
    `📡 ${escapar(fmt(s.opN))} ASes operando na região <span style="color:#6b7280">(${escapar(fmt(s.opMembers))} membros do PTT, ${escapar(fmt(s.opOrigin))} originando prefixos)</span><br/>` +
    `<span style="color:#9ca3af">📐 área de influência ~${escapar(fmtKm2(s.areaKm2))} km²</span>` +
    `</div>`
  )
}

// ---------------------------------------------------------------------------
// Componente
// ---------------------------------------------------------------------------

interface Props {
  ixps: IXPIndexEntry[]
  date?: string
  height?: number
}

export function IXPVoronoiMap({ ixps, date, height = 460 }: Props) {
  const navigate = useNavigate()

  // Contorno do Brasil (carregado uma vez).
  const { data: states } = useQuery({
    queryKey: ['br-states-geojson'],
    queryFn: () => fetch(BR_STATES_URL).then((r) => r.json() as Promise<StatesFC>),
    staleTime: Infinity, gcTime: Infinity,
  })

  // Dados de geolocalização e presença (compartilhados/cacheados com outras páginas).
  const { data: asnGeo } = useQuery({
    queryKey: ['map-asns', date],
    queryFn: () => fetchMapAsns(date ?? undefined) as unknown as Promise<{ features: GeoFeature[] }>,
    staleTime: Infinity, gcTime: Infinity,
    retry: false,
  })
  const { data: prefixGeo } = useQuery({
    queryKey: ['map-prefixes', date],
    queryFn: () => fetchMapPrefixes(date ?? undefined) as unknown as Promise<{ features: GeoFeature[] }>,
    staleTime: Infinity, gcTime: Infinity,
    retry: false,
  })
  const { data: presence } = useQuery({
    queryKey: ['asn-ix-presence', date],
    queryFn: () => fetchIXPresence(date ?? undefined),
    staleTime: Infinity, gcTime: Infinity,
    retry: false,
  })

  // Regiões (dependem só do contorno) e estatísticas (dependem dos dados).
  const regions = useMemo(() => (states ? buildRegions(states) : null), [states])
  const stats = useMemo(
    () => (regions ? buildStats(ixps, asnGeo, prefixGeo, presence, regions.areaByCode) : {}),
    [ixps, asnGeo, prefixGeo, presence, regions],
  )

  // Refs lidos pelos handlers do mapa (registrados uma vez no load).
  const regionsRef = useRef<Regions | null>(null)
  const statsRef = useRef<Record<string, PttStats>>({})
  useEffect(() => { regionsRef.current = regions }, [regions])
  useEffect(() => { statsRef.current = stats }, [stats])

  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const regionsAddedRef = useRef(false)
  const [ready, setReady] = useState(false)

  // ---- init do mapa ----
  useEffect(() => {
    const el = containerRef.current
    if (!el || mapRef.current) return

    const map = new maplibregl.Map({
      container: el,
      style: MAP_STYLE,
      center: BRAZIL_CENTER,
      zoom: BRAZIL_ZOOM,
      bearing: bearingInicial(),
      attributionControl: false,
    })
    addStandardControls(map, { dbip: true })

    map.on('load', () => {
      // Contorno estadual
      map.addSource('states', { type: 'geojson', data: EMPTY_FC })
      map.addLayer({
        id: 'states-outline',
        type: 'line',
        source: 'states',
        paint: STATE_OUTLINE_PAINT,
      })
      fetch(BR_STATES_URL)
        .then((r) => r.json())
        .then((g) => (map.getSource('states') as maplibregl.GeoJSONSource).setData(g))
        .catch(() => {})

      // PTTs: marcadores + rótulos (por cima de tudo)
      map.addSource('ptts', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: PTTS.map((p): GeoJSON.Feature => ({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
            properties: { code: p.code.toUpperCase() },
          })),
        },
      })
      map.addLayer({
        id: 'ptt-dots',
        type: 'circle',
        source: 'ptts',
        paint: {
          'circle-radius': 3.2,
          'circle-color': '#0f172a',
          'circle-stroke-width': 1.5,
          'circle-stroke-color': '#ffffff',
        },
      })
      map.addLayer({
        id: 'ptt-labels',
        type: 'symbol',
        source: 'ptts',
        layout: {
          'text-field': ['get', 'code'],
          'text-font': ['Noto Sans Regular'],
          'text-size': 10,
          'text-offset': [0, 1.0],
          'text-anchor': 'top',
          'text-allow-overlap': false,
        },
        paint: {
          'text-color': '#0f172a',
          'text-halo-color': '#ffffff',
          'text-halo-width': 1.4,
        },
      })

      // Popup analítico (recalcula PTT sob o cursor via nearest-neighbor,
      // restrito ao território — fora do Brasil não tem tooltip).
      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, maxWidth: '300px' })

      const codeAt = (lng: number, lat: number): string | null => {
        const r = regionsRef.current
        if (!r) return null
        if (!turf.booleanPointInPolygon([lng, lat], r.brazil)) return null
        const idx = nearestPttIdx(lat, lng)
        return idx >= 0 ? PTTS[idx].code : null
      }

      map.on('mousemove', (e) => {
        const code = codeAt(e.lngLat.lng, e.lngLat.lat)
        const s = code ? statsRef.current[code] : null
        if (!s) {
          map.getCanvas().style.cursor = ''
          popup.remove()
          return
        }
        map.getCanvas().style.cursor = 'pointer'
        popup.setLngLat(e.lngLat).setHTML(tooltipHTML(s)).addTo(map)
      })
      map.on('mouseout', () => popup.remove())
      map.on('click', (e) => {
        const code = codeAt(e.lngLat.lng, e.lngLat.lat)
        if (code) navigate(`/ixp/${code}`)
      })

      setReady(true)
    })

    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
      regionsAddedRef.current = false
    }
  }, [navigate])

  // ---- adiciona/atualiza os polígonos (preenchimento, sem borda) quando as regiões ficam prontas ----
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready || !regions) return
    if (!regionsAddedRef.current) {
      map.addSource('ptt-fill', { type: 'geojson', data: regions.fillFC })
      map.addLayer(
        {
          id: 'ptt-fill',
          type: 'fill',
          source: 'ptt-fill',
          paint: {
            'fill-color': ['get', 'fillColor'],
            'fill-opacity': 0.42,
            'fill-outline-color': 'rgba(0,0,0,0)', // borda transparente — só a cor separa os vizinhos
          },
        },
        'states-outline', // abaixo do contorno estadual e dos marcadores
      )
      regionsAddedRef.current = true
    } else {
      ;(map.getSource('ptt-fill') as maplibregl.GeoJSONSource).setData(regions.fillFC)
    }
  }, [ready, regions])

  return (
    <div
      ref={containerRef}
      style={{ height }}
      className="w-full rounded-lg overflow-hidden border border-gray-200"
    />
  )
}
