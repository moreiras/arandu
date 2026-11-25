// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { IXP_COORDS } from '../../components/maps/ixpCoords'
import { haversineKm, type LonLat } from '../../lib/geo'
import type { Regiao, SiciOperador } from '../../types/api'

/** Operadora com esta parcela do fixo local (ou mais) entra na tabela de PTT efetivo. */
export const PARTICIPACAO_MINIMA_PCT = 5

export interface OperadoraNoPtt { cnpj: string; empresa: string; share: number }
export interface PttEfetivo {
  codigo: string
  /** distância em linha reta do centróide do município à cidade do PTT (coordenada aproximada) */
  km: number | null
  operadoras: OperadoraNoPtt[]
  /** soma das participações no fixo local das operadoras com sessão direta neste PTT (cada operadora uma vez) */
  parcelaFixo: number
}
export interface PttsEfetivos {
  linhas: PttEfetivo[]
  /** parcela do fixo local declarada por CNPJ sem ASN ligado (o OBINT não vê a rede dele) */
  semAsnPct: number
  /** operadoras com {@link PARTICIPACAO_MINIMA_PCT} ou mais do fixo, e quantas delas têm sessão direta em algum PTT */
  consideradas: number
  comSessaoDireta: number
  /** a lista de provedores da região é cortada no servidor: operadora cujo ASN ficou fora não é contada como "sem sessão" */
  listaCortada: boolean
}

/**
 * PTT efetivo (PT-25, município 5.4): os PTTs onde operadoras com 5% ou mais do fixo local têm sessão direta, com a distância e a parcela do fixo. A operadora entra
 * pelo CNPJ declarado ao SICI e pelos ASNs ligados a ele; a sessão vem do cadastro de participantes do PTT. Não diz que o tráfego sai por ali: a escolha depende de
 * contrato de trânsito e transporte, que o OBINT não vê. A participação é do CNPJ (não se soma por ASN: um CNPJ com vários ASNs conta uma vez).
 */
export function pttsEfetivos(operadores: SiciOperador[], regiao: Regiao, centroide: LonLat | undefined): PttsEfetivos {
  const porAsn = new Map(regiao.provedores.map((p) => [p.asn, p]))
  const grandes = operadores.filter((o) => o.share >= PARTICIPACAO_MINIMA_PCT)
  const mapa = new Map<string, PttEfetivo>()
  let comSessaoDireta = 0
  for (const o of grandes) {
    const ptts = new Set<string>()
    for (const a of o.asns) for (const c of porAsn.get(a)?.ptts_diretos ?? []) ptts.add(c)
    if (ptts.size > 0) comSessaoDireta++
    for (const c of ptts) {
      const e = mapa.get(c) ?? { codigo: c, km: null, operadoras: [], parcelaFixo: 0 }
      e.operadoras.push({ cnpj: o.cnpj, empresa: o.empresa, share: o.share })
      e.parcelaFixo += o.share
      mapa.set(c, e)
    }
  }
  const linhas = [...mapa.values()].map((e) => {
    const c = IXP_COORDS[e.codigo]
    return { ...e, km: centroide && c ? haversineKm(centroide, [c[1], c[0]]) : null }
  }).sort((a, b) => (a.km ?? Infinity) - (b.km ?? Infinity) || a.codigo.localeCompare(b.codigo))
  return {
    linhas,
    semAsnPct: operadores.filter((o) => o.asns.length === 0).reduce((t, o) => t + o.share, 0),
    consideradas: grandes.length, comSessaoDireta,
    listaCortada: regiao.provedores_total > regiao.provedores.length,
  }
}
