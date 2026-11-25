// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { LimiteJanela } from '../types/api'

const n = (v: number) => v.toLocaleString('pt-BR')

/** "120 por minuto, 1.500 por hora e 6.000 por dia"; lista vazia = classe sem teto nesta instalação. */
export function descreverJanelas(js: LimiteJanela[]): string {
  if (js.length === 0) return 'sem teto por janela'
  const itens = js.map((j) => `${n(j.limite)} por ${j.janela}`)
  return itens.length === 1 ? itens[0] : `${itens.slice(0, -1).join(', ')} e ${itens[itens.length - 1]}`
}

export { n as numeroBR }
