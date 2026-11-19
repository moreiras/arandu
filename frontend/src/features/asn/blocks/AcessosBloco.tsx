// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { ASNAccessSection } from '../../../components/acessos/ASNAccessSection'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

export function AcessosBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc, date } = dados
  return (
    <ASNAccessSection asn={doc.asn} date={date ?? undefined} apnicUsers={doc.apnic_users} />
  )
}
