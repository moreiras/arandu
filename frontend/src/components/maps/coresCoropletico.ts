// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { corDaEscala, ESCALA_SEQUENCIAL } from '../../lib/escalasMapa'
import { classeDe } from '../../lib/quebras'

/** Cor de quem não tem dado: cinza claro, explicado na legenda (nunca a cor do zero). */
export const COR_SEM_DADO = '#e5e7eb'

/** Cores das `n` classes de uma escala sequencial segura para daltonismo (Viridis por padrão). */
export function coresDasClasses(n: number, escala: readonly string[] = ESCALA_SEQUENCIAL): string[] {
  return Array.from({ length: n }, (_, i) => corDaEscala(escala, n === 1 ? 0.5 : i / (n - 1)))
}

/**
 * Expressão MapLibre que pinta cada feição pela classe do seu código: `['match', ['get', chave], [ids da classe 0], cor0, ..., semDado]`.
 * Os ids vão agrupados por classe (cada classe é uma lista), então a expressão tem poucas dezenas de ramos mesmo com 5.500 municípios.
 */
export function expressaoCor(valores: Record<string, number | null | undefined>, quebras: number[], cores: string[], chave = 'ibge', semDado = COR_SEM_DADO): unknown[] {
  const porClasse: string[][] = cores.map(() => [])
  for (const [id, v] of Object.entries(valores)) if (typeof v === 'number' && Number.isFinite(v)) porClasse[Math.min(classeDe(v, quebras), cores.length - 1)].push(id)
  const ramos: unknown[] = []
  porClasse.forEach((ids, i) => { if (ids.length) ramos.push(ids, cores[i]) })
  return ramos.length ? ['match', ['get', chave], ...ramos, semDado] : semDado as unknown as unknown[]
}

// ── Bivariado ──────────────────────────────────────────────────────────────
/** Paleta bivariada 3 × 3 (linha = classe do 2º indicador, coluna = classe do 1º): do cinza claro ao azul-violeta escuro; cada cor tem rótulo na legenda. */
export const PALETA_BIVARIADA: string[][] = [
  ['#e8e8e8', '#ace4e4', '#5ac8c8'],
  ['#dfb0d6', '#a5add3', '#5698b9'],
  ['#be64ac', '#8c62aa', '#3b4994'],
]

/** Classe bivariada 0..8 (`linha * 3 + coluna`) a partir das classes de cada indicador (0..2). */
export const classeBivariada = (c1: number, c2: number): number => Math.min(2, c2) * 3 + Math.min(2, c1)

/** Expressão para o mapa bivariado: só municípios com os dois valores recebem cor; o resto fica sem dado. */
export function expressaoBivariada(v1: Record<string, number | null | undefined>, v2: Record<string, number | null | undefined>, q1: number[], q2: number[], chave = 'ibge'): unknown[] {
  const porClasse: string[][] = Array.from({ length: 9 }, () => [])
  for (const [id, a] of Object.entries(v1)) {
    const b = v2[id]
    if (typeof a === 'number' && typeof b === 'number') porClasse[classeBivariada(classeDe(a, q1), classeDe(b, q2))].push(id)
  }
  const ramos: unknown[] = []
  porClasse.forEach((ids, i) => { if (ids.length) ramos.push(ids, PALETA_BIVARIADA[Math.floor(i / 3)][i % 3]) })
  return ramos.length ? ['match', ['get', chave], ...ramos, COR_SEM_DADO] : COR_SEM_DADO as unknown as unknown[]
}

/** Terços (2 quebras) de um indicador, para o bivariado. */
export const NOMES_TERCOS = ['baixo', 'médio', 'alto'] as const
