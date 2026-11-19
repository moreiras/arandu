// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import * as maplibregl from 'maplibre-gl'
import {
  htmlAsn, htmlErbs, htmlCaboSubmarino, htmlEnlaceTerrestre, htmlLinhaTransmissao, htmlPix, htmlPontoAterrissagem, htmlPrefixo, htmlRodovia, htmlScm,
} from './popups'
import type { LayerId } from './tipos'

type MapFeatureEvent = maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }

/** O que as interações leem do componente sem recriar o mapa: refs lidas na hora do evento (hover não dispara estado do React). */
export interface ContextoInteracoes {
  navegar: (to: string) => void
  camadasLigadas: () => Record<LayerId, boolean>
  colorBy: () => string
}

/**
 * Balões ao passar o mouse e cliques das camadas do mapa "Explorar".
 * Cada camada tem um par (id da camada MapLibre → função que monta o HTML); o resto é igual para todas.
 */
export function ligarInteracoes(map: maplibregl.Map, ctx: ContextoInteracoes): void {
  const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, maxWidth: '240px' })

  const mostrar = (html: (p: Record<string, unknown>) => string, cursor = 'pointer', quando?: () => boolean) => (e: MapFeatureEvent) => {
    if (quando && !quando()) return
    const f = e.features?.[0]
    if (!f) return
    map.getCanvas().style.cursor = cursor
    popup.setLngLat(e.lngLat).setHTML(html(f.properties as Record<string, unknown>)).addTo(map)
  }
  const esconder = () => { map.getCanvas().style.cursor = ''; popup.remove() }
  const hover = (layer: string, show: (e: MapFeatureEvent) => void, move = false) => {
    map.on('mouseenter', layer, show)
    if (move) map.on('mousemove', layer, show)
    map.on('mouseleave', layer, esconder)
  }

  hover('explorer-scms',       mostrar(htmlScm))
  hover('explorer-pix',        mostrar(htmlPix))
  hover('explorer-asns',       mostrar(p => htmlAsn(p, ctx.colorBy())))
  hover('explorer-pref-v4',    mostrar(htmlPrefixo, 'crosshair'))
  hover('explorer-pref-v6',    mostrar(htmlPrefixo, 'crosshair'))
  hover('explorer-pref-ix-v4', mostrar(htmlPrefixo, 'crosshair'))
  hover('explorer-pref-ix-v6', mostrar(htmlPrefixo, 'crosshair'))

  // Infra física do estilo base (ITU + TeleGeography + ANEEL) — balão só quando a camada está ligada.
  hover('infra-terrestrial-links',        mostrar(htmlEnlaceTerrestre, 'pointer', () => ctx.camadasLigadas().terrestrial), true)
  hover('infra-submarine-cables',         mostrar(htmlCaboSubmarino, 'pointer', () => ctx.camadasLigadas().submarine), true)
  hover('infra-submarine-landing-points', mostrar(htmlPontoAterrissagem, 'pointer', () => ctx.camadasLigadas().submarine), true)
  hover('infra-power-lines',              mostrar(htmlLinhaTransmissao, 'pointer', () => ctx.camadasLigadas().power), true)
  hover('explorer-erbs',                  mostrar(htmlErbs), true)
  hover('explorer-roads-federal',         mostrar(htmlRodovia), true)
  hover('explorer-roads-estadual',        mostrar(htmlRodovia), true)

  const ir = (layer: string, campo: string, rota: (v: unknown) => string) =>
    map.on('click', layer, (e: MapFeatureEvent) => {
      const v = (e.features?.[0]?.properties as Record<string, unknown>)?.[campo]
      if (v != null && v !== '') ctx.navegar(rota(v))
    })
  ir('explorer-asns', 'asn', v => `/asn/${v}`)
  ir('explorer-scms', 'cnpj', v => `/operadora/${v}`)
  ir('explorer-pix', 'ixp_code', v => `/ixp/${v}`)
}
