// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { ACCENT, type Accent } from './ui'

export function PrefixSection({
  title,
  accent,
  prefixes,
  renderItem,
  total,
  shown,
  onShowAll,
  footer,
}: {
  title: string
  accent: Accent
  prefixes: string[]
  renderItem: (p: string) => React.ReactNode
  total: number
  shown: number
  onShowAll: () => void
  footer?: string
}) {
  const dotColor = ACCENT[accent].dot
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-800 mb-1.5 flex items-center gap-2">
        <span className={`inline-block w-3 h-3 rounded-sm ${dotColor}`} />
        {title}
      </h3>
      <div className="bg-gray-50 rounded border border-gray-200 p-3 max-h-48 overflow-y-auto font-mono text-xs">
        <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
          {prefixes.map(renderItem)}
        </div>
      </div>
      {total > shown && (
        <button
          onClick={onShowAll}
          className="mt-1.5 text-xs text-primario-600 hover:underline"
        >
          Ver todos os {total} prefixos
        </button>
      )}
      {footer && <p className="text-xs text-gray-400 mt-1">{footer}</p>}
    </div>
  )
}

