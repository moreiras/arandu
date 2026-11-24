// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { CARTOES, type Cartao } from './cartoes'

/**
 * Destaque do snapshot: uma pergunta pronta reescrita como **um número com uma frase**. Reaproveita a consulta de um cartão
 * (`cartoes.json`, com `limit` 1: só o `total` interessa) e leva à lista completa. Roda a cada snapshot, sem texto escrito à mão sobre o dado.
 */
export interface Destaque {
  id: string
  cartaoId: string
  /** O que o número conta, no plural ("operadoras"). */
  unidade: string
  /** Continuação da frase depois do número e da unidade. */
  frase: string
  to: string
  rotulo: string
}

export const DESTAQUES: Destaque[] = [
  { id: 'grandes-sem-asn', cartaoId: 'grandes-sem-asn', unidade: 'operadoras', frase: 'com mais de 5 mil assinantes ainda não têm ASN próprio', to: '/operadoras?servico=scm', rotulo: 'Ver as operadoras' },
  { id: 'sem-rpki', cartaoId: 'sem-rpki', unidade: 'ASes brasileiros', frase: 'estão em 3 ou mais PTTs, anunciam IPv6 e não assinaram seus prefixos no RPKI', to: '/seguranca-de-roteamento', rotulo: 'Ver segurança de roteamento' },
  { id: 'monopolio-local', cartaoId: 'monopolio-local', unidade: 'municípios', frase: 'com mil acessos ou mais têm uma única operadora com 80% ou mais da banda larga fixa', to: '/municipios?ordem=hhi', rotulo: 'Ver os municípios por concentração' },
  // mesma consulta e mesma regra da lista de destino (`/acessos/divergencias/scm` com os parâmetros padrão do panorama): o número do
  // destaque é o total que o panorama mostra (HOME-E3; antes eram 351 de `classificacao=apnic_alto` contra 2.147 no destino)
  { id: 'divergencias', cartaoId: 'divergencias-apnic-anatel', unidade: 'ASNs', frase: 'têm usuários estimados pelo APNIC 10 vezes ou mais acima do esperado pelos acessos fixos declarados à Anatel', to: '/panorama/mercado', rotulo: 'Ver o panorama de mercado' },
]

/** O cartão de origem de um destaque (a consulta e as fontes). */
export function cartaoDe(d: Destaque): Cartao {
  const c = CARTOES.find((x) => x.id === d.cartaoId)
  if (!c) throw new Error(`destaque ${d.id}: cartão ${d.cartaoId} não existe em cartoes.json`)
  return c
}

/** Só as consultas que respondem `total` numa única chamada (`query` e `get`); a consulta pede 1 linha, não 5. */
export function consultaDoDestaque(d: Destaque): { tipo: 'query'; colecao: string; corpo: Record<string, unknown> } | { tipo: 'get'; caminho: string; params: Record<string, string | number | boolean> } {
  const c = cartaoDe(d).consulta
  if (c.tipo === 'query') return { tipo: 'query', colecao: c.colecao, corpo: { ...c.corpo, limit: 1 } }
  if (c.tipo === 'get') return { tipo: 'get', caminho: c.caminho, params: { ...(c.params ?? {}), limit: 1 } }
  throw new Error(`destaque ${d.id}: consulta derivada não cabe num número só`)
}
