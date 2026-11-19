// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { ASNAlertsPanel } from '../../../components/ASNAlertsPanel'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

export function AlertasBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc } = dados
  return (
    <ASNAlertsPanel alerts={doc.alerts} />
  )
}
