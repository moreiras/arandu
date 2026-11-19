// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useEffect, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useNavigate } from 'react-router-dom'
import type { MapQueryBody } from '../../../services/api'
import { bearingInicial, addStandardControls, createBaseMapStyle } from '../mapTheme'
import { adicionarCamadas } from './camadasMapa'
import { circlePolygon } from './geo'
import { colorExpr } from './estilo'
import { ligarInteracoes } from './interacoes'
import type { LayerStatus } from './PainelCamadas'
import {
  BRAZIL_CENTER, BRAZIL_ZOOM, EMPTY_FC, FETCH_ORDER, MAPLIBRE_LAYERS, PANEL_WIDTH, STALE_FACTOR,
} from './tipos'
import type { DataLayerId, LayerId, MapState } from './tipos'

const MAP_STYLE: maplibregl.StyleSpecification = createBaseMapStyle()

/**
 * Ciclo de vida do mapa "Explorar": cria o MapLibre uma vez, adiciona fontes/camadas/interações ao carregar o estilo e mantém
 * (por efeitos separados) dados, visibilidade, opacidade, infra do estilo base e o círculo de proximidade em sincronia com o estado.
 * O mapa nunca é recriado por mudança de estado (AGENTS.md: mapas não re-renderizam por hover/estado).
 */
