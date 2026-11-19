// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { OutorgaListSection } from '../OutorgaLista'
import type { BlocoProps } from '../../entidade/registry'
import type { OperadoraCtx } from '../contexto'

export function SeacBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const { dataSeac } = dados
  return (
    <OutorgaListSection
      titulo="SeAC (TV por assinatura)"
      fonte="SeAC (Serviço de Acesso Condicionado)"
      outorgas={dataSeac!.outorgas}
    />
  )
}
