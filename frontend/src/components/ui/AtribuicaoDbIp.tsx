// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { DBIP_TEXTO, DBIP_URL } from '../../lib/atribuicoes'

/** Link de atribuição do DB-IP, visível (não dentro de popover): a licença pede o link na página que usa a base. */
export function AtribuicaoDbIp({ className = '' }: { className?: string }) {
  return (
    <p className={`text-xs text-gray-500 ${className}`} data-testid="atribuicao-dbip">
      <a href={DBIP_URL} target="_blank" rel="noopener noreferrer" className="underline hover:text-gray-700">{DBIP_TEXTO}</a>
    </p>
  )
}
