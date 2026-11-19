// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { TabelaOperadores } from '../TabelaOperadores'
import type { BlocoProps } from '../../entidade/registry'
import type { MunicipioCtx } from '../contexto'

export function MercadoMovelBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const data = dados.movel!
  return <TabelaOperadores titulo={`Telefonia móvel em ${data.nome}`} operadores={data.operadores} />
}
