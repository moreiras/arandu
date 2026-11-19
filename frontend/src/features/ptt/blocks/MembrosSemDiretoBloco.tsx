// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

export function MembrosSemDiretoBloco({ dados }: BlocoProps<PttCtx>) {
  const { membersWithoutDirect, nameMap } = dados
  return (
    <div className="rounded-lg border border-perigo-100 px-5 py-4">
      <h2 className="text-base font-semibold text-perigo-700 mb-3">
        Membros registrados sem peering direto
        <span className="ml-2 text-sm font-normal text-gray-500">
          {membersWithoutDirect.length} AS{membersWithoutDirect.length !== 1 ? 's' : ''}
        </span>
      </h2>
      <div className="flex flex-wrap gap-1.5">
        {membersWithoutDirect.map(asn => (
          <Link
            key={asn}
            to={`/asn/${asn}`}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-perigo-50 border border-perigo-200 text-xs text-perigo-800 hover:bg-perigo-100 transition-colors"
          >
            <span className="font-mono">AS{asn}</span>
            {nameMap[String(asn)] && (
              <span className="text-perigo-600 truncate max-w-[140px]">{nameMap[String(asn)]}</span>
            )}
          </Link>
        ))}
      </div>
    </div>
  )
}
