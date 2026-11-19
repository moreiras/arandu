// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Fragment } from 'react'
import { Link } from 'react-router-dom'
import { GRUPOS_MENU } from './menu'

export interface Migalha { rotulo: string; to?: string; mono?: boolean }

/**
 * Migalhas temáticas: o grupo do menu primeiro, depois a lista de origem e a entidade — "Mercado › Operadoras › Brisanet",
 * "Território › CE › Mossoró". O grupo leva ao primeiro item dele (não existe página de grupo); o último item é a página atual.
 */
export function Migalhas({ grupo, itens }: { grupo: string; itens: Migalha[] }) {
  const g = GRUPOS_MENU.find((x) => x.id === grupo)
  const cadeia: Migalha[] = [...(g ? [{ rotulo: g.rotulo, to: g.itens[0]?.to }] : []), ...itens]
  return (
    <nav aria-label="Você está em" className="min-w-0">
      <ol className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
        {cadeia.map((m, i) => {
          const ultimo = i === cadeia.length - 1
          return (
            <Fragment key={`${i}-${m.rotulo}`}>
              {i > 0 && <li aria-hidden="true" className="text-gray-300">›</li>}
              <li className={m.mono ? 'font-mono' : undefined} aria-current={ultimo ? 'page' : undefined}>
                {m.to && !ultimo ? <Link to={m.to} className="hover:text-gray-700">{m.rotulo}</Link> : <span className="text-gray-600">{m.rotulo}</span>}
              </li>
            </Fragment>
          )
        })}
      </ol>
    </nav>
  )
}
