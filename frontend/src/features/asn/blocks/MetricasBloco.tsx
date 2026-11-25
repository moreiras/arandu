// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { MetricCard } from '../ui'
import { prefixosDe } from '../contexto'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

export function MetricasBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc } = dados
  const { rirV4: rirPrefixesV4, rirV6: rirPrefixesV6, globalV4: globalPrefixesV4, globalV6: globalPrefixesV6 } = prefixosDe(doc)
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <MetricCard
        label="Prefixos IPv6 (Registro.br)"
        value={rirPrefixesV6.length}
        sub={globalPrefixesV6.length !== rirPrefixesV6.length
          ? `${globalPrefixesV6.length} na tabela global`
          : undefined}
        accent="orange"
      />
      <MetricCard
        label="Prefixos IPv4 (Registro.br)"
        value={rirPrefixesV4.length}
        sub={globalPrefixesV4.length !== rirPrefixesV4.length
          ? `${globalPrefixesV4.length} na tabela global`
          : undefined}
        accent="blue"
      />
      <MetricCard label="PTTs com sessão no RS" value={doc.ixps_direct.length} />
      <MetricCard label="IXPs originador" value={doc.ixps_origin.length} />
    </div>
  )
}
