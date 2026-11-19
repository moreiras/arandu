// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { IXPHilbert16 } from '../../../components/hilbert/IXPHilbert16'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

export function HilbertV4Bloco({ dados }: BlocoProps<PttCtx>) {
  const { code, date, mergedV4, selectedPeerV4, setSelectedPeerV4 } = dados
  return (
    <div>
      <h2 className="text-base font-semibold text-gray-800 mb-3">
        Espaço IPv4 — Curva de Hilbert
      </h2>
      <IXPHilbert16
        code={code!}
        date={date ?? undefined}
        peerList={mergedV4?.asn_direct ?? []}
        selectedPeer={selectedPeerV4}
        onSelectPeer={setSelectedPeerV4}
        width={440}
      />
    </div>
  )
}
