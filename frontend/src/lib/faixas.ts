// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

const KBPS: Record<string, number> = { kbps: 1, mbps: 1000, gbps: 1_000_000 }

/**
 * Início da faixa de velocidade do SICI, em kbps, para ordenar "0–512 kbps", "512 kbps a 2 Mbps", "12 a 34 Mbps", "> 34 Mbps".
 * Rótulo sem número ("N/I") vai para o fim. A unidade pode vir depois do segundo número ("2 a 12 Mbps"): vale a primeira que aparecer.
 */
export function inicioDaFaixaKbps(rotulo: string): number {
  const num = rotulo.match(/(\d+(?:[.,]\d+)?)/)
  if (!num) return Number.POSITIVE_INFINITY
  const un = rotulo.slice(num.index! + num[1].length).match(/(kbps|mbps|gbps)/i) ?? rotulo.match(/(kbps|mbps|gbps)/i)
  const fator = un ? KBPS[un[1].toLowerCase()] : 1
  return parseFloat(num[1].replace(',', '.')) * fator
}

/** Ordena entradas [rótulo, valor] pela faixa (menor velocidade primeiro), não pelo valor. */
export function ordenarPorFaixa<T>(entradas: [string, T][]): [string, T][] {
  return [...entradas].sort((a, b) => inicioDaFaixaKbps(a[0]) - inicioDaFaixaKbps(b[0]))
}
