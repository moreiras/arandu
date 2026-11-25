// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { IXPPeerTable } from '../../components/tables/IXPPeerTable'
import type { IXPAssinantes } from '../../services/api'
import type { IXPAfiFull, IXPPeerStats, PeeringDbPeers } from '../../types/api'

export function PeerSection({
  afi,
  label,
  accentColor,
  peerStats,
  loadingMembers,
  selectedPeer,
  onSelectPeer,
  assinantes,
  peeringdb,
}: {
  afi: IXPAfiFull
  label: string
  accentColor: 'blue' | 'purple'
  peerStats: Record<string, IXPPeerStats> | null
  loadingMembers: boolean
  selectedPeer: number | null
  onSelectPeer: (asn: number | null) => void
  assinantes?: IXPAssinantes
  peeringdb?: PeeringDbPeers
}) {
  const accent = accentColor === 'blue' ? 'text-primario-700' : 'text-v6-700'
  const borderColor = accentColor === 'blue' ? 'border-primario-100' : 'border-v6-100'
  const afiKey: 'v4' | 'v6' = label === 'IPv6' ? 'v6' : 'v4'

  return (
    <div className={`rounded-lg border ${borderColor} px-5 py-4 space-y-4`}>
      <div className="flex items-baseline gap-3">
        <h2 className={`text-base font-semibold ${accent}`}>
          ASNs com sessão em route server — {label}
        </h2>
        <span className="text-sm text-gray-500">
          {afi.asn_direct_count} peers
          {afi.asn_stub_count > 0 && (
            <span className="text-gray-400 ml-2">
              · {afi.asn_stub_count} stubs · {afi.asn_direct_count - afi.asn_stub_count} não-stub
            </span>
          )}
        </span>
        {loadingMembers && (
          <span className="text-xs font-normal text-gray-400 animate-pulse">carregando membros…</span>
        )}
      </div>

      {loadingMembers && !afi.asn_direct ? (
        <div className="h-32 bg-gray-50 rounded animate-pulse" />
      ) : (
        <IXPPeerTable
          asnDirect={afi.asn_direct ?? []}
          asnStub={afi.asn_stub ?? []}
          brAsnsDirect={afi.br_asns_direct ?? []}
          peerStats={peerStats}
          afi={afiKey}
          selectedPeer={selectedPeer}
          onSelectPeer={onSelectPeer}
          assinantes={assinantes}
          peeringdb={peeringdb}
        />
      )}

      <p className="text-xs text-gray-400">
        Azul = prefixos próprios · Laranja = prefixos de terceiros repassados por este peer.
        Clique no botão da linha para destacar no mapa de Hilbert.
        Assinantes: acessos SCM (B2C + B2B) informados ao SICI
        {assinantes?.mes_referencia && <> (ref. {assinantes.mes_referencia})</>} pelo CNPJ do AS
        (ASNs com sessão no route server) e também pelos CNPJs dos ASes nos AS-paths que ele anuncia aqui (total, deduplicado por CNPJ).
      </p>
    </div>
  )
}
