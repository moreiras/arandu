// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { OutorgaSection } from '../Outorgas'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

export function OutorgaScmBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc } = dados
  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-2">
        Outorgas SCM
        <span className="text-xs font-normal text-gray-400 ml-2">Anatel · cruzamento por CNPJ</span>
      </h2>
      <OutorgaSection outorgas={doc.scm ?? []} fonte="SCM (Serviço de Comunicação Multimídia)" />
    </div>
  )
}

export function OutorgaSmpBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc } = dados
  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-2">
        Outorgas SMP
        <span className="text-xs font-normal text-gray-400 ml-2">Anatel · cruzamento por CNPJ</span>
      </h2>
      <OutorgaSection outorgas={doc.smp ?? []} fonte="SMP (Serviço Móvel Pessoal)" />
    </div>
  )
}

export function OutorgaStfcBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc } = dados
  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-2">
        Outorgas STFC
        <span className="text-xs font-normal text-gray-400 ml-2">Anatel · cruzamento por CNPJ</span>
      </h2>
      <OutorgaSection outorgas={doc.stfc ?? []} fonte="STFC (Serviço Telefônico Fixo Comutado)" />
    </div>
  )
}

export function OutorgaSeacBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc } = dados
  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-2">
        Outorgas SeAC
        <span className="text-xs font-normal text-gray-400 ml-2">Anatel · cruzamento por CNPJ</span>
      </h2>
      <OutorgaSection outorgas={doc.seac ?? []} fonte="SeAC (Serviço de Acesso Condicionado)" />
    </div>
  )
}
