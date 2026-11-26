// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { Selo } from '../components/entidade/proveniencia'

/**
 * Síntese em texto no topo das páginas (PT-22): 2 a 4 frases montadas por regra fixa, sem modelo de linguagem, a partir dos MESMOS números que a
 * página exibe (os geradores recebem os objetos que a página já buscou; nenhum número é digitado à mão). Cada frase leva selo, fonte e data de
 * referência, mostrados por `SinteseTopo` com o `LinhaProveniencia` dos KPIs. Política editorial: só dados e comparações, sem juízo de valor,
 * causa ou intenção; o que é estimado ou inferido leva o selo próprio. Frase cujo dado falta não é gerada (ausência não vira zero).
 */
export interface FraseSintese {
  id: string
  texto: string
  selo: Selo
  /** Fonte em texto curto ("SICI, Anatel (declarado pelas operadoras)"). */
  fonte: string
  /** Data (AAAA-MM-DD) ou mês (AAAA-MM) a que o número se refere. */
  dataRef?: string | null
}

/** Mínimo e máximo de frases de uma síntese: com menos de duas não há síntese (o bloco some), e acima de quatro vira lista de KPIs. */
export const MIN_FRASES = 2
export const MAX_FRASES = 4

/** Palavras de juízo, causa ou intenção que uma frase gerada nunca usa (conferido em `sintese.test.ts` de cada gerador). */
export const PALAVRAS_PROIBIDAS = /\b(melhor|pior|atrás|atras|ruim|omitiu|preocupante|alarmante|deficiente|porque|culpa|negligên)/i

export const n0 = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
export const n1 = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })
export const pct1 = (v: number) => `${n1(v)}%`
/** Número grande abreviado: 161,3 mi. */
export function compacto(v: number): string {
  const a = Math.abs(v)
  if (a >= 1e9) return `${n1(v / 1e9)} bi`
  if (a >= 1e6) return `${n1(v / 1e6)} mi`
  if (a >= 1e4) return `${n0(v / 1e3)} mil`
  return n0(v)
}
/** A palavra no singular ou no plural pelo número, sem o número (para frases em que o número vem em outro elemento). */
export const palavra = (q: number | null | undefined, um: string, varios: string) => (q === 1 ? um : varios)
/** "1 PTT" / "3 PTTs". */
export const plural = (q: number, um: string, varios: string) => `${n0(q)} ${q === 1 ? um : varios}`

/** Mantém no máximo `MAX_FRASES`, sem duplicar id; o bloco só aparece com pelo menos `MIN_FRASES`. */
export function limitar(frases: Array<FraseSintese | null | undefined | false>): FraseSintese[] {
  const vistos = new Set<string>()
  const ok: FraseSintese[] = []
  for (const f of frases) {
    if (!f || vistos.has(f.id)) continue
    vistos.add(f.id)
    ok.push(f)
  }
  const cortadas = ok.slice(0, MAX_FRASES)
  return cortadas.length >= MIN_FRASES ? cortadas : []
}
