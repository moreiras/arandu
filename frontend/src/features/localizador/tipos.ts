// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Tipos, cores e constantes do Localizador de Redes (divisão do pages/Localizador.tsx). */
import { MAP_COLORS } from '../../components/maps/mapTheme'

export interface AsnFeature {
  geometry: { coordinates: [number, number] } | null // [lon, lat]; nula quando a regra de pessoa natural não tem centróide
  properties: {
    asn: number; name: string
    cnpj?: string; razao_social?: string; nome_fantasia?: string
    city?: string; uf?: string; country?: string
  }
}

export interface PrefixFeature {
  geometry: { coordinates: [number, number] } | null // [lon, lat]; nula quando a regra de pessoa natural não tem centróide
  properties: { prefix_count?: number; ip_version?: number; origin_asn?: number; city?: string; uf?: string }
}

export interface PixFeature {
  geometry: { coordinates: [number, number] } | null // [lon, lat]; nula quando a regra de pessoa natural não tem centróide
  properties: { ixp_code?: string; name?: string; ixp_name?: string }
}

export interface ScmGeoFeature {
  geometry: { coordinates: [number, number] } | null
  properties: {
    cnpj: string
    razao_social: string
    nome_fantasia?: string
    municipio?: string
    uf?: string
    has_asn: boolean
    asns: number[] | string
    situacao?: string
    /** Declarou acessos no mês de referência do SICI (ausente em snapshot antigo). */
    sici_ativo?: boolean
    sici_mes_referencia?: string
    /** Tecnologia predominante declarada pela empresa ao SICI (nacional, por CNPJ; não é a do município). */
    sici_tecnologia?: string
  }
}

// Entidade da lista — deduplicada por CNPJ (ASes sem CNPJ ficam um por ASN).
// Reúne o que se sabe do operador: ASNs, outorga SCM e usuários SICI no raio.
export interface Entity {
  key: string
  cnpj?: string
  asns: number[]          // todos os ASNs conhecidos do CNPJ (ou o próprio AS)
  asnsNoRaio: number[]    // os que aparecem no raio (sede ou prefixo): contagem, etiquetas e CSV usam estes (LOC-E3)
  name: string
  city?: string; uf?: string
  fromHq: boolean         // sede de AS dentro do raio
  v4: boolean; v6: boolean // prefixos na região
  scm: boolean            // tem outorga SCM
  scmHq: boolean          // sede de SCM dentro do raio
  sici?: { acessos: number; municipios: number }
}

/** Sede de AS dentro do raio (um ponto no mapa). */
export interface AsnDot {
  lat: number; lon: number; asn: number; name: string
  cnpj?: string; razao_social?: string; nome_fantasia?: string; city?: string; uf?: string
}

/** Bolha de prefixos: um AS, uma família, uma localização. */
export interface Bubble {
  lat: number; lon: number; asn: number; name: string
  afi: number; own: boolean; city?: string; uf?: string
  count: number
}

export interface InfoAsn { name: string; cnpj?: string; razao_social?: string; nome_fantasia?: string; city?: string; uf?: string }

/** AS da lista (sede no raio e/ou prefixo na região). */
export interface AsnNaLista { asn: number; name: string; city?: string; uf?: string; fromHq: boolean; v4: boolean; v6: boolean }

export interface MunicipioSici { ibge: string; nome: string; uf: string; lat: number; lon: number; acessos: number; operadores: { cnpj: string; empresa: string; acessos: number }[] }

export type TipoTag = 'near' | 'major' | 'other' | 'none'
export interface TagIx { code: string; label: string; kind: TipoTag }

// ── cores (tema compartilhado — ver mapTheme.ts) ────────────────────────────
// forte = AS com sede na região (próprio) · fraco = AS com sede fora (externo)
export const V4_STRONG = MAP_COLORS.v4Strong
export const V4_WEAK = MAP_COLORS.v4Weak
export const V6_STRONG = MAP_COLORS.v6Strong
export const V6_WEAK = MAP_COLORS.v6Weak
export const HQ_COLOR = '#334155'    // sede do AS — cinza escuro
export const SCM_HQ_COLOR = MAP_COLORS.scmWithAsn // SCM com AS
export const CNPJ_COLOR = MAP_COLORS.cnpj  // cor do CNPJ nos tooltips
export const SICI_COLOR = MAP_COLORS.sici  // usuários declarados ao SICI, por município
export const SCM_SEM_AS_COLOR = MAP_COLORS.scmWithoutAsn
// Selo "SCM" com texto branco: a cor do mapa (#a855f7) dá 3,96:1; esta (purple-700) passa de 4,5:1 (NBR 17225 5.11.3).
export const SCM_SELO = '#7e22ce'

export function prefixColor(afi: number, own: boolean): string {
  if (afi === 6) return own ? V6_STRONG : V6_WEAK
  return own ? V4_STRONG : V4_WEAK
}

export const fmtBR = (n: number) => n.toLocaleString('pt-BR')

export function formatCnpj(cnpj: string): string {
  const d = cnpj.replace(/\D/g, '')
  if (d.length !== 14) return cnpj
  return `${d.slice(0,2)}.${d.slice(2,5)}.${d.slice(5,8)}/${d.slice(8,12)}-${d.slice(12)}`
}

export function parseAsns(raw: number[] | string): number[] {
  return typeof raw === 'string' ? JSON.parse(raw) : (raw ?? [])
}

// ── IXes do IX.br ────────────────────────────────────────────────────────────
// Principais sempre exibidos como tags, na ordem pedida.
export const MAJOR_IX = ['sp', 'ce', 'rj', 'df', 'rs'] as const

// ── tags de participação em IX ───────────────────────────────────────────────
// near  = IX mais próximo do ponto · major = um dos principais · other/none = genéricos
const IX_TAG_BASE = 'text-xs leading-4 px-1.5 rounded-full border whitespace-nowrap'
export const IX_TAG_CLASS: Record<TipoTag, string> = {
  near:  `${IX_TAG_BASE} bg-primario-600 text-white border-primario-600 font-medium`,
  major: `${IX_TAG_BASE} bg-primario-50 text-primario-700 border-primario-200`,
  other: `${IX_TAG_BASE} bg-gray-50 text-gray-500 border-gray-200`,
  none:  `${IX_TAG_BASE} bg-gray-50 text-gray-400 border-gray-200`,
}

export const BR_STATES_URL = '/br-states.geojson'
export const EMPTY_FC: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] }

/** ASNs de uma entidade que valem para o raio: os vistos no raio; para entidade só de SCM/SICI (nenhum ASN no raio), os do CNPJ. */
export const asnsDoRaio = (e: Entity): number[] => (e.asnsNoRaio.length ? e.asnsNoRaio : e.asns)
