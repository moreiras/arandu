// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { AspaCustomersTable, AspaProvidersTable } from '../RpkiTabelas'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

export function AspaBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc } = dados
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <AspaProvidersTable aspaProviders={doc.aspa_providers ?? []} />
      <AspaCustomersTable aspaCustomers={doc.aspa_customers ?? []} />
    </div>
  )
}
