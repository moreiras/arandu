// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Tipos, constantes e definição das camadas do mapa "Explorar" (divisão do ExplorerMap.tsx). */
import { MAP_COLORS, MAP_DEFAULT_CENTER, MAP_DEFAULT_ZOOM } from '../mapTheme'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type PredicateKind =
  | 'is_br'
  | 'ixps_direct_in'
  | 'ixps_direct_nin'
  | 'ixps_origin_in'
  | 'ixps_origin_nin'
  | 'has_rpki'
  | 'no_rpki'
  | 'has_aspa'
  | 'no_aspa'
  | 'v4_ft'
  | 'v6_ft'
  | 'pct_v6_gte'
  | 'porte'
  | 'has_scm'
  | 'no_scm'

export interface Predicate {
  id: string
  kind: PredicateKind
  value: string
}

export interface FilterGroup {
  id: string
  op: 'and' | 'or'
  predicates: Predicate[]
}

// Camadas com dados buscados pelo front: uma consulta por camada, cada uma com seu
// cache, para ligar ou desligar uma camada sem recarregar as outras e sobrepor
// camadas de origens diferentes. Cabos/enlaces/linhas de transmissão vêm do estilo
// base (mapTheme.ts) e só têm a visibilidade alternada aqui.
export type DataLayerId =
  | 'pix'
  | 'asns_geo'
  | 'outorgas_scm'
  | 'prefixes_v4'
  | 'prefixes_v6'
  | 'prefixos_ix_v4'
  | 'prefixos_ix_v6'
  | 'roads_federal'
  | 'roads_estadual'
  | 'erbs'

export type StyleLayerId = 'submarine' | 'terrestrial' | 'power'
export type LayerId = DataLayerId | StyleLayerId

export type ScmMode = 'todas' | 'com_asn' | 'sem_asn'

export interface MapState {
  // Recorte de ASes — vale para todas as camadas com `recorte: true`
  groupOp: 'and' | 'or'
  groups: FilterGroup[]
  nearIxp: string
  nearRadiusKm: number
  nearMode: 'sede' | 'prefixos'
  // Camadas ligadas
  on: Record<LayerId, boolean>
  // Ajustes por camada
  colorBy: string
  scmMode: ScmMode
  ixCode: string
  ixExcludeAsns: string
  ixIncludeAsns: string
  pixOnlySelected: boolean
  roadsFederalPaved: boolean
  roadsEstadualPaved: boolean
  /** Geração das estações do SMP na camada Antenas: '' = todas, ou 2G/3G/4G/5G. */
  erbsGeracao: string
}

export type LayerGroup = 'internet' | 'ptt' | 'infra'

export interface LayerDef {
  id: LayerId
  label: string
  group: LayerGroup
  color: string
  // Respeita o recorte de ASes (🔻)
  recorte?: boolean
  // Tem exportação CSV
  csv?: boolean
  // Forma do ícone no menu
  shape: 'dot' | 'line'
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const BRAZIL_CENTER = MAP_DEFAULT_CENTER
export const BRAZIL_ZOOM = MAP_DEFAULT_ZOOM
export const BR_STATES_URL = '/br-states.geojson'
export const EMPTY_FC: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] }
export const PANEL_WIDTH = 288

// Cores (tema compartilhado — ver mapTheme.ts)
export const COLOR_BOTH  = MAP_COLORS.visibilityBoth
export const COLOR_V4    = MAP_COLORS.visibilityV4Only
export const COLOR_V6    = MAP_COLORS.visibilityV6Only
export const COLOR_NONE  = MAP_COLORS.visibilityNone

export const COLOR_PIX          = MAP_COLORS.pixFill
export const COLOR_PIX_STROKE   = MAP_COLORS.pixStroke
export const COLOR_PREF_V4_BR   = MAP_COLORS.prefixV4Br
export const COLOR_PREF_V6_BR   = MAP_COLORS.prefixV6Br
export const COLOR_PREF_V4_PTT  = '#c4b5fd'
export const COLOR_PREF_V6_PTT  = '#f87171'
export const COLOR_ASNS_GEO     = MAP_COLORS.asMember
export const COLOR_SCM          = MAP_COLORS.scmWithoutAsn // só SCM (sem ASN) — igual ao Localizador
export const COLOR_SCM_WITH_ASN = MAP_COLORS.scmWithAsn
export const COLOR_SCM_STROKE   = '#6b21a8'
// Dimensão "outorga" do colorBy das sedes de AS:
export const COLOR_WITH_SCM     = '#60a5fa' // AS + SCM — azul claro
export const COLOR_WITHOUT_SCM  = '#1e3a8a' // só AS (sem outorga) — azul escuro

