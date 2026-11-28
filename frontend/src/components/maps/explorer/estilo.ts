// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Cor das sedes de AS por dimensão ("Colorir por"): expressão do MapLibre, rótulo do popup e itens da legenda. */
import type * as maplibregl from 'maplibre-gl'
import { COLOR_ASNS_GEO, COLOR_BOTH, COLOR_NONE, COLOR_SCM, COLOR_SCM_SICI_COM, COLOR_SCM_SICI_NA, COLOR_SCM_SICI_SEM, COLOR_SCM_WITH_ASN, COLOR_V4, COLOR_V6, COLOR_WITHOUT_SCM, COLOR_WITH_SCM } from './tipos'
import type { ScmColorBy } from './tipos'

// Escala de um só matiz (azul), do claro ao escuro, para categorias sim/não e para faixas ordenadas: a cor não expressa juízo.
// Contraste WCAG entre pares: escuro/claro 4,6; escuro/médio 2,2; médio/claro 2,1; sem dado/claro 1,6. O texto da legenda e do balão sempre acompanha a cor.
export const COR_ESCURA = '#1e3a8a'
export const COR_MEDIA = '#2f6fe0'
export const COR_CLARA = '#7cb0f7'
export const COR_SEM_DADO = '#d9dde3'
export const COR_AMOSTRA_INSUFICIENTE = '#6b7280'

const NOTA_ROA = 'ROA publicada: o ASN aparece como origem autorizada em ao menos uma ROA válida (VRP) do RPKI. Não mede se as redes validam rotas (ROV).'
const NOTA_ASPA = 'Publicação do objeto ASPA (RPKI) pelo ASN como cliente. A verificação de ASPA (ASPA verification) pelas redes ainda não é medida.'
const NOTA_ROV = 'Estimado: medição por amostragem de usuários do APNIC Labs (I-RoV), não declaração da rede. Faixa do percentual de medições em que a rede não alcança rota RPKI-inválida; com menos de 100 amostras, a faixa não é calculada.'

/** Selo e nota exibidos sob os itens da legenda de uma dimensão de cor (vazio quando não há). */
export function colorByNota(colorBy: string): { selo?: string; nota: string } | null {
  switch (colorBy) {
    case 'rpki': return { nota: NOTA_ROA }
    case 'aspa': return { nota: NOTA_ASPA }
    case 'rov': return { selo: 'estimado', nota: NOTA_ROV }
    default: return null
  }
}

export function colorExpr(colorBy: string): maplibregl.ExpressionSpecification {
  const cv: maplibregl.ExpressionSpecification = ['get', 'color_value']
  switch (colorBy) {
    case 'solid':
      return ['literal', COLOR_ASNS_GEO] as maplibregl.ExpressionSpecification
    case 'visibility':
      return ['match', cv, 'both', COLOR_BOTH, 'v4_only', COLOR_V4, 'v6_only', COLOR_V6, 'none', COLOR_NONE, COLOR_NONE]
    case 'rpki':
      return ['match', cv, 'yes', COR_ESCURA, 'no', COR_CLARA, COR_SEM_DADO]
    case 'aspa':
      return ['match', cv, 'yes', COR_ESCURA, 'no', COR_CLARA, COR_SEM_DADO]
    case 'rov':
      return ['match', cv, 'ate_10', COR_CLARA, 'de_10_a_90', COR_MEDIA, 'acima_de_90', COR_ESCURA, 'amostra_insuficiente', COR_AMOSTRA_INSUFICIENTE, COR_SEM_DADO]
    case 'porte':
      return ['match', cv,
        'MICRO EMPRESA', '#3b82f6',
        'EMPRESA DE PEQUENO PORTE', '#f59e0b',
        'DEMAIS', '#8b5cf6',
        '#9ca3af']
    case 'pct_v6':
      return ['case', ['has', 'color_value'],
        ['interpolate', ['linear'], ['to-number', cv, 0], 0, COR_CLARA, 50, COR_MEDIA, 100, COR_ESCURA],
        COR_SEM_DADO]
    case 'outorga':
      return ['match', cv, 'with_scm', COLOR_WITH_SCM, 'without_scm', COLOR_WITHOUT_SCM, COLOR_NONE]
    default:
      return ['literal', COLOR_ASNS_GEO] as maplibregl.ExpressionSpecification
  }
}

