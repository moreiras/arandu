// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ReactNode } from 'react'
import { Link } from '../layout/LinkDatado'

/**
 * Nota curta das páginas que mostram totais que diferem de outras páginas (PT-15): o mesmo nome conta universos diferentes, o rótulo
 * de cada número diz o universo, e a explicação completa fica em `/sobre#contagens`. `children` traz, se houver, o caso desta página.
 */
export function NotaVariosTotais({ children, className = '' }: { children?: ReactNode; className?: string }) {
  return (
    <p className={`text-xs text-gray-600 max-w-[90ch] ${className}`} data-testid="nota-varios-totais">
      <strong className="font-semibold text-gray-700">Por que há vários totais.</strong>{' '}
      {children ?? 'Números com o mesmo nome podem contar universos diferentes (ASNs delegados pela LACNIC ao Brasil ou na lista do Registro.br; com sessão em route server, no cadastro do IX.br ou originando prefixo; municípios do IBGE ou do Censo).'}{' '}
      Cada rótulo diz o universo. <Link to="/sobre#contagens" className="text-primario-700 underline">Como cada total é contado</Link>.
    </p>
  )
}