export const LAYERS: LayerDef[] = [
  { id: 'asns_geo',       label: 'Sedes dos ASes',        group: 'internet', color: COLOR_ASNS_GEO,    recorte: true, csv: true, shape: 'dot' },
  { id: 'outorgas_scm',   label: 'Operadores SCM',        group: 'internet', color: COLOR_SCM,         recorte: true, csv: true, shape: 'dot' },
  { id: 'prefixes_v6',    label: 'Prefixos IPv6 BR',      group: 'internet', color: COLOR_PREF_V6_BR,  recorte: true, csv: true, shape: 'dot' },
  { id: 'prefixes_v4',    label: 'Prefixos IPv4 BR',      group: 'internet', color: COLOR_PREF_V4_BR,  recorte: true, csv: true, shape: 'dot' },
  { id: 'prefixos_ix_v6', label: 'Prefixos IPv6 PTT',     group: 'ptt',      color: COLOR_PREF_V6_PTT, recorte: true, csv: true, shape: 'dot' },
  { id: 'prefixos_ix_v4', label: 'Prefixos IPv4 PTT',     group: 'ptt',      color: COLOR_PREF_V4_PTT, recorte: true, csv: true, shape: 'dot' },
  { id: 'pix',            label: 'PIX dos PTTs',          group: 'infra',    color: COLOR_PIX,                               shape: 'dot' },
  { id: 'submarine',      label: 'Cabos submarinos',      group: 'infra',    color: MAP_COLORS.submarineCableBr,             shape: 'line' },
  { id: 'terrestrial',    label: 'Enlaces terrestres (ITU)', group: 'infra', color: MAP_COLORS.terrestrialLink,              shape: 'line' },
  { id: 'power',          label: 'Linhas de transmissão (ANEEL)', group: 'infra', color: MAP_COLORS.powerLine,               shape: 'line' },
  { id: 'erbs',           label: 'Antenas do SMP (licenciadas)', group: 'infra', color: MAP_COLORS.erbs,                    shape: 'dot' },
  { id: 'roads_federal',  label: 'Rodovias federais',     group: 'infra',    color: MAP_COLORS.road,                         shape: 'line' },
  { id: 'roads_estadual', label: 'Rodovias estaduais',    group: 'infra',    color: MAP_COLORS.roadState,                    shape: 'line' },
]
export const LAYER_BY_ID = Object.fromEntries(LAYERS.map(l => [l.id, l])) as Record<LayerId, LayerDef>

// Ordem de busca — da menor para a maior quantidade de dados estimada, para o
// usuário já ver as camadas leves enquanto as pesadas carregam.
export const FETCH_ORDER: DataLayerId[] = [
  'pix', 'asns_geo', 'outorgas_scm', 'prefixes_v6', 'prefixes_v4',
  'roads_federal', 'roads_estadual', 'erbs', 'prefixos_ix_v6', 'prefixos_ix_v4',
]
export const MAX_CONCURRENT = 2

export const PTT_LAYERS = new Set<LayerId>(['prefixos_ix_v4', 'prefixos_ix_v6'])

// Ordem de desenho (de baixo para cima) e opacidade base de cada camada MapLibre.
// A opacidade cai para STALE_FACTOR × base enquanto dados antigos aguardam os novos.
export const STALE_FACTOR = 0.35
// Nomes de propriedade de pintura tipados (o MapLibre 6 recusa `string` em setPaintProperty).
export type PropriedadeOpacidade = 'circle-opacity' | 'line-opacity' | 'fill-opacity'
export const MAPLIBRE_LAYERS: Array<{ id: string; data: DataLayerId; opacityProp: PropriedadeOpacidade; opacity: number }> = [
  { id: 'explorer-erbs',           data: 'erbs',           opacityProp: 'circle-opacity', opacity: 0.55 },
  { id: 'explorer-roads-estadual', data: 'roads_estadual', opacityProp: 'line-opacity',   opacity: 0.75 },
  { id: 'explorer-roads-federal',  data: 'roads_federal',  opacityProp: 'line-opacity',   opacity: 0.85 },
  { id: 'explorer-pref-v4',        data: 'prefixes_v4',    opacityProp: 'circle-opacity', opacity: 0.6 },
  { id: 'explorer-pref-v6',        data: 'prefixes_v6',    opacityProp: 'circle-opacity', opacity: 0.6 },
  { id: 'explorer-pref-ix-v4',     data: 'prefixos_ix_v4', opacityProp: 'circle-opacity', opacity: 0.7 },
  { id: 'explorer-pref-ix-v6',     data: 'prefixos_ix_v6', opacityProp: 'circle-opacity', opacity: 0.7 },
  { id: 'explorer-scms',           data: 'outorgas_scm',   opacityProp: 'circle-opacity', opacity: 0.65 },
  { id: 'explorer-asns',           data: 'asns_geo',       opacityProp: 'circle-opacity', opacity: 0.8 },
  { id: 'explorer-pix',            data: 'pix',            opacityProp: 'circle-opacity', opacity: 0.9 },
]

export const INITIAL: MapState = {
  groupOp: 'and',
  groups: [],
  nearIxp: '',
  nearRadiusKm: 150,
  nearMode: 'sede',
  on: {
    pix: true,
    asns_geo: false,
    outorgas_scm: false,
    prefixes_v4: false,
    prefixes_v6: false,
    prefixos_ix_v4: false,
    prefixos_ix_v6: false,
    roads_federal: false,
    roads_estadual: false,
    erbs: false,
    submarine: false,
    terrestrial: false,
    power: false,
  },
  colorBy: 'solid',
  scmMode: 'todas',
  ixCode: 'sp',
  ixExcludeAsns: '',
  ixIncludeAsns: '',
  pixOnlySelected: false,
  roadsFederalPaved: false,
  roadsEstadualPaved: false,
  erbsGeracao: '',
}
