// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { Regiao, SiciOperador } from '../../types/api'

/** Operadora com menos desta parcela do fixo local vai para "Demais" (a lista inteira fica a um clique). */
export const PARCELA_MINIMA_LINHA_PCT = 1
/** Número máximo de linhas nominais antes de "Demais". */
export const MAX_LINHAS = 8

export type SituacaoRede = 'sem_asn' | 'direta' | 'so_indireta' | 'sem_ptt' | 'indeterminada'

export interface LinhaQuemAtende {
  cnpj: string
  /** nome a exibir: o do SICI, ou o do ASN quando o SICI não informa nome */
  nome: string
  nomeDoAsn: boolean
  /** nome não informado ao SICI e sem ASN para suprir: a linha mostra o CNPJ */
  semNome: boolean
  /** marca do cadastro quando o CNPJ está numa mudança de CNPJ provável (inferido) */
  marca?: string
  acessos: number
  share: number
  asns: number[]
  diretos: string[]
  /** PTTs em que a operadora só aparece de forma indireta (sem sessão direta nele) */
  indiretos: string[]
  situacao: SituacaoRede
}
export interface QuemAtende {
  linhas: LinhaQuemAtende[]
  /** operadoras abaixo do corte, agregadas */
  demais: { n: number; acessos: number; share: number; comAsn: number; comSessaoDireta: number; linhas: LinhaQuemAtende[] } | null
  total: number
  /** parcela do fixo (0 a 100) em operadora com ASN ligado, com sessão direta e só indireta; as duas últimas estão contidas na primeira */
  pctComAsn: number
  pctDireta: number
  pctSoIndireta: number
  /** a lista de provedores da região é cortada no servidor: parte das operadoras pode estar sem leitura */
  indeterminadas: number
  listaCortada: boolean
}

const NOME_NAO_INFORMADO = /^\s*nenhum\s+informado\s*$/i
const pct = (parte: number, total: number) => (total > 0 ? (parte / total) * 100 : 0)

/**
 * "Quem atende e como se conecta" (PT-26, município 5.2): uma linha por CNPJ do fixo, ordenada por acessos locais, com os ASNs ligados e os PTTs em que
 * esses ASNs têm sessão direta ou só aparecem de forma indireta. A parcela é do CNPJ (um CNPJ com vários ASNs conta uma vez; sem ASN também entra). O ASN de
 * operadora nacional aparece em todo município onde ela declara e não indica rede dentro dele. O nome já chega mascarado para empresário individual: não se
 * troca nem se completa nome de registro com ASN ou CNPJ de pessoa natural.
 */
export function quemAtende(
  operadores: SiciOperador[], regiao: Regiao | null | undefined, marcas: Array<{ marca: string; de_cnpj: string; para_cnpj: string }> = [],
): QuemAtende {
  const porAsn = new Map((regiao?.provedores ?? []).map((p) => [p.asn, p]))
  const listaCortada = !!regiao && regiao.provedores_total > regiao.provedores.length
  const marcaDe = new Map<string, string>()
  for (const m of marcas) { marcaDe.set(m.de_cnpj, m.marca); marcaDe.set(m.para_cnpj, m.marca) }
  const total = operadores.reduce((t, o) => t + o.acessos, 0)
  const todas: LinhaQuemAtende[] = operadores.map((o) => {
    const diretos = new Set<string>()
    const indiretos = new Set<string>()
    let ausentes = 0
    for (const a of o.asns) {
      const p = porAsn.get(a)
      if (!p) { ausentes++; continue }
      p.ptts_diretos.forEach((c) => diretos.add(c))
      p.ptts_indiretos.forEach((c) => indiretos.add(c))
    }
    const so = [...indiretos].filter((c) => !diretos.has(c)).sort()
    let situacao: SituacaoRede
    if (o.asns.length === 0) situacao = 'sem_asn'
    else if (diretos.size > 0) situacao = 'direta'
    else if (so.length > 0) situacao = 'so_indireta'
    else if (!regiao || (listaCortada && ausentes > 0)) situacao = 'indeterminada'
    else situacao = 'sem_ptt'
    const nomeSici = (o.empresa ?? '').trim()
    const nenhum = !nomeSici || NOME_NAO_INFORMADO.test(nomeSici)
    const nomeAsn = nenhum ? o.asns.map((a) => porAsn.get(a)?.nome).find((n) => !!n) : undefined
    return {
      cnpj: o.cnpj, nome: nenhum ? (nomeAsn ?? '') : nomeSici, nomeDoAsn: nenhum && !!nomeAsn, semNome: nenhum && !nomeAsn,
      marca: marcaDe.get(o.cnpj), acessos: o.acessos, share: pct(o.acessos, total), asns: o.asns,
      diretos: [...diretos].sort(), indiretos: so, situacao,
    }
  }).sort((a, b) => b.acessos - a.acessos || a.cnpj.localeCompare(b.cnpj))

  const soma = (f: (l: LinhaQuemAtende) => boolean) => pct(todas.filter(f).reduce((t, l) => t + l.acessos, 0), total)
  const nominais = todas.filter((l, i) => i < MAX_LINHAS && l.share >= PARCELA_MINIMA_LINHA_PCT)
  const resto = todas.filter((l) => !nominais.includes(l))
  // uma única operadora abaixo do corte aparece com o próprio nome: "Demais (1)" não agrega nada
  const linhas = resto.length === 1 ? [...nominais, resto[0]] : nominais
  const soAcessos = resto.reduce((t, l) => t + l.acessos, 0)
  const demais = resto.length > 1 ? {
    n: resto.length, acessos: soAcessos, share: pct(soAcessos, total),
    comAsn: resto.filter((l) => l.asns.length > 0).length, comSessaoDireta: resto.filter((l) => l.situacao === 'direta').length, linhas: resto,
  } : null
  return {
    linhas, demais, total,
    pctComAsn: soma((l) => l.asns.length > 0), pctDireta: soma((l) => l.situacao === 'direta'), pctSoIndireta: soma((l) => l.situacao === 'so_indireta'),
    indeterminadas: todas.filter((l) => l.situacao === 'indeterminada').length, listaCortada,
  }
}
