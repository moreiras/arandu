// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ASNDocument, AbusoAsn, BloqueiosAsn, RadarAsn, ExposicaoAsn, TransitoAsn, FacilitiesAsn, HistoricoBloco, OrganizacaoAsn, PeeringAsn, PoliticaAsn, ProntidaoAsn, RouteServersAsn, SegurancaAsn } from '../../types/api'
import type { WeekSeries } from '../../components/bgp/HourlyActivityChart'

/** Tudo que um bloco da página de ASN pode precisar: o documento e os extras que a página busca em paralelo. */
export interface AsnCtx {
  /** Série e eventos recentes do AS (perfil, `include=historico`). */
  historico?: HistoricoBloco | null
  /** Segurança de roteamento (`include=seguranca`): ROV e DNSSEC medidos pelo APNIC, AS Rank do CAIDA e bogons. */
  seguranca?: SegurancaAsn | null
  /** Prontidão em segurança de roteamento (`include=prontidao`): índice em 4 pilares. */
  prontidao?: ProntidaoAsn | null
  /** Sessões do AS nos route servers do IX.br (`include=route_servers`). */
  routeServers?: RouteServersAsn | null
  /** Rejeições e política por communities nos route servers (`include=politica_rs`). */
  politicaRs?: PoliticaAsn | null
  /** Organização do AS no CAIDA e abuso agregado do Feodo Tracker (`include=organizacao,abuso`). */
  organizacao?: OrganizacaoAsn | null
  abuso?: AbusoAsn | null
  /** Cone de clientes inferido do AS (`include=transito`). */
  transito?: TransitoAsn | null
  /** Testes do OONI no AS: veredito da sonda, CC BY-NC-SA 4.0 (`include=bloqueios`). */
  bloqueios?: BloqueiosAsn | null
  /** Cloudflare Radar no AS: IPv6, tráfego e velocidade (só topo) e papel no BGP, CC BY-NC 4.0 (`include=radar`). */
  radar?: RadarAsn | null
  /** Exposição de serviços observada pelo Shodan no AS (`include=exposicao`). */
  exposicao?: ExposicaoAsn | null
  /** Instalações do Brasil e atributos de peering do PeeringDB (`include=facilities,peering`). */
  facilities?: FacilitiesAsn | null
  peering?: PeeringAsn | null
  doc: ASNDocument
  date: string | null
  /** Estabilidade BGP do AS (rota pesada, só nesta página) e a série das últimas semanas. */
  stabilityData?: any
  asnStability?: any
  asnWeeks?: WeekSeries[]
  asnDiagnosis?: any
  ixpPaths: Record<string, any>
  pathNodeMeta: Record<string, any>
  ixpMemberCodes: string[]
  ixpPeerStats?: any
  carregandoCaminhos: boolean
}

export function prefixosDe(doc: ASNDocument) {
  return {
    rirV4: doc.rir_prefixes_v4 ?? [],
    rirV6: doc.rir_prefixes_v6 ?? [],
    globalV4: doc.global_prefixes_v4 ?? [],
    globalV6: doc.global_prefixes_v6 ?? [],
    rpki: doc.rpki_validation ?? {},
  }
}
