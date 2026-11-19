// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { RedeSection } from '../RedeSection'
import type { BlocoProps } from '../../entidade/registry'
import type { OperadoraCtx } from '../contexto'

export function RedeBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const { rede } = dados
  return (
    <RedeSection rede={rede!} />
  )
}
