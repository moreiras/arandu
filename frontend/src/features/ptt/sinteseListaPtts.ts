// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { ExternalIXPIndexEntry, IXPIndexEntry, SnapshotSummary } from '../../types/api'
import { compacto, limitar, n0, type FraseSintese } from '../../lib/sintese'

export const REGRAS_SINTESE_LISTA_PTTS = 'sintese-lista-ptts-1'

/**
 * Síntese da lista de PTTs (PT-22, ixps 5.5): dos mesmos objetos dos KPIs da página (`summary` do snapshot, PTTs do IX.br e IXPs externos). Só contagens e a
 * estimativa de usuários, cada uma com o próprio selo; o IX.br e os IXPs de fora ficam em frases separadas e nunca se somam num número só.
 */
export function sinteseListaPtts(ixps: IXPIndexEntry[], externos: ExternalIXPIndexEntry[], summary: SnapshotSummary | null | undefined, snapshot: string | null | undefined): FraseSintese[] {
  const diretos = summary?.ixp_aggregate?.asn_direct_union_count
  const alcancados = summary?.ixp_estimated_users_v4
  const pais = summary?.br_apnic_users_total
  const externosBr = summary?.external_ixps_br_asn_union_count
  const externosComBr = externos.filter((i) => (i.br_member_count ?? 0) > 0).length
  return limitar([
    diretos != null && ixps.length > 0 && { id: 'sessoes', selo: 'fato', fonte: 'looking glasses do IX.br', dataRef: snapshot,
      texto: `${n0(diretos)} ASNs distintos têm sessão com algum route server dos ${n0(ixps.length)} PTTs do IX.br (união; não é peering bilateral).` },
    alcancados != null && pais != null && { id: 'usuarios', selo: 'estimado', fonte: 'APNIC Labs e looking glasses do IX.br', dataRef: snapshot,
      texto: `Os prefixos vistos nos PTTs do IX.br alcançam cerca de ${compacto(alcancados)} dos ${compacto(pais)} usuários estimados em ASNs brasileiros (IPv4, cada usuário contado uma vez).` },
    externosBr != null && externos.length > 0 && { id: 'externos', selo: 'fato', fonte: 'PeeringDB (autodeclarado)', dataRef: snapshot,
      texto: `Fora do IX.br, ${n0(externosBr)} ASNs brasileiros declaram presença em ${n0(externosComBr)} dos ${n0(externos.length)} IXPs do PeeringDB.` },
  ])
}
