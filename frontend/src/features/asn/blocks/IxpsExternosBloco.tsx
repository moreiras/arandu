// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../../components/layout/LinkDatado'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

export function IxpsExternosBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc } = dados
  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-2">
        Presença em outros IXPs
      </h2>
      <div className="flex flex-wrap gap-2">
        {doc.external_ixps!.map(code => (
          <Link
            key={code}
            to={`/ixp-externo/${code}`}
            className="px-3 py-1.5 rounded border border-primario-200 bg-primario-50 text-primario-700 text-sm hover:bg-primario-100 transition-colors"
          >
            {code}
          </Link>
        ))}
      </div>
      <p className="text-xs text-gray-400 mt-1.5">
        Fonte: PeeringDB, dados autodeclarados
      </p>
    </div>
  )
}
