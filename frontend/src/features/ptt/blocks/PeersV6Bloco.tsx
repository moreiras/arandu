// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { PeerSection } from '../PeerSection'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

export function PeersV6Bloco({ dados }: BlocoProps<PttCtx>) {
  const { v6, mergedV6, peersV6, loadingPeersV6, loadingMembers, membersData, assinantes, selectedPeerV6, setSelectedPeerV6 } = dados
  return (
    v6 ? (
      <PeerSection
        afi={mergedV6 ?? v6}
        label="IPv6"
        accentColor="purple"
        peerStats={loadingPeersV6 ? null : (peersV6?.peers ?? {})}
        loadingMembers={loadingMembers && !membersData}
        selectedPeer={selectedPeerV6}
        onSelectPeer={setSelectedPeerV6}
        assinantes={assinantes}
        peeringdb={peersV6?.peeringdb}
      />
    ) : (
      <div className="rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 text-sm text-gray-400">
        Dados IPv6 não coletados para este IXP no snapshot atual.
      </div>
    )
  )
}
