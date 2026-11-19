// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { PeerSection } from '../PeerSection'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

export function PeersV4Bloco({ dados }: BlocoProps<PttCtx>) {
  const { v4, mergedV4, peersV4, loadingPeersV4, loadingMembers, membersData, assinantes, selectedPeerV4, setSelectedPeerV4 } = dados
  return (
    v4 ? (
      <PeerSection
        afi={mergedV4 ?? v4}
        label="IPv4"
        accentColor="blue"
        peerStats={loadingPeersV4 ? null : (peersV4?.peers ?? {})}
        loadingMembers={loadingMembers && !membersData}
        selectedPeer={selectedPeerV4}
        onSelectPeer={setSelectedPeerV4}
        assinantes={assinantes}
        peeringdb={peersV4?.peeringdb}
      />
    ) : (
      <div className="rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-400">
        Dados IPv4 não coletados para este IXP no snapshot atual.
      </div>
    )
  )
}
