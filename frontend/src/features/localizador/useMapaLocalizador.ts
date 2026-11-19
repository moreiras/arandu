// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useCallback, useEffect, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import {
  BearingToggleControl, bearingInicial, MAP_DEFAULT_CENTER, MAP_DEFAULT_ZOOM, STATE_OUTLINE_PAINT, createBaseMapStyle,
} from '../../components/maps/mapTheme'
import { featuresBolhas, featuresPix, featuresScm, featuresSedes, featuresSici } from './balloes'
import type { AsnDot, Bubble, InfoAsn, MunicipioSici, ScmGeoFeature } from './tipos'
import type { GrupoCoord, Ponto } from './calculos'
import { circlePolygon } from './geo'
import { BR_STATES_URL, EMPTY_FC, SICI_COLOR } from './tipos'
import { DBIP_ATRIBUICAO_HTML } from '../../lib/atribuicoes'

const MAP_STYLE: maplibregl.StyleSpecification = createBaseMapStyle()

// Raio da bolha ∝ log(nº de prefixos) — equivalente ao antigo bubbleRadius().
const bubbleRadiusExpr: maplibregl.ExpressionSpecification =
  ['+', 4, ['*', 3, ['log10', ['+', 1, ['get', 'count']]]]]
const bubbleColorExpr: maplibregl.ExpressionSpecification = ['get', 'color']

// Elemento DOM do marcador (pino azul arrastável).
function makePinElement(): HTMLDivElement {
  const el = document.createElement('div')
  el.style.cssText =
    'width:18px;height:18px;background:#2563eb;border:3px solid white;border-radius:50%;box-shadow:0 2px 8px rgba(0,0,0,.55);cursor:grab'
  return el
}

type Evento = maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }

/** Fontes e camadas do Localizador (executa no `load` do mapa). A ordem de adição é a de desenho, de baixo para cima. */
export function adicionarCamadas(map: maplibregl.Map): void {
  // Bordas estaduais
  map.addSource('states', { type: 'geojson', data: EMPTY_FC })
  map.addLayer({ id: 'states-outline', type: 'line', source: 'states', paint: STATE_OUTLINE_PAINT })
  fetch(BR_STATES_URL).then(r => r.json())
    .then(g => (map.getSource('states') as maplibregl.GeoJSONSource).setData(g))
    .catch(() => {})

  // Círculo de raio (abaixo de tudo; não-interativo)
  map.addSource('radius', { type: 'geojson', data: EMPTY_FC })
  map.addLayer({ id: 'radius-fill', type: 'fill', source: 'radius', paint: { 'fill-color': '#3b82f6', 'fill-opacity': 0.07 } })
  map.addLayer({ id: 'radius-line', type: 'line', source: 'radius', paint: { 'line-color': '#2563eb', 'line-width': 1.5 } })

  // Bolhas de prefixos (abaixo das sedes)
  map.addSource('bubbles', { type: 'geojson', data: EMPTY_FC })
  map.addLayer({
    id: 'bubbles', type: 'circle', source: 'bubbles',
    paint: {
      'circle-radius': bubbleRadiusExpr,
      'circle-color': bubbleColorExpr,
      'circle-opacity': 0.7,
      'circle-stroke-width': 1,
      'circle-stroke-color': bubbleColorExpr,
    },
  })

  // Sedes de AS — cor mais clara quando há outorga SCM correspondente.
  // radius=8 quando múltiplos ASes agregados na mesma coordenada.
  map.addSource('asns', { type: 'geojson', data: EMPTY_FC })
  map.addLayer({
    id: 'asns', type: 'circle', source: 'asns',
    paint: {
      'circle-radius': ['get', 'radius'],
      'circle-color': ['get', 'color'],
      'circle-opacity': 0.95,
      'circle-stroke-width': 2,
      'circle-stroke-color': '#ffffff',
    },
  })

  // PIX (PTTs físicos) — por cima
  map.addSource('pix', { type: 'geojson', data: EMPTY_FC })
  map.addLayer({
    id: 'pix', type: 'circle', source: 'pix',
    paint: {
      'circle-radius': 6,
      'circle-color': '#fbbf24',
      'circle-opacity': 0.9,
      'circle-stroke-width': 1.5,
      'circle-stroke-color': '#92400e',
    },
  })

  // SCMs Anatel — mesma aparência da sede quando tem AS, roxo quando não tem.
  // radius=8 quando múltiplos SCMs agregados na mesma coordenada.
  map.addSource('scms-loc', { type: 'geojson', data: EMPTY_FC })
  map.addLayer({
    id: 'scms-loc', type: 'circle', source: 'scms-loc',
    paint: {
      'circle-radius': ['get', 'radius'],
      'circle-color': ['get', 'color'],
      'circle-opacity': 0.85,
      'circle-stroke-width': ['get', 'strokeWidth'],
      'circle-stroke-color': '#ffffff',
    },
  })

  // Usuários declarados ao SICI, por município — vermelho, ponto no centróide do IBGE (mesmo formato/raio das outras camadas).
  map.addSource('sici-mun', { type: 'geojson', data: EMPTY_FC })
  map.addLayer({
    id: 'sici-mun', type: 'circle', source: 'sici-mun',
    paint: {
      'circle-radius': ['get', 'radius'],
      'circle-color': SICI_COLOR,
      'circle-opacity': 0.85,
      'circle-stroke-width': 2,
      'circle-stroke-color': '#ffffff',
    },
  })
}

