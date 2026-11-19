// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { GlobalTableSection } from '../TabelaGlobal'
import { prefixosDe } from '../contexto'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

export function TabelaGlobalBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc } = dados
  const { rirV4: rirPrefixesV4, rirV6: rirPrefixesV6, globalV4: globalPrefixesV4, globalV6: globalPrefixesV6, rpki: rpkiValidation } = prefixosDe(doc)
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {globalPrefixesV6.length > 0 ? (
        <GlobalTableSection
          title={`Tabela de rotas global IPv6 (${globalPrefixesV6.length})`}
          accent="amber"
          prefixes={globalPrefixesV6}
          rirPrefixes={rirPrefixesV6}
          rpkiValidation={rpkiValidation}
          cols={1}
          diffNote={globalPrefixesV6.length !== rirPrefixesV6.length
            ? `(${globalPrefixesV6.length - rirPrefixesV6.length > 0 ? '+' : ''}${globalPrefixesV6.length - rirPrefixesV6.length} vs Registro.br)`
            : undefined}
        />
      ) : (
        <div className="bg-gray-50 rounded border border-gray-200 p-4 flex items-center justify-center text-sm text-gray-400">
          Sem prefixos IPv6 na tabela global
        </div>
      )}
      {globalPrefixesV4.length > 0 ? (
        <GlobalTableSection
          title={`Tabela de rotas global IPv4 (${globalPrefixesV4.length})`}
          accent="teal"
          prefixes={globalPrefixesV4}
          rirPrefixes={rirPrefixesV4}
          rpkiValidation={rpkiValidation}
          cols={2}
          diffNote={globalPrefixesV4.length !== rirPrefixesV4.length
            ? `(${globalPrefixesV4.length - rirPrefixesV4.length > 0 ? '+' : ''}${globalPrefixesV4.length - rirPrefixesV4.length} vs Registro.br)`
            : undefined}
        />
      ) : (
        <div className="bg-gray-50 rounded border border-gray-200 p-4 flex items-center justify-center text-sm text-gray-400">
          Sem prefixos IPv4 na tabela global
        </div>
      )}
    </div>
  )
}
