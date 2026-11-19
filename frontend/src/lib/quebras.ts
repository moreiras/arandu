// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

/** Como as classes de um mapa coroplético são cortadas. A escolha é declarada na legenda (nunca escondida). */
export type MetodoQuebras = 'quantis' | 'intervalos-iguais'

export const DESCRICAO_METODO: Record<MetodoQuebras, string> = {
  quantis: 'Classes com o mesmo número de municípios (quantis): mostram a ordem, não a distância entre os valores.',
  'intervalos-iguais': 'Classes de mesma largura entre o menor e o maior valor: preservam a distância entre os valores, mas valores extremos podem esvaziar classes.',
}

/**
 * Limites internos das classes (`classes - 1` valores, crescentes e sem repetição; pode devolver menos se os dados forem muito repetidos).
 * `valores` fora (nulos, NaN, infinitos) são ignorados.
 */
export function calcularQuebras(valores: Array<number | null | undefined>, classes: number, metodo: MetodoQuebras = 'quantis'): number[] {
  const v = valores.filter((x): x is number => typeof x === 'number' && Number.isFinite(x)).sort((a, b) => a - b)
  if (v.length === 0 || classes < 2) return []
  const brutas: number[] = []
  for (let i = 1; i < classes; i++) {
    if (metodo === 'quantis') {
      const pos = (i / classes) * (v.length - 1)
      const lo = Math.floor(pos)
      brutas.push(v[lo] + (v[Math.min(lo + 1, v.length - 1)] - v[lo]) * (pos - lo))
    } else {
      brutas.push(v[0] + ((v[v.length - 1] - v[0]) * i) / classes)
    }
  }
  return brutas.filter((q, i) => i === 0 || q > brutas[i - 1])
}

/** Índice da classe (0 = menor) de um valor: a classe `i` vai até `quebras[i]` (inclusive no limite inferior da seguinte). */
export function classeDe(valor: number, quebras: number[]): number {
  let c = 0
  while (c < quebras.length && valor >= quebras[c]) c++
  return c
}

/** Rótulos da legenda, um por classe: "menos de X", "X a Y", "Y ou mais". */
export function rotulosDasClasses(quebras: number[], formatar: (v: number) => string): string[] {
  if (quebras.length === 0) return ['todos os valores']
  const r = [`menos de ${formatar(quebras[0])}`]
  for (let i = 1; i < quebras.length; i++) r.push(`${formatar(quebras[i - 1])} a ${formatar(quebras[i])}`)
  r.push(`${formatar(quebras[quebras.length - 1])} ou mais`)
  return r
}