const CAMADAS_INTERATIVAS = ['bubbles', 'asns', 'pix', 'scms-loc', 'sici-mun']

/** Balão que segue o cursor (HTML pronto em `properties.tip`), modal em clique de agregados e clique no mapa vazio para mover o ponto. */
export function ligarInteracoes(map: maplibregl.Map, cb: {
  abrirModal: (m: { title: string; html: string }) => void
  moverPonto: (p: Ponto) => void
}): void {
  const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, maxWidth: '240px' })
  const onEnter = (e: Evento) => {
    const f = e.features?.[0]; if (!f) return
    map.getCanvas().style.cursor = 'pointer'
    const tip = (f.properties as Record<string, unknown>)?.tip as string ?? ''
    popup.setLngLat(e.lngLat).setHTML(tip).addTo(map)
  }
  const onMove = (e: maplibregl.MapMouseEvent) => popup.setLngLat(e.lngLat)
  const onLeave = () => { map.getCanvas().style.cursor = ''; popup.remove() }
  for (const id of CAMADAS_INTERATIVAS) {
    map.on('mouseenter', id, onEnter)
    map.on('mousemove', id, onMove)
    map.on('mouseleave', id, onLeave)
  }

  // Clique em feature com múltiplas entidades → abre modal com lista completa.
  const onFeatureClick = (e: Evento) => {
    const f = e.features?.[0]; if (!f) return
    const props = f.properties as Record<string, unknown>
    const entityCount = (props.entityCount as number) ?? 1
    if (entityCount > 1) {
      cb.abrirModal({ title: (props.modalTitle as string) ?? '', html: (props.modalHtml as string) ?? '' })
    }
  }
  for (const id of ['bubbles', 'asns', 'scms-loc', 'sici-mun']) map.on('click', id, onFeatureClick)

  // Clique em mapa vazio → move o ponto central de busca.
  map.on('click', (e) => {
    const hit = map.queryRenderedFeatures(e.point, { layers: CAMADAS_INTERATIVAS })
    if (hit.length === 0) cb.moverPonto([e.lngLat.lat, e.lngLat.lng])
  })
}

/**
 * Ciclo de vida do mapa do Localizador: cria o MapLibre uma vez, mantém o pino arrastável e o círculo do raio, e escreve as feições
 * de cada camada quando os dados calculados mudam. Os cálculos ficam em `calculos.ts`; o HTML dos balões em `balloes.ts`.
 */
