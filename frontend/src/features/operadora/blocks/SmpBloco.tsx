// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { SmpSection } from '../SmpSection'
import type { BlocoProps } from '../../entidade/registry'
import type { OperadoraCtx } from '../contexto'

export function SmpBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const { dataMovel } = dados
  return (
    <SmpSection dataMovel={dataMovel!} />
  )
}
