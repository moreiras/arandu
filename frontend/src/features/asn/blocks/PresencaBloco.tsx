// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useLayoutEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { IXPPresenceGraph } from '../../../components/graphs/IXPPresenceGraph'
import { prefixosDe } from '../contexto'
import type { BlocoProps } from '../../entidade/registry'
import type { AsnCtx } from '../contexto'

export function PresencaBloco({ dados }: BlocoProps<AsnCtx>) {
  const { doc, ixpPaths, pathNodeMeta, ixpMemberCodes, ixpPeerStats, carregandoCaminhos } = dados
  const { rirV4: rirPrefixesV4, rirV6: rirPrefixesV6 } = prefixosDe(doc)
  const navigate = useNavigate()
  const loadingPaths = dados.carregandoCaminhos
  // Medição responsiva dos grafos SVG
  const presenceRef = useRef<HTMLDivElement>(null)
  const [presenceWidth, setPresenceWidth] = useState(560)
  useLayoutEffect(() => {
    const el = presenceRef.current
    if (!el) return
    const ro = new ResizeObserver(entries => {
      setPresenceWidth(Math.min(Math.floor(entries[0].contentRect.width), 560))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
      {/* IPv6 */}
      <div ref={presenceRef} className="overflow-hidden">
        <h2 className="text-base font-semibold text-gray-800 mb-3 flex items-center gap-2">
          Presença em IXPs — IPv6
          {loadingPaths && (
            <span className="text-xs font-normal text-gray-400 animate-pulse">carregando caminhos…</span>
          )}
        </h2>
        <IXPPresenceGraph
          mainAsn={doc.asn}
          afi="v6"
          mainAsnRirPrefixes={rirPrefixesV6}
          ixpPresence={doc.ixp_presence}
          ixpPaths={ixpPaths}
          pathNodeMeta={pathNodeMeta}
          ixpMemberCodes={ixpMemberCodes}
          ixpPeerStats={ixpPeerStats}
          onIxpClick={(code) => navigate(`/ixp/${code}`)}
          onBridgeClick={(asnId) => navigate(`/asn/${asnId}`)}
          width={presenceWidth}
          height={Math.round(presenceWidth * 420 / 560)}
        />
      </div>

      {/* IPv4 */}
      <div className="overflow-hidden">
        <h2 className="text-base font-semibold text-gray-800 mb-3 flex items-center gap-2">
          Presença em IXPs — IPv4
          {loadingPaths && (
            <span className="text-xs font-normal text-gray-400 animate-pulse">carregando caminhos…</span>
          )}
        </h2>
        <IXPPresenceGraph
          mainAsn={doc.asn}
          afi="v4"
          mainAsnRirPrefixes={rirPrefixesV4}
          ixpPresence={doc.ixp_presence}
          ixpPaths={ixpPaths}
          pathNodeMeta={pathNodeMeta}
          ixpMemberCodes={ixpMemberCodes}
          ixpPeerStats={ixpPeerStats}
          onIxpClick={(code) => navigate(`/ixp/${code}`)}
          onBridgeClick={(asnId) => navigate(`/asn/${asnId}`)}
          width={presenceWidth}
          height={Math.round(presenceWidth * 420 / 560)}
        />
      </div>
    </div>
  )
}
