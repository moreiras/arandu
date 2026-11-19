// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { Frase } from '../asn/sintese'
import type { PrefixoInfo } from '../../services/api'
import type { ASNDocument } from '../../types/api'

/** Frase-síntese do prefixo: mesmas regras da ficha do AS (regras versionadas, sem IA, selo em cada frase), numa página curta e sem abas. */
export const REGRAS_VERSAO_PREFIXO = 'sintese-prefixo-1'

export function sintesePrefixo(info: PrefixoInfo, asn?: ASNDocument | null): Frase[] {
  const f: Frase[] = []
  const org = info.geo_org?.name
  f.push({
    id: 'origem', selo: 'fato',
    texto: info.origin_asn != null
      ? `${info.prefix} é originado pelo AS${info.origin_asn}${org ? ` (${org})` : ''} na tabela de roteamento.`
      : `${info.prefix} consta do Registro.br, mas não há origem observada na tabela de roteamento neste snapshot.`,
  })
  const estado = asn?.rpki_validation?.[info.prefix]
  if (estado === 'valid') f.push({ id: 'rpki', selo: 'fato', texto: 'A origem anunciada tem ROA válido.' })
  else if (estado === 'invalid') f.push({ id: 'rpki', selo: 'fato', texto: 'A origem anunciada é inválida frente aos ROAs publicados.' })
  else if (estado === 'not_found') f.push({ id: 'rpki', selo: 'fato', texto: 'Nenhum ROA publicado cobre este prefixo.' })
  if (info.uf) f.push({ id: 'geo', selo: 'inferido', texto: `Associado a ${info.uf} pela geolocalização do bloco e pelo cadastro da organização; não indica a posição de equipamento nem de pessoa.` })
  return f
}
