// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { Frase } from '../asn/sintese'
import type { PrefixoInfo } from '../../services/api'

/** Frase-síntese do prefixo: mesmas regras da ficha do AS (regras versionadas, sem IA, selo em cada frase), numa página curta e sem abas.
 *  Versão 2: o detentor (Registro.br) e a origem observada (tabela global) são frases separadas, e o RPKI é o do par anunciado. */
export const REGRAS_VERSAO_PREFIXO = 'sintese-prefixo-2'

const comNome = (asn: number, nome?: string | null) => `AS${asn}${nome ? ` (${nome})` : ''}`

export const FONTE_ORIGEM: Record<string, string> = {
  tabela_global: 'na tabela global coletada',
  route_servers_ixbr: 'nos route servers do IX.br',
}

export function sintesePrefixo(info: PrefixoInfo): Frase[] {
  const f: Frase[] = []
  const det = info.registro_asn ?? null
  if (det != null) {
    f.push({
      id: 'detentor', selo: 'fato',
      texto: info.escopo === 'rota_dentro_de_alocacao' && info.alocacao_registro_br
        ? `Dentro de ${info.alocacao_registro_br}, alocado pelo Registro.br ao ${comNome(det, info.registro_asn_nome ?? info.geo_org?.name)}.`
        : `Alocado pelo Registro.br ao ${comNome(det, info.registro_asn_nome ?? info.geo_org?.name)}.`,
    })
  } else if (info.escopo === 'fora_do_registro_br') {
    f.push({ id: 'detentor', selo: 'fato', texto: `${info.prefix} não está dentro de nenhuma alocação do Registro.br neste snapshot.` })
  }
  const orig = info.observed_origin_asn ?? null
  if (orig != null) {
    const onde = FONTE_ORIGEM[info.observed_origin_fonte ?? ''] ?? 'na tabela de roteamento coletada'
    const relacao = det == null ? '' : orig === det ? ', o mesmo AS do Registro.br' : ', diferente do AS do Registro.br'
    f.push({ id: 'origem', selo: 'fato', texto: `Anunciado ${onde} com origem ${comNome(orig, info.observed_origin_nome)}${relacao}.` })
  } else {
    f.push({ id: 'origem', selo: 'fato', texto: `${info.prefix} não é anunciado como está na tabela global coletada neste snapshot (pode haver rotas mais específicas dentro dele).` })
  }
  const r = info.rpki_observado
  if (r) {
    const autorizados = [...new Set(r.roas_que_cobrem.map((x) => `AS${x.asn}`))].join(', ')
    if (r.estado === 'valid') f.push({ id: 'rpki', selo: 'fato', texto: 'A origem observada tem ROA válido.' })
    else if (r.estado === 'invalid' && r.motivo === 'maxlength_excedido') f.push({ id: 'rpki', selo: 'fato', texto: `A origem observada é inválida frente aos ROAs publicados: o ROA do mesmo AS tem maxLength menor que /${info.prefix.split('/')[1]}.` })
    else if (r.estado === 'invalid') f.push({ id: 'rpki', selo: 'fato', texto: `A origem observada é inválida frente aos ROAs publicados: os ROAs que cobrem o prefixo autorizam ${autorizados || 'outro AS'}.` })
    else if (r.estado === 'not_found') f.push({ id: 'rpki', selo: 'fato', texto: 'Nenhum ROA publicado cobre este prefixo.' })
    else f.push({ id: 'rpki', selo: 'fato', texto: 'RPKI não avaliado: sem anúncio observado deste prefixo, não há par prefixo e origem para validar.' })
  }
  if (info.uf) f.push({ id: 'geo', selo: 'inferido', texto: `Associado a ${info.uf} pela geolocalização do bloco e pelo cadastro da organização; não indica a posição de equipamento nem de pessoa.` })
  return f
}
