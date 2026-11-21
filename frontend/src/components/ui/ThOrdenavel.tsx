// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import type { Ordem } from '../../lib/ordenacao'

/**
 * Cabeçalho de coluna ordenável para tabelas montadas à mão, com o mesmo comportamento do `TabelaDados`: botão (teclado; NBR 17225
 * 5.1.13), `aria-sort` e seta. Sem `onOrdenar` vira um `<th>` comum. O estado vem de `useOrdenacao(...).props(campo)` ou, quando a
 * ordem é do servidor, de `alternarOrdem`.
 */
export function ThOrdenavel({ campo, ordem, onOrdenar, children, className = '', alinhar = 'left', title }: {
  campo: string
  ordem: Ordem | null | undefined
  onOrdenar?: (campo: string) => void
  children: ReactNode
  className?: string
  alinhar?: 'left' | 'right' | 'center'
  title?: string
}) {
  const sentido = ordem?.campo === campo ? ordem.dir : null
  const just = alinhar === 'right' ? 'justify-end text-right' : alinhar === 'center' ? 'justify-center text-center' : 'text-left'
  return (
    <th scope="col" className={className} title={title} aria-sort={sentido === 'asc' ? 'ascending' : sentido === 'desc' ? 'descending' : onOrdenar ? 'none' : undefined}>
      {onOrdenar ? (
        <button type="button" onClick={() => onOrdenar(campo)}
          className={`inline-flex w-full items-center gap-0.5 rounded hover:text-gray-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primario-500 ${just}`}>
          <span>{children}</span>
          <span aria-hidden="true" className={sentido ? 'text-primario-700' : 'text-gray-300'}>{sentido === 'asc' ? '▲' : sentido === 'desc' ? '▼' : '↕'}</span>
        </button>
      ) : children}
    </th>
  )
}
