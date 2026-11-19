// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { PrefixSection } from '../Prefixos'
import { prefixosDe } from '../contexto'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

export function PrefixosRirBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc } = dados
  const { rirV4: rirPrefixesV4, rirV6: rirPrefixesV6 } = prefixosDe(doc)
  const [showAllV4, setShowAllV4] = useState(false)
  const [showAllV6, setShowAllV6] = useState(false)
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {rirPrefixesV6.length > 0 ? (
        <PrefixSection
          title={`IPv6 alocado pelo Registro.br (${rirPrefixesV6.length})`}
          accent="orange"
          prefixes={showAllV6 ? rirPrefixesV6 : rirPrefixesV6.slice(0, 50)}
          renderItem={(p) => <div key={p} className="text-alerta-700">{p}</div>}
          total={rirPrefixesV6.length}
          shown={Math.min(rirPrefixesV6.length, showAllV6 ? rirPrefixesV6.length : 50)}
          onShowAll={() => setShowAllV6(true)}
        />
      ) : (
        <div className="bg-gray-50 rounded border border-gray-200 p-4 flex items-center justify-center text-sm text-gray-400">
          Sem prefixos IPv6
        </div>
      )}
      {rirPrefixesV4.length > 0 ? (
        <PrefixSection
          title={`IPv4 alocado pelo Registro.br (${rirPrefixesV4.length})`}
          accent="blue"
          prefixes={showAllV4 ? rirPrefixesV4 : rirPrefixesV4.slice(0, 50)}
          renderItem={(p) => <div key={p} className="text-primario-700">{p}</div>}
          total={rirPrefixesV4.length}
          shown={Math.min(rirPrefixesV4.length, showAllV4 ? rirPrefixesV4.length : 50)}
          onShowAll={() => setShowAllV4(true)}
        />
      ) : (
        <div className="bg-gray-50 rounded border border-gray-200 p-4 flex items-center justify-center text-sm text-gray-400">
          Sem prefixos IPv4
        </div>
      )}
    </div>
  )
}
