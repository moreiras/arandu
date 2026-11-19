// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Fontes e camadas do mapa "Explorar" (executa uma vez por estilo carregado; `camadasMapa.test.ts` verifica ids e ordem). */
import * as maplibregl from 'maplibre-gl'
import { MAP_COLORS, STATE_OUTLINE_PAINT } from '../mapTheme'
import { colorExpr } from './estilo'
import {
  BR_STATES_URL, COLOR_PIX, COLOR_PIX_STROKE, COLOR_PREF_V4_BR, COLOR_PREF_V4_PTT, COLOR_PREF_V6_BR, COLOR_PREF_V6_PTT, COLOR_SCM,
  COLOR_SCM_STROKE, COLOR_SCM_WITH_ASN, EMPTY_FC, FETCH_ORDER, INITIAL,
} from './tipos'

export function adicionarCamadas(map: maplibregl.Map): void {
  // State borders
  map.addSource('states', { type: 'geojson', data: EMPTY_FC })
  map.addLayer({
    id: 'states-outline', type: 'line', source: 'states',
    paint: STATE_OUTLINE_PAINT,
  })
  fetch(BR_STATES_URL).then(r => r.json())
    .then(g => (map.getSource('states') as maplibregl.GeoJSONSource).setData(g))
    .catch(() => {})

  // Uma source por camada de dados — cada consulta preenche a sua ao chegar.
  for (const id of FETCH_ORDER) {
    map.addSource(`src-${id}`, { type: 'geojson', data: EMPTY_FC })
  }

  // Círculo do raio de proximidade (abaixo das camadas de dados)
  map.addSource('recorte-radius', { type: 'geojson', data: EMPTY_FC })
  map.addLayer({
    id: 'recorte-radius-fill', type: 'fill', source: 'recorte-radius',
    paint: { 'fill-color': '#3b82f6', 'fill-opacity': 0.05 },
  })
  map.addLayer({
    id: 'recorte-radius-line', type: 'line', source: 'recorte-radius',
    paint: { 'line-color': '#3b82f6', 'line-width': 1.2, 'line-dasharray': [3, 2], 'line-opacity': 0.7 },
  })

  const hidden = { visibility: 'none' as const }
  const roadLayout = { 'line-join': 'round' as const, 'line-cap': 'round' as const, visibility: 'none' as const }

  // Antenas do SMP licenciadas: células de ~2 km, raio pelo número de estações (cadastro, não cobertura)
  map.addLayer({
    id: 'explorer-erbs', type: 'circle', source: 'src-erbs', layout: hidden,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, ['step', ['get', 'n'], 1.5, 5, 2.5, 20, 4], 9, ['step', ['get', 'n'], 3, 5, 5, 20, 8], 12, ['step', ['get', 'n'], 5, 5, 8, 20, 12]],
      'circle-color': MAP_COLORS.erbs,
      'circle-opacity': 0.55,
      'circle-stroke-width': 0,
    },
  })
  map.addLayer({
    id: 'explorer-roads-estadual', type: 'line', source: 'src-roads_estadual', layout: roadLayout,
    paint: { 'line-color': MAP_COLORS.roadState, 'line-width': 0.9, 'line-opacity': 0.75 },
  })
  map.addLayer({
    id: 'explorer-roads-federal', type: 'line', source: 'src-roads_federal', layout: roadLayout,
    paint: { 'line-color': MAP_COLORS.road, 'line-width': 1.6, 'line-opacity': 0.85 },
  })

  // Prefixos BR geolocalizados IPv4 / IPv6
  map.addLayer({
    id: 'explorer-pref-v4', type: 'circle', source: 'src-prefixes_v4', layout: hidden,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 2, 7, 4, 12, 7],
      'circle-color': COLOR_PREF_V4_BR,
      'circle-opacity': 0.6,
      'circle-stroke-width': 0,
    },
  })
  map.addLayer({
    id: 'explorer-pref-v6', type: 'circle', source: 'src-prefixes_v6', layout: hidden,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 2, 7, 4, 12, 7],
      'circle-color': COLOR_PREF_V6_BR,
      'circle-opacity': 0.6,
      'circle-stroke-width': 0,
    },
  })

  // Prefixos PTT IPv4 (violeta claro) / IPv6 (vermelho)
  map.addLayer({
    id: 'explorer-pref-ix-v4', type: 'circle', source: 'src-prefixos_ix_v4', layout: hidden,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 3, 7, 5, 12, 8],
      'circle-color': COLOR_PREF_V4_PTT,
      'circle-opacity': 0.7,
      'circle-stroke-width': 0,
    },
  })
  map.addLayer({
    id: 'explorer-pref-ix-v6', type: 'circle', source: 'src-prefixos_ix_v6', layout: hidden,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 3, 7, 5, 12, 8],
      'circle-color': COLOR_PREF_V6_PTT,
      'circle-opacity': 0.7,
      'circle-stroke-width': 0,
    },
  })

  // Outorgas SCM — cinza com ASN, roxo sem ASN (igual ao Localizador)
  map.addLayer({
    id: 'explorer-scms', type: 'circle', source: 'src-outorgas_scm', layout: hidden,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 2.5, 7, 4.5, 12, 8],
      'circle-color': ['case', ['get', 'has_asn'], COLOR_SCM_WITH_ASN, COLOR_SCM],
      'circle-opacity': 0.65,
      'circle-stroke-width': 0.5,
      'circle-stroke-color': COLOR_SCM_STROKE,
    },
  })

  // Sedes de AS (colored by color_value)
  map.addLayer({
    id: 'explorer-asns', type: 'circle', source: 'src-asns_geo', layout: hidden,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 3, 7, 5, 12, 9],
      'circle-color': colorExpr(INITIAL.colorBy),
      'circle-opacity': 0.8,
      'circle-stroke-width': 0,
    },
  })

  // PIX — por cima de tudo, para não sumir sob as nuvens de prefixos
  map.addLayer({
    id: 'explorer-pix', type: 'circle', source: 'src-pix', layout: hidden,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 5, 7, 8, 12, 12],
      'circle-color': COLOR_PIX,
      'circle-opacity': 0.9,
      'circle-stroke-width': 1.5,
      'circle-stroke-color': COLOR_PIX_STROKE,
    },
  })
}