export function useMapaLocalizador(p: {
  markerPos: Ponto | null
  radius: number
  setMarkerPos: (p: Ponto) => void
  abrirModal: (m: { title: string; html: string }) => void
  show: { asns: boolean; prefixes: boolean; scms: boolean; sici: boolean }
  asnDots: AsnDot[]
  prefixBubbles: Bubble[]
  pixDots: Array<{ lat: number; lon: number; name: string; ixpName: string }>
  coordGroups: Map<string, GrupoCoord>
  scmsInRadius: ScmGeoFeature[]
  siciMunInRadius: MunicipioSici[]
  asnToCnpj: Map<number, string>
  asnNameMap: Map<number, InfoAsn>
}) {
  const { markerPos, radius, show } = p
  const mapDivRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const markerRef = useRef<maplibregl.Marker | null>(null)
  const radiusRef = useRef(radius)
  const cbRef = useRef({ setMarkerPos: p.setMarkerPos, abrirModal: p.abrirModal })
  cbRef.current = { setMarkerPos: p.setMarkerPos, abrirModal: p.abrirModal }
  const [mapReady, setMapReady] = useState(false)

  useEffect(() => {
    if (!mapDivRef.current || mapRef.current) return
    const map = new maplibregl.Map({
      container: mapDivRef.current,
      style: MAP_STYLE,
      center: MAP_DEFAULT_CENTER,
      zoom: MAP_DEFAULT_ZOOM,
      bearing: bearingInicial(),
      attributionControl: false,
    })
    // Exceção proposital: NavigationControl fica em bottom-left aqui (não top-right como nos outros mapas) porque o painel de
    // entidades ocupa top-right em altura cheia — colocar em top-right sobreporia os dois.
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-left')
    map.addControl(new BearingToggleControl(), 'bottom-left')
    map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: DBIP_ATRIBUICAO_HTML }), 'bottom-right')   // camada de prefixos: DB-IP

    map.on('load', () => {
      adicionarCamadas(map)
      ligarInteracoes(map, { abrirModal: m => cbRef.current.abrirModal(m), moverPonto: pt => cbRef.current.setMarkerPos(pt) })
      setMapReady(true)
    })

    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
      markerRef.current = null
    }
  }, [])

  const setRadiusCircle = useCallback((lat: number, lon: number, km: number) => {
    const src = mapRef.current?.getSource('radius') as maplibregl.GeoJSONSource | undefined
    src?.setData(circlePolygon(lat, lon, km))
  }, [])

  // marker + circle
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady) return

    if (!markerPos) {
      markerRef.current?.remove(); markerRef.current = null
      ;(map.getSource('radius') as maplibregl.GeoJSONSource | undefined)?.setData(EMPTY_FC)
      return
    }

    const [lat, lon] = markerPos

    if (!markerRef.current) {
      const m = new maplibregl.Marker({ element: makePinElement(), draggable: true })
        .setLngLat([lon, lat])
        .addTo(map)
      m.on('drag', () => {
        const pt = m.getLngLat()
        setRadiusCircle(pt.lat, pt.lng, radiusRef.current)
      })
      m.on('dragend', () => {
        const pt = m.getLngLat()
        cbRef.current.setMarkerPos([pt.lat, pt.lng])
      })
      markerRef.current = m
    } else {
      markerRef.current.setLngLat([lon, lat])
    }

    setRadiusCircle(lat, lon, radius)
  }, [markerPos, mapReady]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    radiusRef.current = radius
    if (markerPos) setRadiusCircle(markerPos[0], markerPos[1], radius)
  }, [radius, markerPos, setRadiusCircle])

  // bolhas, sedes de AS e PIX
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady) return
    const set = (id: string, features: GeoJSON.Feature[]) =>
      (map.getSource(id) as maplibregl.GeoJSONSource | undefined)?.setData({ type: 'FeatureCollection', features })
    set('bubbles', show.prefixes ? featuresBolhas(p.prefixBubbles, p.asnNameMap, p.asnToCnpj) : [])
    set('asns', show.asns ? featuresSedes(p.asnDots, show.scms, p.coordGroups, p.asnToCnpj) : [])
    set('pix', featuresPix(p.pixDots))
  }, [p.asnDots, p.prefixBubbles, p.pixDots, show.asns, show.prefixes, show.scms, p.asnToCnpj, p.asnNameMap, p.coordGroups, mapReady]) // eslint-disable-line react-hooks/exhaustive-deps

  // SCMs
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady) return
    const src = map.getSource('scms-loc') as maplibregl.GeoJSONSource | undefined
    if (!src) return
    if (!show.scms || !markerPos || p.scmsInRadius.length === 0) {
      src.setData(EMPTY_FC)
      map.setLayoutProperty('scms-loc', 'visibility', 'none')
      return
    }
    src.setData({ type: 'FeatureCollection', features: featuresScm(p.coordGroups, p.asnToCnpj, p.asnNameMap) })
    map.setLayoutProperty('scms-loc', 'visibility', 'visible')
  }, [p.scmsInRadius, show.scms, show.asns, p.asnDots, p.coordGroups, p.asnToCnpj, mapReady, markerPos, p.asnNameMap]) // eslint-disable-line react-hooks/exhaustive-deps

  // SICI
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady) return
    const src = map.getSource('sici-mun') as maplibregl.GeoJSONSource | undefined
    if (!src) return
    if (!show.sici || p.siciMunInRadius.length === 0) { src.setData(EMPTY_FC); return }
    src.setData({ type: 'FeatureCollection', features: featuresSici(p.siciMunInRadius) })
  }, [p.siciMunInRadius, show.sici, mapReady]) // eslint-disable-line react-hooks/exhaustive-deps

  return { mapDivRef, mapRef }
}
