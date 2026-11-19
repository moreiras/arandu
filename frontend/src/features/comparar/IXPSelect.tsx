// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/** Seletor de IXP (IX.br ou externo) da página Comparar. */


export type SelType = 'ixbr' | 'ext'
export const MIN_SETS = 2
export const MAX_SETS = 4

export function parseVal(v: string): { type: SelType; code: string } | null {
  if (!v) return null
  const idx = v.indexOf(':')
  if (idx === -1) return null
  return { type: v.slice(0, idx) as SelType, code: v.slice(idx + 1) }
}

export function makeVal(type: SelType, code: string) {
  return `${type}:${code}`
}

// ── Dropdown ─────────────────────────────────────────────────────────────────

export interface IXPOption {
  val: string
  label: string
  type: SelType
  code: string
}

export function IXPSelect({
  id,
  label,
  value,
  onChange,
  options,
  disabledVals,
  onRemove,
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
  options: IXPOption[]
  disabledVals: string[]
  onRemove?: () => void
}) {
  const ixbrOptions = options.filter(o => o.type === 'ixbr')
  const extOptions  = options.filter(o => o.type === 'ext')

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label htmlFor={id} className="block text-sm font-medium text-gray-700">{label}</label>
        {onRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="text-xs text-gray-400 hover:text-perigo-500"
            title="Remover este IXP da comparação"
          >
            remover ✕
          </button>
        )}
      </div>
      <select
        id={id}
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primario-400 bg-white"
      >
        <option value="">— Selecione um PTT —</option>
        <optgroup label="IX.br">
          {ixbrOptions.map(o => (
            <option key={o.val} value={o.val} disabled={disabledVals.includes(o.val)}>
              {o.label}
            </option>
          ))}
        </optgroup>
        <optgroup label="Outros IXPs (PeeringDB)">
          {extOptions.map(o => (
            <option key={o.val} value={o.val} disabled={disabledVals.includes(o.val)}>
              {o.label}
            </option>
          ))}
        </optgroup>
      </select>
    </div>
  )
}