const ROV_ROTULOS: Record<string, string> = {
  ate_10: 'Até 10% das medições com validação',
  de_10_a_90: 'De 10% a 90% das medições com validação',
  acima_de_90: 'Acima de 90% das medições com validação',
  amostra_insuficiente: 'Amostra insuficiente',
  sem_dado: 'Sem dado',
}

export function colorValueLabel(cv: unknown, colorBy: string): string {
  if (colorBy === 'solid') return ''
  if (colorBy === 'visibility') {
    const m: Record<string, string> = { both: 'IPv6 + IPv4', v6_only: 'Só IPv6', v4_only: 'Só IPv4', none: 'Não visível na FT' }
    return m[cv as string] ?? String(cv ?? '')
  }
  if (colorBy === 'rpki') return cv === 'yes' ? 'Com ROA publicada' : cv === 'no' ? 'Sem ROA publicada' : 'Sem dado'
  if (colorBy === 'aspa') return cv === 'yes' ? 'Com ASPA publicada' : cv === 'no' ? 'Sem ASPA publicada' : 'Sem dado'
  if (colorBy === 'rov') return ROV_ROTULOS[cv as string] ?? 'Sem dado'
  if (colorBy === 'porte') return String(cv ?? '')
  if (colorBy === 'pct_v6') return cv != null ? `${cv}% IPv6` : 'Sem dado'
  if (colorBy === 'outorga') return cv === 'with_scm' ? 'Com outorga SCM' : cv === 'without_scm' ? 'Sem outorga SCM' : ''
  return ''
}

export function colorByItems(colorBy: string): Array<{ color: string; label: string; opacity?: number }> {
  switch (colorBy) {
    case 'visibility': return [
      { color: COLOR_BOTH, label: 'IPv6 + IPv4' },
      { color: COLOR_V4,   label: 'Só IPv4' },
      { color: COLOR_V6,   label: 'Só IPv6' },
      { color: COLOR_NONE, label: 'Não visível na FT', opacity: 0.6 },
    ]
    case 'rpki': return [
      { color: COR_ESCURA, label: 'Com ROA publicada' },
      { color: COR_CLARA, label: 'Sem ROA publicada' },
      { color: COR_SEM_DADO, label: 'Sem dado' },
    ]
    case 'aspa': return [
      { color: COR_ESCURA, label: 'Com ASPA publicada' },
      { color: COR_CLARA, label: 'Sem ASPA publicada' },
      { color: COR_SEM_DADO, label: 'Sem dado' },
    ]
    case 'rov': return [
      { color: COR_CLARA, label: 'Até 10% das medições com validação' },
      { color: COR_MEDIA, label: 'De 10% a 90%' },
      { color: COR_ESCURA, label: 'Acima de 90%' },
      { color: COR_AMOSTRA_INSUFICIENTE, label: 'Amostra insuficiente' },
      { color: COR_SEM_DADO, label: 'Sem dado' },
    ]
    case 'porte': return [
      { color: '#3b82f6', label: 'Micro empresa' },
      { color: '#f59e0b', label: 'Pequeno porte' },
      { color: '#8b5cf6', label: 'Demais' },
      { color: '#9ca3af', label: 'Desconhecido' },
    ]
    case 'pct_v6': return [
      { color: COR_CLARA, label: '0% IPv6' },
      { color: COR_MEDIA, label: '50%' },
      { color: COR_ESCURA, label: '100%' },
      { color: COR_SEM_DADO, label: 'Sem dado' },
    ]
    case 'outorga': return [
      { color: COLOR_WITH_SCM,    label: 'AS com outorga SCM' },
      { color: COLOR_WITHOUT_SCM, label: 'AS sem outorga SCM' },
    ]
    default: return []
  }
}

/** Cor das outorgas SCM: por ASN (padrão) ou pela declaração de acessos ao SICI (PT-26, MAPA 5.4). */
export function scmColorExpr(por: ScmColorBy): maplibregl.ExpressionSpecification {
  if (por === 'sici') {
    return ['match', ['to-string', ['coalesce', ['get', 'sici_ativo'], '']], 'true', COLOR_SCM_SICI_COM, 'false', COLOR_SCM_SICI_SEM, COLOR_SCM_SICI_NA]
  }
  return ['case', ['get', 'has_asn'], COLOR_SCM_WITH_ASN, COLOR_SCM]
}
