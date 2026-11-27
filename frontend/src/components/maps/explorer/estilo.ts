// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Cor das sedes de AS por dimensão ("Colorir por"): expressão do MapLibre, rótulo do popup e itens da legenda. */
import type * as maplibregl from 'maplibre-gl'
import { COLOR_ASNS_GEO, COLOR_BOTH, COLOR_NONE, COLOR_SCM, COLOR_SCM_SICI_COM, COLOR_SCM_SICI_NA, COLOR_SCM_SICI_SEM, COLOR_SCM_WITH_ASN, COLOR_V4, COLOR_V6, COLOR_WITHOUT_SCM, COLOR_WITH_SCM } from './tipos'
import type { ScmColorBy } from './tipos'

export function colorExpr(colorBy: string): maplibregl.ExpressionSpecification {
  const cv: maplibregl.ExpressionSpecification = ['get', 'color_value']
  switch (colorBy) {
    case 'solid':
      return ['literal', COLOR_ASNS_GEO] as maplibregl.ExpressionSpecification
    case 'visibility':
      return ['match', cv, 'both', COLOR_BOTH, 'v4_only', COLOR_V4, 'v6_only', COLOR_V6, 'none', COLOR_NONE, COLOR_NONE]
    case 'rpki':
      return ['match', cv, 'yes', '#16a34a', 'no', '#dc2626', '#9ca3af']
    case 'aspa':
      return ['match', cv, 'yes', '#2563eb', 'no', '#dc2626', '#9ca3af']
    case 'porte':
      return ['match', cv,
        'MICRO EMPRESA', '#3b82f6',
        'EMPRESA DE PEQUENO PORTE', '#f59e0b',
        'DEMAIS', '#8b5cf6',
        '#9ca3af']
    case 'pct_v6':
      return ['interpolate', ['linear'],
        ['coalesce', ['to-number', cv, 0], 0],
        0, '#dc2626', 30, '#f59e0b', 60, '#16a34a', 100, '#2563eb']
    case 'outorga':
      return ['match', cv, 'with_scm', COLOR_WITH_SCM, 'without_scm', COLOR_WITHOUT_SCM, COLOR_NONE]
    default:
      return ['literal', COLOR_ASNS_GEO] as maplibregl.ExpressionSpecification
  }
}

export function colorValueLabel(cv: unknown, colorBy: string): string {
  if (colorBy === 'solid') return ''
  if (colorBy === 'visibility') {
    const m: Record<string, string> = { both: 'IPv6 + IPv4', v6_only: 'Só IPv6', v4_only: 'Só IPv4', none: 'Não visível na FT' }
    return m[cv as string] ?? String(cv ?? '')
  }
  if (colorBy === 'rpki') return cv === 'yes' ? 'Tem RPKI' : cv === 'no' ? 'Sem RPKI' : ''
  if (colorBy === 'aspa') return cv === 'yes' ? 'Tem ASPA' : cv === 'no' ? 'Sem ASPA' : ''
  if (colorBy === 'porte') return String(cv ?? '')
  if (colorBy === 'pct_v6') return cv != null ? `${cv}% IPv6` : ''
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
      { color: '#16a34a', label: 'Tem RPKI' },
      { color: '#dc2626', label: 'Sem RPKI' },
      { color: '#9ca3af', label: 'Desconhecido' },
    ]
    case 'aspa': return [
      { color: '#2563eb', label: 'Tem ASPA' },
      { color: '#dc2626', label: 'Sem ASPA' },
      { color: '#9ca3af', label: 'Desconhecido' },
    ]
    case 'porte': return [
      { color: '#3b82f6', label: 'Micro empresa' },
      { color: '#f59e0b', label: 'Pequeno porte' },
      { color: '#8b5cf6', label: 'Demais' },
      { color: '#9ca3af', label: 'Desconhecido' },
    ]
    case 'pct_v6': return [
      { color: '#dc2626', label: '0% IPv6' },
      { color: '#f59e0b', label: '30%' },
      { color: '#16a34a', label: '60%' },
      { color: '#2563eb', label: '100%' },
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
