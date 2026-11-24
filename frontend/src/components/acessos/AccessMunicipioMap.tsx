import { html, htmlSeguro } from '../../lib/html'
import { useEffect, useMemo, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import {
  MAP_COLORS,
  STATE_OUTLINE_PAINT,
  MAP_DEFAULT_CENTER,
  MAP_DEFAULT_ZOOM,
  bearingInicial,
  createBaseMapStyle,
  addStandardControls,
  MARKER_RADIUS_EXPR,
  MARKER_OPACITY,
} from '../maps/mapTheme'
import { VerDados } from '../ui/VerDados'

const BR_STATES_URL = '/br-states.geojson'
const CENTROIDS_URL = '/municipios-centroides.json'
/** Linhas da tabela alternativa: o bastante para os maiores sem pôr milhares de linhas no DOM de cada perfil. */
const MAX_TABELA = 500

/** Shape mínima usada pelo mapa — SiciMunicipioRow e MovelMunicipioRow (fixa/móvel)
 *  satisfazem ambas estruturalmente, sem precisar de conversão no chamador. */
export interface AccessMunicipioMapRow {
  ibge: string
  nome: string
  uf: string
  acessos: number
  pf: number
  pj: number
  share?: number | null
  municipio_acessos?: number | null
}

/**
 * Distribuição municipal dos acessos como bolhas proporcionais em centróides.
 *
 * Deliberadamente não é um coroplético: pintar os 5.570 polígonos exigiria a malha
 * inteira do IBGE (dezenas de MB) e ainda daria peso visual à área do município —
 * o Amazonas dominaria o mapa com pouquíssimos acessos. O raio da bolha representa
 * o número de acessos diretamente.
 */
export function AccessMunicipioMap({
  municipios,
  height = 380,
  onMunicipioClick,
}: {
  municipios: AccessMunicipioMapRow[]
  height?: number
  /** Quando fornecido, bolhas viram clicáveis (cursor de ponteiro) e chamam
   *  este callback com o código IBGE do município clicado. */
  onMunicipioClick?: (ibge: string) => void
}) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const [centroids, setCentroids] = useState<Record<string, [number, number]> | null>(null)
  const onClickRef = useRef(onMunicipioClick)
  onClickRef.current = onMunicipioClick

  useEffect(() => {
    let alive = true
    fetch(CENTROIDS_URL)
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (alive) setCentroids(d) })
      .catch(() => { if (alive) setCentroids(null) })
    return () => { alive = false }
  }, [])

  const fc = useMemo<GeoJSON.FeatureCollection>(() => {
    if (!centroids) return { type: 'FeatureCollection', features: [] }
    return {
      type: 'FeatureCollection',
      features: municipios.flatMap(m => {
        const c = centroids[m.ibge]
        if (!c) return []
        return [{
          type: 'Feature' as const,
          geometry: { type: 'Point' as const, coordinates: c },
          properties: {
            ibge: m.ibge, nome: m.nome, uf: m.uf, acessos: m.acessos,
            pf: m.pf, pj: m.pj,
            share: m.share ?? null,
            municipio_acessos: m.municipio_acessos ?? null,
          },
        }]
      }),
    }
  }, [municipios, centroids])

  const maxAcessos = useMemo(
    () => municipios.reduce((mx, m) => Math.max(mx, m.acessos), 0) || 1,
    [municipios],
  )

  useEffect(() => {
    if (!container.current || map.current) return
    map.current = new maplibregl.Map({
      container: container.current,
      style: createBaseMapStyle(),
      center: MAP_DEFAULT_CENTER,
      zoom: MAP_DEFAULT_ZOOM,
      bearing: bearingInicial(),
      attributionControl: false,
    })
    addStandardControls(map.current)

    // O container costuma medir poucos pixels no instante da construção (o layout
    // ainda não assentou); reobserva e força o resize, como nos demais mapas.
    const ro = new ResizeObserver(() => map.current?.resize())
    ro.observe(container.current)

    map.current.on('load', () => {
      const m = map.current
      if (!m) return

      // 'mun' precisa existir de forma síncrona neste handler: o outro efeito
      // decide se aplica os dados na hora (isStyleLoaded() já true) ou só no
      // próximo 'load' — se essa fonte só aparecesse depois do await abaixo,
      // um 'load' que dispara antes do fetch de states resolver encontraria a
      // fonte ausente e nunca mais tentaria de novo (o listener é 'once').
      m.addSource('mun', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({
        id: 'mun-circles', type: 'circle', source: 'mun',
        paint: {
          'circle-color': MAP_COLORS.v4Strong,
          'circle-opacity': MARKER_OPACITY,
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 0.8,
          'circle-radius': MARKER_RADIUS_EXPR,
        },
      })

      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false })
      m.on('mouseenter', 'mun-circles', e => {
        m.getCanvas().style.cursor = 'pointer'
        const f = e.features?.[0]
        if (!f) return
        const p = f.properties as Record<string, unknown>
        const share = p.share == null ? '' :
          htmlSeguro`<div style="color:#64748b">${Number(p.share).toLocaleString('pt-BR')}% do município</div>`
        popup.setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number])
          .setHTML(
            html`<div style="font:12px system-ui;line-height:1.45">
               <div style="font-weight:600">${p.nome} <span style="color:#94a3b8">${p.uf}</span></div>
               <div>${Number(p.acessos).toLocaleString('pt-BR')} acessos</div>
               <div style="color:#64748b">B2C ${Number(p.pf).toLocaleString('pt-BR')} · B2B ${Number(p.pj).toLocaleString('pt-BR')}</div>
               ${share}
             </div>`)
          .addTo(m)
      })
      m.on('mouseleave', 'mun-circles', () => {
        m.getCanvas().style.cursor = onClickRef.current ? 'pointer' : ''
        popup.remove()
      })
      m.on('click', 'mun-circles', e => {
        const f = e.features?.[0]
        const ibge = (f?.properties as Record<string, unknown> | undefined)?.ibge
        if (ibge != null) onClickRef.current?.(String(ibge))
      })

      // Contorno dos estados é decoração pura — carrega depois, sem bloquear
      // a criação da fonte/camada de dados acima.
      fetch(BR_STATES_URL).then(r => r.json()).then(states => {
        if (!map.current) return
        map.current.addSource('states', { type: 'geojson', data: states })
        map.current.addLayer(
          { id: 'states-line', type: 'line', source: 'states', paint: STATE_OUTLINE_PAINT },
          'mun-circles',
        )
      }).catch(() => { /* contorno é decoração: sem ele o mapa ainda funciona */ })
    })

    return () => { ro.disconnect(); map.current?.remove(); map.current = null }
  }, [])

  useEffect(() => {
    const m = map.current
    if (!m) return
    const apply = () => {
      const src = m.getSource('mun') as maplibregl.GeoJSONSource | undefined
      if (!src) return
      src.setData(fc)
      // Raio pela raiz do número de acessos: área da bolha fica proporcional ao
      // valor, que é como o olho compara círculos. O piso de cada zoom (3/5/9)
      // é o mesmo do marcador-padrão dos outros mapas (MARKER_RADIUS_EXPR) — um
      // município sem acessos vira um ponto do mesmo peso visual que um ASN;
      // acima disso a bolha cresce com a magnitude.
      m.setPaintProperty('mun-circles', 'circle-radius', [
        'interpolate', ['linear'], ['zoom'],
        3, ['interpolate', ['linear'], ['sqrt', ['get', 'acessos']],
            0, 3, Math.sqrt(maxAcessos), 16],
        7, ['interpolate', ['linear'], ['sqrt', ['get', 'acessos']],
            0, 5, Math.sqrt(maxAcessos), 32],
        12, ['interpolate', ['linear'], ['sqrt', ['get', 'acessos']],
            0, 9, Math.sqrt(maxAcessos), 48],
      ])
    }
    if (m.isStyleLoaded()) apply()
    else m.once('load', apply)
  }, [fc, maxAcessos])

  const semCoordenada = centroids
    ? municipios.filter(m => !centroids[m.ibge]).length
    : 0

  // Alternativa em texto do mapa (NBR 17225 5.2.4): os municípios com mais acessos, com os mesmos números das bolhas.
  const alternativa = useMemo(() => [...municipios].sort((a, b) => b.acessos - a.acessos).slice(0, MAX_TABELA)
    .map((m) => ({ municipio: m.nome, uf: m.uf, acessos: m.acessos, share: m.share ?? null })), [municipios])
  const comParcela = alternativa.some((m) => m.share != null)
  const rotuloMapa = `Mapa de bolhas: acessos declarados em ${municipios.length.toLocaleString('pt-BR')} municípios (os números estão em "Ver dados")`

  return (
    <div>
      <div ref={container} style={{ height }} role="group" aria-label={rotuloMapa}
        className="w-full rounded-lg overflow-hidden border border-gray-200" />
      <div className="text-xs text-gray-500 mt-1">
        Bolha proporcional aos acessos declarados no município.
        {semCoordenada > 0 && ` ${semCoordenada} município(s) sem coordenada.`}
      </div>
      <VerDados dados={alternativa} campos={comParcela ? ['municipio', 'uf', 'acessos', 'share'] : ['municipio', 'uf', 'acessos']}
        rotulos={{ municipio: 'Município', uf: 'UF', acessos: 'Acessos', share: 'Parcela no município (%)' }}
        titulo={municipios.length > MAX_TABELA ? `Ver dados (${MAX_TABELA} municípios com mais acessos, de ${municipios.length.toLocaleString('pt-BR')})` : 'Ver dados (tabela dos municípios)'} />
    </div>
  )
}
