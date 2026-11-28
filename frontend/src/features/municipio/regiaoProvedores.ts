// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { RegiaoProvedor, RegiaoVinculo } from '../../types/api'
import { unirPtts } from './quemAtende'

const ORDEM_VINCULO: RegiaoVinculo[] = ['sici', 'sede', 'geo']

/** Uma operadora (CNPJ) da região, com os ASNs dela; ASN sem CNPJ ligado (ou de pessoa natural) é uma linha própria. */
export interface LinhaProvedor {
  /** `cnpj:…` ou `asn:…`: identifica a linha */
  chave: string
  cnpj: string | null
  /** nome mais frequente entre os ASNs da linha (empate: o do menor ASN) */
  nome: string
  asns: Array<{ asn: number; nome: string }>
  vinculos: RegiaoVinculo[]
  /** acessos (fixo + móvel) do CNPJ na região, contados uma vez: a API repete o total do CNPJ em cada ASN dele */
  acessos: number
  /** prefixos geolocalizados ali: cada prefixo é de um ASN só, então os ASNs somam */
  prefixos: number
  diretos: string[]
  indiretos: string[]
}

export interface ProvedoresAgrupados {
  linhas: LinhaProvedor[]
  /** ASNs lidos (as linhas os repartem) */
  asns: number
  /** linhas com CNPJ ligado */
  operadoras: number
}

function maisFrequente(nomes: string[]): string {
  const n = new Map<string, number>()
  for (const x of nomes) if (x) n.set(x, (n.get(x) ?? 0) + 1)
  let melhor = ''
  let max = 0
  for (const [x, c] of n) if (c > max) { melhor = x; max = c }   // o Map guarda a ordem de inserção: o empate fica com o do menor ASN
  return melhor
}

/**
 * Agrupa os provedores da região por CNPJ. Regra por coluna: acessos = os do CNPJ, uma vez (máximo entre os ASNs, que trazem o mesmo total, separado em fixo
 * e móvel); prefixos = soma dos ASNs; vínculo = união (SICI, sede, IPs); PTTs = união dos ASNs (direto em qualquer um vale como direto; só indireto é o que
 * sobra). A ordem é a da API: acessos, vínculos, prefixos e menor ASN.
 */
export function agruparProvedores(provedores: RegiaoProvedor[]): ProvedoresAgrupados {
  const grupos = new Map<string, RegiaoProvedor[]>()
  for (const p of [...provedores].sort((a, b) => a.asn - b.asn)) {
    const chave = p.cnpj ? `cnpj:${p.cnpj}` : `asn:${p.asn}`
    grupos.set(chave, [...(grupos.get(chave) ?? []), p])
  }
  const linhas: LinhaProvedor[] = [...grupos].map(([chave, ps]) => {
    const { diretos, indiretos } = unirPtts(ps)
    return {
      chave, cnpj: ps[0].cnpj ?? null, nome: maisFrequente(ps.map((p) => p.nome)),
      asns: ps.map((p) => ({ asn: p.asn, nome: p.nome })),
      vinculos: ORDEM_VINCULO.filter((v) => ps.some((p) => p.vinculos.includes(v))),
      acessos: Math.max(...ps.map((p) => p.acessos_fixo)) + Math.max(...ps.map((p) => p.acessos_movel)),
      prefixos: ps.reduce((t, p) => t + p.prefixos_geo, 0),
      diretos, indiretos,
    }
  }).sort((a, b) => b.acessos - a.acessos || b.vinculos.length - a.vinculos.length || b.prefixos - a.prefixos || a.asns[0].asn - b.asns[0].asn)
  return { linhas, asns: provedores.length, operadoras: linhas.filter((l) => l.cnpj).length }
}

/** Dados do corte do conjunto (teto de municípios) que a página repassa aos blocos da região. */
export interface CorteRegiao { cortado?: boolean; dentroDoRaio?: number; raioKm?: number; raioEfetivoKm?: number; n: number }

/** Aviso de que a região foi limitada ao teto de municípios (o raio pedido tinha mais); `null` se não houve corte. */
export function avisoLimiteRegiao(c: CorteRegiao | undefined, fmtKm: (km: number) => string, fmt: (n: number) => string): string | null {
  if (!c?.cortado) return null
  return `O raio de ${fmt(c.raioKm ?? 0)} km tem ${fmt(c.dentroDoRaio ?? c.n)} municípios, mas a região foi limitada aos ${fmt(c.n)} mais próximos, até ${fmtKm(c.raioEfetivoKm ?? 0)} do centro. Os demais não entram nesta tabela nem nos blocos de PTTs, trânsito e segurança.`
}