export function useMapaExplorer(p: {
  state: MapState
  statuses: Record<LayerId, LayerStatus>
  resultById: Record<DataLayerId, { data?: unknown; isPlaceholderData?: boolean } | undefined>
  /** Corpo da consulta que gerou os dados das sedes de AS (para o `color_by` dos dados, não o do estado atual). */
  corpoSedes: () => MapQueryBody | undefined
  selectedIx: string | null
  panelOpen: boolean
}) {
  const { state, statuses, resultById, selectedIx, panelOpen } = p
  const navigate = useNavigate()
  const [ready, setReady] = useState(false)
  const [mapError, setMapError] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef       = useRef<maplibregl.Map | null>(null)
  const navigateRef  = useRef(navigate)
  const colorByRef   = useRef(state.colorBy)
  const onRef        = useRef(state.on)
  const lastDataRef  = useRef<Partial<Record<DataLayerId, unknown>>>({})
  const corpoSedesRef = useRef(p.corpoSedes)
  corpoSedesRef.current = p.corpoSedes

  useEffect(() => { navigateRef.current = navigate }, [navigate])
  useEffect(() => { onRef.current = state.on }, [state.on])

  // Init map once
  useEffect(() => {
    const el = containerRef.current
    if (!el || mapRef.current) return

    let map: maplibregl.Map
    try {
      map = new maplibregl.Map({
        container: el,
        style: MAP_STYLE,
        center: BRAZIL_CENTER,
        zoom: BRAZIL_ZOOM,
        bearing: bearingInicial(),
        attributionControl: false,
      })
      map.setPadding({ top: 0, right: 0, bottom: 0, left: panelOpen ? PANEL_WIDTH : 0 })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Falha ao inicializar o mapa'
      console.error('ExplorerMap init failed', err)
      setMapError(message)
      return
    }

    addStandardControls(map, { dbip: true })

    const initLayers = () => {
      if (!map.isStyleLoaded()) return
      if (map.getSource('src-pix')) { setReady(true); return }
      adicionarCamadas(map)
      ligarInteracoes(map, {
        navegar: to => navigateRef.current(to),
        camadasLigadas: () => onRef.current,
        colorBy: () => colorByRef.current,
      })
      lastDataRef.current = {}
      setReady(true)
    }

    map.on('load', initLayers)
    map.on('styledata', initLayers)
    map.on('error', e => {
      const message =
        (e.error instanceof Error && e.error.message)
        || (typeof e.error === 'string' ? e.error : 'Erro interno do MapLibre')
      console.error('ExplorerMap runtime error', e.error ?? e)
      setMapError(message)
    })
    initLayers()

    let frame1 = 0
    let frame2 = 0
    const resizeMap = () => { try { map.resize() } catch {} }
    frame1 = window.requestAnimationFrame(() => {
      resizeMap()
      frame2 = window.requestAnimationFrame(resizeMap)
    })

    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(() => resizeMap()) : null
    ro?.observe(el)

    mapRef.current = map
    return () => {
      if (frame1) window.cancelAnimationFrame(frame1)
      if (frame2) window.cancelAnimationFrame(frame2)
      ro?.disconnect()
      map.remove()
      mapRef.current = null
      setReady(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Dados → sources: cada camada é desenhada assim que a sua consulta chega.
  const resultados = FETCH_ORDER.map(id => resultById[id])
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    for (const id of FETCH_ORDER) {
      const r = resultById[id]
      const data = r?.data
      if (!data || lastDataRef.current[id] === data) continue
      lastDataRef.current[id] = data
      ;(map.getSource(`src-${id}`) as maplibregl.GeoJSONSource | undefined)?.setData(data as GeoJSON.FeatureCollection)
      if (id === 'asns_geo' && !r.isPlaceholderData) {
        // color_by da consulta que gerou estes dados (não o do estado atual)
        const colorBy = corpoSedesRef.current()?.color_by ?? 'solid'
        colorByRef.current = colorBy
        map.setPaintProperty('explorer-asns', 'circle-color', colorExpr(colorBy))
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...resultados.map(r => r?.data), ...resultados.map(r => r?.isPlaceholderData), ready])

  // Visibilidade + opacidade (dados antigos esmaecidos enquanto os novos chegam)
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    for (const ml of MAPLIBRE_LAYERS) {
      if (!map.getLayer(ml.id)) continue
      const on = state.on[ml.data]
      map.setLayoutProperty(ml.id, 'visibility', on ? 'visible' : 'none')
      const stale = statuses[ml.data]?.stale
      map.setPaintProperty(ml.id, ml.opacityProp, stale ? ml.opacity * STALE_FACTOR : ml.opacity)
    }
    // PIX: só os do PTT selecionado, se pedido
    if (map.getLayer('explorer-pix')) {
      map.setFilter('explorer-pix', state.pixOnlySelected && selectedIx
        ? ['==', ['get', 'ixp_code'], selectedIx]
        : null)
    }
  }, [state.on, state.pixOnlySelected, selectedIx, statuses, ready])

  // Infra física do estilo base: em /mapa fica oculta por padrão (diferente dos
  // outros mapas, que a mostram como fundo); ligada, destacada + interativa.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const { submarine, terrestrial, power } = state.on
    if (map.getLayer('infra-terrestrial-links')) {
      map.setLayoutProperty('infra-terrestrial-links', 'visibility', terrestrial ? 'visible' : 'none')
      map.setPaintProperty('infra-terrestrial-links', 'line-width', 1.5)
      map.setPaintProperty('infra-terrestrial-links', 'line-opacity', 0.85)
    }
    if (map.getLayer('infra-submarine-cables')) {
      map.setLayoutProperty('infra-submarine-cables', 'visibility', submarine ? 'visible' : 'none')
      map.setPaintProperty('infra-submarine-cables', 'line-width', 2.2)
    }
    if (map.getLayer('infra-submarine-landing-points')) {
      map.setLayoutProperty('infra-submarine-landing-points', 'visibility', submarine ? 'visible' : 'none')
      map.setPaintProperty('infra-submarine-landing-points', 'circle-radius', 4)
    }
    if (map.getLayer('infra-power-lines')) {
      map.setLayoutProperty('infra-power-lines', 'visibility', power ? 'visible' : 'none')
      map.setPaintProperty('infra-power-lines', 'line-width', 1.2)
      map.setPaintProperty('infra-power-lines', 'line-opacity', 0.85)
    }
  }, [state.on, ready])

  // Círculo do raio de proximidade em volta de cada PIX do PTT escolhido
  const pixData = resultById.pix?.data as GeoJSON.FeatureCollection | undefined
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const src = map.getSource('recorte-radius') as maplibregl.GeoJSONSource | undefined
    if (!src) return
    const code = state.nearIxp.trim().toLowerCase()
    if (!code || !pixData || !(state.nearRadiusKm > 0)) { src.setData(EMPTY_FC); return }
    const features = pixData.features
      .filter(f => (f.properties as Record<string, unknown>)?.ixp_code === code && f.geometry.type === 'Point')
      .map(f => {
        const [lon, lat] = (f.geometry as GeoJSON.Point).coordinates
        return circlePolygon(lon, lat, state.nearRadiusKm)
      })
    src.setData({ type: 'FeatureCollection', features })
  }, [state.nearIxp, state.nearRadiusKm, pixData, ready])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    map.resize()
    map.easeTo({ padding: { top: 0, right: 0, bottom: 0, left: panelOpen ? PANEL_WIDTH : 0 }, duration: 300 })
  }, [panelOpen])

  return { containerRef, mapError }
}
