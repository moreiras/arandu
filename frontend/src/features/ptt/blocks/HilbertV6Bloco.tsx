// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { IXPHilbertV6 } from '../../../components/hilbert/IXPHilbertV6'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

export function HilbertV6Bloco({ dados }: BlocoProps<PttCtx>) {
  const { code, date, mergedV6, selectedPeerV6, setSelectedPeerV6 } = dados
  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-3">
        Espaço IPv6: curva de Hilbert
      </h2>
      <IXPHilbertV6
        code={code!}
        date={date ?? undefined}
        peerList={mergedV6?.asn_direct ?? []}
        selectedPeer={selectedPeerV6}
        onSelectPeer={setSelectedPeerV6}
        blockWidth={240}
      />
    </div>
  )
}
