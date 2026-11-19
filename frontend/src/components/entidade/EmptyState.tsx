// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { formatarReferencia } from './proveniencia'

/** "Sem dado neste snapshot": diz a data em vez de deixar o bloco em branco. */
export function EmptyState({ mensagem, snapshot, detalhe }: { mensagem?: string; snapshot?: string | null; detalhe?: string }) {
  return (
    <div className="rounded border border-dashed border-gray-300 px-4 py-6 text-center text-sm text-gray-500" role="status">
      <div>{mensagem ?? 'Sem dado neste snapshot'}{snapshot ? ` (${formatarReferencia(snapshot)})` : ''}.</div>
      {detalhe && <div className="mt-1 text-xs text-gray-400">{detalhe}</div>}
    </div>
  )
}
