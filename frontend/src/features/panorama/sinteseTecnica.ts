// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { BrasilIndicadores, SnapshotSummary } from '../../types/api'
import { limitar, n0, palavra, type FraseSintese } from '../../lib/sintese'
import { UNIVERSOS } from '../../lib/universos'
import { fracao, pct } from './formato'

export const REGRAS_SINTESE_TECNICA = 'sintese-tecnica-2'

/**
 * Síntese do Resumo do Panorama técnico (PT-22, panorama-técnico 5.2): frases montadas dos objetos que os KPIs da aba usam (`summary` do snapshot e
 * `/brasil/indicadores`), com as mesmas contas (`fracao`). Descreve, não explica: nada de causa, comparação regional nem juízo. O recorte por região
 * (5.2) é a tabela `RetratoRegional`, depois dos cartões, e não entra nas frases.
 */
export function sinteseTecnica(s: SnapshotSummary | null | undefined, br: BrasilIndicadores | null | undefined, ref: string | null | undefined): FraseSintese[] {
  const pub = br?.rpki?.publicacao
  const ix = s?.ixp_aggregate
  const pttsIxbr = s ? (s.ixps_ok ?? 0) + (s.ixps_partial ?? 0) + (s.ixps_missing ?? 0) : null
  const v6 = br?.ipv6?.pct_usuarios_ipv6
  const roa = pub && pub.br_asns_total > 0 && pub.br_asns_with_roa != null ? fracao(pub.br_asns_with_roa, pub.br_asns_total) : null
  const rov = br?.rov?.media_ponderada_pct
  return limitar([
    v6 != null && { id: 'ipv6', selo: 'estimado', fonte: 'APNIC Labs', dataRef: br?.snapshot_date ?? ref,
      texto: `${pct(v6)} dos usuários estimados no Brasil usam IPv6. A conta soma as estimativas do APNIC por ASN brasileiro.` },
    pub && roa != null && { id: 'roa', selo: 'fato', fonte: 'RPKI (Routinator)', dataRef: br?.snapshot_date ?? ref,
      texto: `${n0(pub.br_asns_with_roa)} dos ${n0(pub.br_asns_total)} ${UNIVERSOS.asnsRegistroBr.rotulo} publicaram ao menos uma ROA (${pct(roa)}).` },
    ix?.asn_direct_union_count != null && pttsIxbr != null && pttsIxbr > 0 && { id: 'ixbr', selo: 'fato', fonte: 'looking glasses do IX.br', dataRef: ref,
      texto: `O IX.br tem ${n0(pttsIxbr)} ${palavra(pttsIxbr, 'PTT', 'PTTs')}, e ${n0(ix.asn_direct_union_count)} ${palavra(ix.asn_direct_union_count, 'ASN tem', 'ASNs têm')} sessão em route server de algum deles. A conta é a união dos PTTs, sem peering bilateral.` },
    rov != null && { id: 'rov', selo: 'estimado', fonte: 'APNIC Labs', dataRef: br?.rov?.fonte?.as_of ?? br?.snapshot_date ?? ref,
      texto: `${pct(rov, 2)} das medições do APNIC indicam filtragem de rotas inválidas. A média é ponderada pelas amostras, não pelos usuários.` },
  ])
}
