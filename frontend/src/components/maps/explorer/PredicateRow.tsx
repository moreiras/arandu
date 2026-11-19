// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Uma linha de filtro do recorte de ASes (tipo + valor + remover). */
import { CloseIcon } from './icones'
import { NEEDS_VALUE } from './consulta'
import type { Predicate, PredicateKind } from './tipos'

export const KIND_OPTIONS: Array<{ group: string; options: Array<{ value: PredicateKind; label: string }> }> = [
  { group: 'Base', options: [
    { value: 'is_br', label: 'Registro.br' },
  ]},
  { group: 'IXPs', options: [
    { value: 'ixps_direct_in',  label: 'Direto em PTT' },
    { value: 'ixps_direct_nin', label: 'Não direto em PTT' },
    { value: 'ixps_origin_in',  label: 'Origina em PTT' },
    { value: 'ixps_origin_nin', label: 'Não origina em PTT' },
  ]},
  { group: 'Segurança', options: [
    { value: 'has_rpki', label: 'Tem RPKI' },
    { value: 'no_rpki',  label: 'Sem RPKI' },
    { value: 'has_aspa', label: 'Tem ASPA' },
    { value: 'no_aspa',  label: 'Sem ASPA' },
  ]},
  { group: 'Alcance', options: [
    { value: 'v4_ft',      label: 'Anuncia IPv4 (FT)' },
    { value: 'v6_ft',      label: 'Anuncia IPv6 (FT)' },
    { value: 'pct_v6_gte', label: '% IPv6 ≥' },
  ]},
  { group: 'Porte', options: [
    { value: 'porte', label: 'Porte =' },
  ]},
  { group: 'Regulatório', options: [
    { value: 'has_scm', label: 'Tem outorga SCM' },
    { value: 'no_scm',  label: 'Sem outorga SCM' },
  ]},
]

export function predicatePlaceholder(kind: PredicateKind): string {
  if (kind === 'ixps_direct_in' || kind === 'ixps_direct_nin' ||
      kind === 'ixps_origin_in' || kind === 'ixps_origin_nin') return 'ex: sp'
  if (kind === 'pct_v6_gte') return '0–100'
  return ''
}

export function PredicateRow({
  predicate,
  onChange,
  onRemove,
}: {
  predicate: Predicate
  onChange: (partial: Partial<Predicate>) => void
  onRemove: () => void
}) {
  const inp = 'border border-gray-200 rounded px-1.5 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-primario-500 bg-white'

  return (
    <div className="flex items-center gap-1">
      <select
        aria-label="Campo do filtro"
        value={predicate.kind}
        onChange={e => onChange({ kind: e.target.value as PredicateKind, value: '' })}
        className={`flex-1 min-w-0 ${inp}`}
      >
        {KIND_OPTIONS.map(({ group, options }) => (
          <optgroup key={group} label={group}>
            {options.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </optgroup>
        ))}
      </select>

      {NEEDS_VALUE.has(predicate.kind) && predicate.kind === 'porte' && (
        <select
          aria-label="Porte"
          value={predicate.value}
          onChange={e => onChange({ value: e.target.value })}
          className={`w-20 ${inp}`}
        >
          <option value="">—</option>
          <option value="MICRO EMPRESA">Micro</option>
          <option value="EMPRESA DE PEQUENO PORTE">P. Porte</option>
          <option value="DEMAIS">Demais</option>
        </select>
      )}

      {NEEDS_VALUE.has(predicate.kind) && predicate.kind !== 'porte' && (
        <input
          type={predicate.kind === 'pct_v6_gte' ? 'number' : 'text'}
          value={predicate.value}
          onChange={e => onChange({ value: e.target.value })}
          placeholder={predicatePlaceholder(predicate.kind)}
          className={`w-14 ${inp}`}
          min={predicate.kind === 'pct_v6_gte' ? 0 : undefined}
          max={predicate.kind === 'pct_v6_gte' ? 100 : undefined}
        />
      )}

      <button
        onClick={onRemove}
        className="text-gray-300 hover:text-perigo-400 flex-shrink-0 transition-colors p-0.5"
        title="Remover filtro"
      >
        <CloseIcon />
      </button>
    </div>
  )
}
