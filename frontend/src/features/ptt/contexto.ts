// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { IXPAssinantes } from '../../services/api'
import type { FacilitiesPtt, HistoricoBloco, IXPAfiFull, IXPIndexAfi, PortasIxp, RejeicoesIxp, RouteServersIxp } from '../../types/api'

/** Tudo que um bloco da página de PTT pode precisar: o documento, o índice, os extras buscados em paralelo e a seleção compartilhada com os mapas de Hilbert. */
export interface PttCtx {
  /** Série e eventos recentes do PTT (perfil, `include=historico`). */
  historico?: HistoricoBloco | null
  /** Route servers do PTT e as sessões dos membros (`include=route_servers`). */
  routeServers?: RouteServersIxp | null
  /** Rejeições e política nos route servers do PTT (`include=rejeicoes`). */
  rejeicoes?: RejeicoesIxp | null
  /** Instalações do PeeringDB onde o PTT está e, nos externos, as portas por velocidade (`include=facilities,portas`). */
  facilities?: FacilitiesPtt | null
  portas?: PortasIxp | null
  code: string
  date: string | null
  ixp: any
  v4: IXPAfiFull | null
  v6: IXPAfiFull | null
  v4idx: IXPIndexAfi | null
  v6idx: IXPIndexAfi | null
  par: number | null
  dir: number | null
  dif: number | null
  org: number | null
  brOriginUnion: number | null
  cbrAsns: number | null
  cftAsns: number | null
  totalBrASNs: number | null
  totalGlobalASNs: number | null
  estUsers: any
  potential: any
  /** Usuários BR totais estimados pela APNIC no snapshot (`totais` do perfil). */
  usuariosBrTotal: number | null
  mergedV4: IXPAfiFull | null
  mergedV6: IXPAfiFull | null
  membersWithoutDirect: number[]
  nameMap: Record<string, string>
  peersV4: any
  peersV6: any
  loadingPeersV4: boolean
  loadingPeersV6: boolean
  loadingMembers: boolean
  membersData: any
  assinantes?: IXPAssinantes
  selectedPeerV4: number | null
  selectedPeerV6: number | null
  setSelectedPeerV4: (asn: number | null) => void
  setSelectedPeerV6: (asn: number | null) => void
}
