// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { cru, html, htmlSeguro } from '../../lib/html'
import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import {
  MAP_COLORS, STATE_OUTLINE_PAINT, MAP_DEFAULT_CENTER, MAP_DEFAULT_ZOOM, bearingInicial, createBaseMapStyle, addStandardControls,
  MARKER_RADIUS_EXPR, MARKER_OPACITY,
} from '../../components/maps/mapTheme'
import type { Servico } from './servicos'
import { fmtCnpj } from './formato'

const BR_STATES_URL = '/br-states.geojson'
const EMPTY_FC: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] }

function sedePopupHtml(p: Record<string, unknown>): string {
  const cnpj = String(p.cnpj ?? '')
  const asns: number[] = typeof p.asns === 'string' ? JSON.parse(p.asns) : (p.asns as number[] ?? [])
  // tudo o que vem do dado passa pela tag `html` (escapa); os trechos montados aqui entram como `htmlSeguro`.
  const asnsLine = asns.length > 0
    ? htmlSeguro`<div class="mt-1">AS: ${cru(asns.map(a => html`<a href="/asn/${a}" class="text-primario-600 hover:underline">${a}</a>`).join(', '))}</div>`
    : ''
  return html`
    <div class="text-xs leading-relaxed">
      <div class="font-semibold text-sm mb-1">
        <a href="/operadora/${cnpj}" class="hover:underline">${p.razao_social ?? ''}</a>
      </div>
      ${p.nome_fantasia ? htmlSeguro`<div class="text-gray-500">${p.nome_fantasia}</div>` : ''}
      <div class="text-gray-400 font-mono">
        <a href="/operadora/${cnpj}" class="hover:underline">${fmtCnpj(cnpj)}</a>
      </div>
      <div>${p.municipio ?? ''}/${p.uf ?? ''}</div>
      ${asnsLine}
    </div>`
}

/** Ponto na sede de cada outorga do serviço, cor por has_asn. Um só componente para SCM, SMP, STFC e SeAC (a rota e o rótulo vêm do serviço). */
export function MapaSede({ servico, date, uf, comAsn, moldura }: { servico: Servico; date?: string; uf?: string; comAsn: boolean; moldura?: boolean }) {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstance = useRef<maplibregl.Map | null>(null)

  const FONTE = `${servico.id}s`
  const CAMADA = `${servico.id}s-point`

  const { data: geo } = useQuery({
    queryKey: [`${servico.id}-map`, date, uf, comAsn],
    queryFn: () => servico.mapa!({ date, uf: uf || undefined, com_asn: comAsn }),
    staleTime: 5 * 60 * 1000,
  })

  useEffect(() => {
    if (!mapRef.current || mapInstance.current) return
    mapInstance.current = new maplibregl.Map({
      container: mapRef.current,
      style: createBaseMapStyle(),
      center: MAP_DEFAULT_CENTER,
      zoom: MAP_DEFAULT_ZOOM,
      bearing: bearingInicial(),
      attributionControl: false,
    })
    addStandardControls(mapInstance.current)

    // O MapLibre mede o container na construção, e o layout às vezes ainda
    // não assentou nesse instante (canvas nasce com poucos pixels de altura).
    // Reobserva o tamanho do container e força um resize quando ele muda.
    const map = mapInstance.current
    const observer = new ResizeObserver(() => map.resize())
    observer.observe(mapRef.current)

    return () => { observer.disconnect(); map.remove(); mapInstance.current = null }
  }, [])

  useEffect(() => {
    const map = mapInstance.current
    if (!map || !geo) return

    const addLayer = () => {
      if (map.getSource(FONTE)) {
        (map.getSource(FONTE) as maplibregl.GeoJSONSource).setData(geo as never)
      } else {
        // Bordas estaduais (mesmo padrão dos outros mapas)
        map.addSource('states', { type: 'geojson', data: EMPTY_FC })
        map.addLayer({
          id: 'states-outline', type: 'line', source: 'states',
          paint: STATE_OUTLINE_PAINT,
        })
        fetch(BR_STATES_URL).then(r => r.json())
          .then(g => (map.getSource('states') as maplibregl.GeoJSONSource).setData(g))
          .catch(() => {})

        map.addSource(FONTE, { type: 'geojson', data: geo as never })
        map.addLayer({
          id: CAMADA,
          type: 'circle',
          source: FONTE,
          paint: {
            'circle-color': ['case', ['get', 'has_asn'], MAP_COLORS.scmWithAsn, MAP_COLORS.scmWithoutAsn],
            'circle-radius': MARKER_RADIUS_EXPR,
            'circle-stroke-width': 0,
            'circle-opacity': MARKER_OPACITY,
          },
        })

        map.on('click', CAMADA, (e) => {
          const f = e.features?.[0]
          if (!f) return
          const p = f.properties as Record<string, unknown>
          new maplibregl.Popup({ closeButton: false, maxWidth: '260px' })
            .setLngLat(e.lngLat)
            .setHTML(sedePopupHtml(p))
            .addTo(map)
        })
        map.on('mouseenter', CAMADA, () => { map.getCanvas().style.cursor = 'pointer' })
        map.on('mouseleave', CAMADA, () => { map.getCanvas().style.cursor = '' })
      }
    }

    if (map.isStyleLoaded()) addLayer()
    else map.once('load', addLayer)
  }, [geo])

  const conteudo = (
    <>
      {/* A alternativa em texto é a lista de outorgas da página, com os mesmos filtros (UF, com AS) */}
      <div ref={mapRef} className="w-full h-full" role="group" aria-label={`Mapa das sedes das outorgadas ${servico.rotulo}, com e sem AS; a lista da página traz as mesmas empresas`} />
      <div className="absolute bottom-8 right-3 flex gap-2 text-xs bg-white/90 backdrop-blur px-3 py-2 rounded shadow-sm border border-gray-200">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full inline-block" style={{ background: MAP_COLORS.scmWithoutAsn }} aria-hidden="true" /> {servico.rotulo} sem AS
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full inline-block" style={{ background: MAP_COLORS.scmWithAsn }} aria-hidden="true" /> {servico.rotulo} com AS
        </span>
      </div>
    </>
  )
  // SCM e SMP trazem o mapa dentro das abas (a moldura é delas); STFC e SeAC têm só este mapa, com moldura própria
  return moldura
    ? <div className="relative rounded-lg border border-gray-200 overflow-hidden" style={{ height: 420 }}>{conteudo}</div>
    : conteudo
}
