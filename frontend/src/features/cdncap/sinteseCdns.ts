// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { CDNPresenceResponse } from '../../types/api'
import { limitar, n0, palavra, type FraseSintese } from '../../lib/sintese'

export const REGRAS_SINTESE_CDNS = 'sintese-cdns-2'

/**
 * Síntese da presença de CDNs e CAPs (PT-22, cdns 5.2): dos mesmos números da matriz (`/cdns/presence`: provedores, colunas do IX.br e de fora). A lista é um
 * catálogo curado e incompleto: "nenhum provedor do catálogo" não quer dizer ausência de conteúdo, e a frase diz isso. Presença por cadastro de participantes
 * casado com a lista curada é inferida (mesmo selo do KPI do Panorama); a de fora vem do PeeringDB, autodeclarada. Não recomenda instalar nada em lugar algum.
 */
export function sinteseCdns(d: CDNPresenceResponse | null | undefined): FraseSintese[] {
  if (!d || d.cdns.length === 0) return []
  const noIxbr = d.cdns.filter((c) => c.ixbr_count > 0).length
  const fora = d.cdns.filter((c) => c.external_count > 0).length
  const pttsSemCdn = d.ixbr_columns.filter((c) => c.cdn_count === 0).length
  const nPtts = d.ixbr_columns.length
  return limitar([
    { id: 'catalogo', selo: 'inferido', fonte: 'catálogo curado do projeto e cadastro do IX.br', dataRef: d.snapshot_date,
      texto: `O catálogo acompanha ${n0(d.cdns.length)} ${palavra(d.cdns.length, 'provedor', 'provedores')} de CDN e de conteúdo. Desses, ${n0(noIxbr)} ${palavra(noIxbr, 'consta', 'constam')} do cadastro de participantes de ao menos um PTT do IX.br.` },
    nPtts > 0 && { id: 'ptts-sem', selo: 'inferido', fonte: 'catálogo curado do projeto e cadastro do IX.br', dataRef: d.snapshot_date,
      texto: pttsSemCdn === 0
        ? `${nPtts === 1 ? 'O PTT do IX.br tem' : `Todos os ${n0(nPtts)} PTTs do IX.br têm`} ao menos um provedor do catálogo no cadastro.`
        : `${n0(pttsSemCdn)} dos ${n0(nPtts)} ${palavra(nPtts, 'PTT', 'PTTs')} do IX.br ${palavra(pttsSemCdn, 'não tem', 'não têm')} nenhum provedor do catálogo no cadastro. O catálogo é incompleto, então zero não quer dizer ausência de conteúdo.` },
    d.external_columns.length > 0 && { id: 'fora', selo: 'fato', fonte: 'PeeringDB (autodeclarado)', dataRef: d.snapshot_date,
      texto: `Fora do IX.br, ${n0(fora)} ${palavra(fora, 'provedor do catálogo declara', 'provedores do catálogo declaram')} presença em ${n0(d.external_columns.length)} ${palavra(d.external_columns.length, 'IXP', 'IXPs')} do PeeringDB.` },
  ])
}
