// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { SiciMunicipioRow } from '../../types/api'

export type MunicipioOperadora = SiciMunicipioRow & { ibge: string }

export interface ResumoUf { uf: string; municipios: number; acessos: number; pf: number; pj: number; pct: number | null }

/** Resumo por UF dos municípios da operadora (PT-23). A soma dos acessos por UF é a soma dos municípios: bate com o total declarado. */
export function resumoPorUf(municipios: readonly MunicipioOperadora[]): ResumoUf[] {
  const por = new Map<string, ResumoUf>()
  for (const m of municipios) {
    const e = por.get(m.uf) ?? { uf: m.uf, municipios: 0, acessos: 0, pf: 0, pj: 0, pct: null }
    e.municipios += 1; e.acessos += m.acessos; e.pf += m.pf; e.pj += m.pj
    por.set(m.uf, e)
  }
  const total = [...por.values()].reduce((s, e) => s + e.acessos, 0)
  return [...por.values()].map((e) => ({ ...e, pct: total ? (100 * e.acessos) / total : null })).sort((a, b) => b.acessos - a.acessos || a.uf.localeCompare(b.uf))
}

/** Municípios em que a operadora tem mais da metade dos acessos declarados (parcela estritamente acima de 50%); parcela nula não conta. */
export const comMaisDaMetade = (municipios: readonly MunicipioOperadora[]) => municipios.filter((m) => m.share != null && m.share > 50).length

/** Municípios em que ela é a única declarante (HHI local 10.000). */
export const comUmSoDeclarante = (municipios: readonly MunicipioOperadora[]) => municipios.filter((m) => m.municipio_operadores === 1).length

/** Sem acento e em minúsculas, para a busca por nome. */
export const semAcento = (t: string) => t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
